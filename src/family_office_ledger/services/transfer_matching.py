"""Transfer matching service for pairing inter-account transfers."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from family_office_ledger.domain.transactions import Transaction
from family_office_ledger.domain.transfer_matching import (
    TransferMatch,
    TransferMatchingSession,
    TransferMatchStatus,
)
from family_office_ledger.domain.value_objects import TransactionType
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    TransactionRepository,
)


class TransferMatchNotFoundError(Exception):
    pass


class TransferSessionNotFoundError(Exception):
    pass


class TransferSessionExistsError(Exception):
    pass


@dataclass
class TransferMatchingSummary:
    total_matches: int = 0
    pending_count: int = 0
    confirmed_count: int = 0
    rejected_count: int = 0
    total_confirmed_amount: Decimal = field(default_factory=lambda: Decimal("0"))


class TransferMatchingService:
    # Matches: same amount, within date_tolerance_days, TRANSFER or TRUST_TRANSFER types
    TRANSFER_TYPES = {TransactionType.TRANSFER, TransactionType.TRUST_TRANSFER}

    def __init__(
        self,
        transaction_repo: TransactionRepository,
        account_repo: AccountRepository,
    ) -> None:
        self._transaction_repo = transaction_repo
        self._account_repo = account_repo
        self._sessions: dict[UUID, TransferMatchingSession] = {}

    def create_session(
        self,
        entity_ids: list[UUID] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        date_tolerance_days: int = 3,
    ) -> TransferMatchingSession:
        session = TransferMatchingSession(
            entity_ids=entity_ids or [],
            date_tolerance_days=date_tolerance_days,
        )

        candidates = self._find_transfer_candidates(
            entity_ids=entity_ids,
            start_date=start_date,
            end_date=end_date,
        )

        matches = self._pair_transfers(candidates, date_tolerance_days)
        session.matches = matches

        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: UUID) -> TransferMatchingSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise TransferSessionNotFoundError(f"Session {session_id} not found")
        return session

    def list_matches(
        self,
        session_id: UUID,
        status: TransferMatchStatus | None = None,
    ) -> list[TransferMatch]:
        session = self.get_session(session_id)
        if status is None:
            return session.matches
        return [m for m in session.matches if m.status == status]

    def confirm_match(self, session_id: UUID, match_id: UUID) -> TransferMatch:
        session = self.get_session(session_id)
        match = self._find_match(session, match_id)
        match.status = TransferMatchStatus.CONFIRMED
        match.confirmed_at = datetime.now(UTC)
        return match

    def reject_match(self, session_id: UUID, match_id: UUID) -> TransferMatch:
        session = self.get_session(session_id)
        match = self._find_match(session, match_id)
        match.status = TransferMatchStatus.REJECTED
        return match

    def close_session(self, session_id: UUID) -> TransferMatchingSession:
        session = self.get_session(session_id)
        session.status = "completed"
        session.closed_at = datetime.now(UTC)
        return session

    def get_summary(self, session_id: UUID) -> TransferMatchingSummary:
        session = self.get_session(session_id)
        confirmed_amount = sum(
            (m.amount for m in session.matches if m.is_confirmed),
            Decimal("0"),
        )
        return TransferMatchingSummary(
            total_matches=len(session.matches),
            pending_count=session.pending_count,
            confirmed_count=session.confirmed_count,
            rejected_count=session.rejected_count,
            total_confirmed_amount=confirmed_amount,
        )

    def _find_match(
        self, session: TransferMatchingSession, match_id: UUID
    ) -> TransferMatch:
        for match in session.matches:
            if match.id == match_id:
                return match
        raise TransferMatchNotFoundError(f"Match {match_id} not found in session")

    def _find_transfer_candidates(
        self,
        entity_ids: list[UUID] | None,
        start_date: date | None,
        end_date: date | None,
    ) -> list[Transaction]:
        candidates: list[Transaction] = []

        if entity_ids:
            for entity_id in entity_ids:
                txns = list(
                    self._transaction_repo.list_by_entity(
                        entity_id,
                        start_date=start_date,
                        end_date=end_date,
                    )
                )
                candidates.extend(txns)
        elif start_date and end_date:
            candidates = list(
                self._transaction_repo.list_by_date_range(start_date, end_date)
            )

        return candidates

    def _pair_transfers(
        self,
        transactions: list[Transaction],
        date_tolerance_days: int,
    ) -> list[TransferMatch]:
        matches: list[TransferMatch] = []
        matched_ids: set[UUID] = set()

        outflows: list[Transaction] = []
        inflows: list[Transaction] = []

        for txn in transactions:
            if txn.id in matched_ids:
                continue

            for entry in txn.entries:
                if entry.debit_amount.is_positive and entry.credit_amount.is_zero:
                    outflows.append(txn)
                    break
                elif entry.credit_amount.is_positive and entry.debit_amount.is_zero:
                    inflows.append(txn)
                    break

        for outflow in outflows:
            if outflow.id in matched_ids:
                continue

            outflow_amount = outflow.total_debits.amount
            outflow_date = outflow.transaction_date
            outflow_account_id = self._get_primary_account_id(outflow)

            best_match: Transaction | None = None
            best_score = 0

            for inflow in inflows:
                if inflow.id in matched_ids:
                    continue

                inflow_amount = inflow.total_credits.amount
                inflow_date = inflow.transaction_date
                inflow_account_id = self._get_primary_account_id(inflow)

                if outflow_account_id == inflow_account_id:
                    continue

                if outflow_amount != inflow_amount:
                    continue

                date_diff = abs((outflow_date - inflow_date).days)
                if date_diff > date_tolerance_days:
                    continue

                score = self._calculate_match_score(outflow, inflow, date_diff)
                if score > best_score:
                    best_score = score
                    best_match = inflow

            if best_match is not None:
                match = TransferMatch(
                    source_transaction_id=outflow.id,
                    target_transaction_id=best_match.id,
                    source_account_id=outflow_account_id,
                    target_account_id=self._get_primary_account_id(best_match),
                    amount=outflow_amount,
                    transfer_date=outflow_date,
                    confidence_score=best_score,
                    memo=outflow.memo or best_match.memo or "",
                )
                matches.append(match)
                matched_ids.add(outflow.id)
                matched_ids.add(best_match.id)

        return matches

    def _get_primary_account_id(self, txn: Transaction) -> UUID:
        if txn.entries:
            return txn.entries[0].account_id
        raise ValueError(f"Transaction {txn.id} has no entries")

    def _calculate_match_score(
        self,
        outflow: Transaction,
        inflow: Transaction,
        date_diff: int,
    ) -> int:
        score = 50

        if date_diff == 0:
            score += 30
        elif date_diff == 1:
            score += 20
        elif date_diff <= 3:
            score += 10

        if outflow.memo and inflow.memo:
            if outflow.memo.lower() == inflow.memo.lower():
                score += 20
            elif any(
                word in inflow.memo.lower()
                for word in outflow.memo.lower().split()
                if len(word) > 3
            ):
                score += 10

        return min(score, 100)


__all__ = [
    "TransferMatchingService",
    "TransferMatchingSummary",
    "TransferMatchNotFoundError",
    "TransferSessionNotFoundError",
    "TransferSessionExistsError",
]
