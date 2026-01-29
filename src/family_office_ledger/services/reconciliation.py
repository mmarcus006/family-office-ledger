"""Reconciliation service for matching imported transactions with ledger."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from family_office_ledger.domain.reconciliation import (
    ReconciliationMatch,
    ReconciliationMatchStatus,
    ReconciliationSession,
    ReconciliationSessionStatus,
)
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.value_objects import Money
from family_office_ledger.parsers.csv_parser import CSVParser
from family_office_ledger.parsers.ofx_parser import OFXParser
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    ReconciliationSessionRepository,
    TransactionRepository,
)
from family_office_ledger.services.interfaces import (
    MatchResult,
    ReconciliationService,
    ReconciliationSummary,
)


class SessionExistsError(Exception):
    """Raised when trying to create a session when one already exists."""


class SessionNotFoundError(Exception):
    """Raised when a session is not found."""


class MatchNotFoundError(Exception):
    """Raised when a match is not found."""


@dataclass
class SessionSummary:
    """Summary statistics for a reconciliation session."""

    total_imported: int
    pending: int
    confirmed: int
    rejected: int
    skipped: int
    match_rate: float


class ReconciliationServiceImpl(ReconciliationService):
    """Implementation of ReconciliationService for bank/brokerage reconciliation.

    Match scoring:
    - Exact amount match: 50 points
    - Date within 3 days: 30 points
    - Memo similarity: up to 20 points (based on text similarity)

    Minimum score for match: 50 points (requires at least exact amount)
    """

    # Scoring weights
    SCORE_EXACT_AMOUNT = 50
    SCORE_DATE_WITHIN_3_DAYS = 30
    SCORE_MEMO_MAX = 20
    MATCH_THRESHOLD = 50  # Minimum score to consider a match

    # Import reference prefix for tracking matched imports
    IMPORT_REF_PREFIX = "IMPORT:"

    def __init__(
        self,
        transaction_repo: TransactionRepository,
        account_repo: AccountRepository,
        session_repo: ReconciliationSessionRepository | None = None,
    ) -> None:
        """Initialize ReconciliationService.

        Args:
            transaction_repo: Repository for transaction persistence.
            account_repo: Repository for account lookup.
            session_repo: Repository for reconciliation sessions (optional for backward compat).
        """
        self._transaction_repo = transaction_repo
        self._account_repo = account_repo
        self._session_repo = session_repo
        self._csv_parser = CSVParser()
        self._ofx_parser = OFXParser()

    def import_transactions(
        self,
        file_path: str,
        account_id: UUID,
        file_format: str,
    ) -> list[dict[str, Any]]:
        """Import transactions from a file.

        Args:
            file_path: Path to the file to import.
            account_id: ID of the account to import into.
            file_format: Format of the file ('csv', 'ofx', 'qfx').

        Returns:
            List of imported transaction dictionaries with standardized fields.

        Raises:
            ValueError: If file format is not supported.
            FileNotFoundError: If file does not exist.
        """
        format_lower = file_format.lower()

        if format_lower == "csv":
            return self._csv_parser.parse(file_path)
        elif format_lower in ("ofx", "qfx"):
            return self._ofx_parser.parse(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

    def match_imported(
        self,
        imported_transactions: list[dict[str, Any]],
        account_id: UUID,
    ) -> list[MatchResult]:
        """Match imported transactions against ledger transactions.

        Uses fuzzy matching based on:
        - Exact amount: 50 points
        - Date within 3 days: 30 points
        - Memo similarity: up to 20 points

        Args:
            imported_transactions: List of imported transaction dictionaries.
            account_id: Account ID to match against.

        Returns:
            List of MatchResult objects indicating match status and confidence.
        """
        results: list[MatchResult] = []

        # Get all ledger transactions for this account
        ledger_transactions = list(self._transaction_repo.list_by_account(account_id))

        for imported in imported_transactions:
            best_match: MatchResult | None = None
            best_score = 0

            imported_id = str(imported.get("import_id", ""))
            imported_date = imported.get("date")
            imported_amount = imported.get("amount")
            imported_desc = str(
                imported.get("description", "") or imported.get("memo", "")
            )

            if imported_date is None or imported_amount is None:
                results.append(
                    MatchResult(
                        imported_id=imported_id,
                        ledger_transaction_id=None,
                        confidence_score=0,
                        matched=False,
                        reason="Missing date or amount in imported transaction",
                    )
                )
                continue

            for ledger_txn in ledger_transactions:
                score = self._calculate_match_score(
                    imported_date=imported_date,
                    imported_amount=imported_amount,
                    imported_desc=imported_desc,
                    ledger_txn=ledger_txn,
                    account_id=account_id,
                )

                if score > best_score:
                    best_score = score
                    reason = self._build_match_reason(score)
                    best_match = MatchResult(
                        imported_id=imported_id,
                        ledger_transaction_id=ledger_txn.id,
                        confidence_score=score,
                        matched=score >= self.MATCH_THRESHOLD,
                        reason=reason,
                    )

            if best_match and best_match.matched:
                results.append(best_match)
            else:
                results.append(
                    MatchResult(
                        imported_id=imported_id,
                        ledger_transaction_id=None,
                        confidence_score=0,
                        matched=False,
                        reason="No matching ledger transaction found",
                    )
                )

        return results

    def _calculate_match_score(
        self,
        imported_date: date,
        imported_amount: Decimal,
        imported_desc: str,
        ledger_txn: Transaction,
        account_id: UUID,
    ) -> int:
        """Calculate match score between imported and ledger transaction.

        Args:
            imported_date: Date from imported transaction.
            imported_amount: Amount from imported transaction.
            imported_desc: Description from imported transaction.
            ledger_txn: Ledger transaction to compare against.
            account_id: Account ID to look for in entries.

        Returns:
            Match score (0-100).
        """
        score = 0

        # Find the entry for this account in the ledger transaction
        ledger_amount = self._get_transaction_amount_for_account(ledger_txn, account_id)
        if ledger_amount is None:
            return 0

        # Exact amount match: 50 points
        if imported_amount == ledger_amount:
            score += self.SCORE_EXACT_AMOUNT
        else:
            # No amount match = no match at all
            return 0

        # Date within 3 days: 30 points
        date_diff = abs((imported_date - ledger_txn.transaction_date).days)
        if date_diff <= 3:
            score += self.SCORE_DATE_WITHIN_3_DAYS

        # Memo similarity: up to 20 points
        if imported_desc and ledger_txn.memo:
            similarity = SequenceMatcher(
                None,
                imported_desc.lower(),
                ledger_txn.memo.lower(),
            ).ratio()
            score += int(similarity * self.SCORE_MEMO_MAX)

        return score

    def _get_transaction_amount_for_account(
        self, txn: Transaction, account_id: UUID
    ) -> Decimal | None:
        """Get the net amount for a specific account in a transaction.

        For asset accounts:
        - Debit = money coming in (positive)
        - Credit = money going out (negative)

        Args:
            txn: Transaction to examine.
            account_id: Account ID to find.

        Returns:
            Net amount for the account, or None if not found.
        """
        for entry in txn.entries:
            if entry.account_id == account_id:
                # Net = debit - credit
                # For asset accounts, debit is positive (money in), credit is negative (money out)
                debit = (
                    entry.debit_amount.amount if entry.debit_amount else Decimal("0")
                )
                credit = (
                    entry.credit_amount.amount if entry.credit_amount else Decimal("0")
                )
                return debit - credit
        return None

    def _build_match_reason(self, score: int) -> str:
        """Build a human-readable reason for the match score.

        Args:
            score: Match score.

        Returns:
            Reason string.
        """
        reasons = []
        if score >= self.SCORE_EXACT_AMOUNT:
            reasons.append("exact amount match")
        if score >= self.SCORE_EXACT_AMOUNT + self.SCORE_DATE_WITHIN_3_DAYS:
            reasons.append("date within 3 days")
        if score > self.SCORE_EXACT_AMOUNT + self.SCORE_DATE_WITHIN_3_DAYS:
            reasons.append("memo similarity")

        if reasons:
            return "Matched: " + ", ".join(reasons)
        return "No match"

    def confirm_match(
        self,
        imported_id: str,
        ledger_transaction_id: UUID,
    ) -> None:
        """Confirm a match between an imported transaction and a ledger transaction.

        Updates the ledger transaction's reference field to include the import ID.

        Args:
            imported_id: ID of the imported transaction.
            ledger_transaction_id: ID of the ledger transaction.
        """
        txn = self._transaction_repo.get(ledger_transaction_id)
        if txn is None:
            raise ValueError(f"Ledger transaction not found: {ledger_transaction_id}")

        # Update reference to include import ID
        if txn.reference:
            txn.reference = f"{txn.reference};{self.IMPORT_REF_PREFIX}{imported_id}"
        else:
            txn.reference = f"{self.IMPORT_REF_PREFIX}{imported_id}"

        self._transaction_repo.update(txn)

    def create_from_import(
        self,
        imported_transaction: dict[str, Any],
        account_id: UUID,
    ) -> Transaction:
        """Create a new ledger transaction from an imported transaction.

        Creates a balanced double-entry transaction:
        - Positive amount: debit to account (money in), credit to suspense
        - Negative amount: credit from account (money out), debit to suspense

        Note: The suspense account entry is a placeholder. In real usage,
        the user would categorize this to the appropriate income/expense account.

        Args:
            imported_transaction: Imported transaction dictionary.
            account_id: Account ID for the primary entry.

        Returns:
            Created and saved Transaction.
        """
        import_id = str(imported_transaction.get("import_id", ""))
        txn_date = imported_transaction.get("date")
        amount = imported_transaction.get("amount")
        description = str(
            imported_transaction.get("description", "")
            or imported_transaction.get("memo", "")
            or "Imported transaction"
        )

        if not isinstance(txn_date, date):
            raise ValueError("Invalid or missing date in imported transaction")
        if not isinstance(amount, Decimal):
            raise ValueError("Invalid or missing amount in imported transaction")

        # Get the account to determine currency
        account = self._account_repo.get(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")

        currency = account.currency

        # Create transaction
        txn = Transaction(
            transaction_date=txn_date,
            memo=description,
            reference=import_id,
        )
        # Update created_at to use timezone-aware datetime
        object.__setattr__(txn, "created_at", datetime.now(UTC))

        # Create entries based on amount sign
        abs_amount = abs(amount)
        money_amount = Money(abs_amount, currency)

        if amount >= 0:
            # Positive = money coming in (debit to asset account)
            txn.add_entry(
                Entry(
                    account_id=account_id,
                    debit_amount=money_amount,
                    memo=description,
                )
            )
            # Credit to a suspense/unclassified income (using same account as placeholder)
            # In real implementation, this would be a designated suspense account
            txn.add_entry(
                Entry(
                    account_id=account_id,
                    credit_amount=money_amount,
                    memo=f"Suspense: {description}",
                )
            )
        else:
            # Negative = money going out (credit from asset account)
            txn.add_entry(
                Entry(
                    account_id=account_id,
                    credit_amount=money_amount,
                    memo=description,
                )
            )
            # Debit to a suspense/unclassified expense (using same account as placeholder)
            txn.add_entry(
                Entry(
                    account_id=account_id,
                    debit_amount=money_amount,
                    memo=f"Suspense: {description}",
                )
            )

        # Save and return
        self._transaction_repo.add(txn)
        return txn

    def get_reconciliation_summary(
        self,
        account_id: UUID,
        start_date: date,
        end_date: date,
    ) -> ReconciliationSummary:
        """Get a summary of reconciliation status for an account.

        Examines transactions in the date range and counts:
        - Total transactions (considered as "imported")
        - Matched (have import reference)
        - Unmatched (no import reference)
        - Duplicates (same import ID appears multiple times)

        Args:
            account_id: Account ID to summarize.
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            ReconciliationSummary with statistics.
        """
        transactions = list(
            self._transaction_repo.list_by_account(
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
            )
        )

        total_count = len(transactions)
        matched_count = 0
        unmatched_count = 0
        duplicate_count = 0
        exceptions: list[str] = []
        seen_import_ids: set[str] = set()

        for txn in transactions:
            # Check if it has an import reference
            if self.IMPORT_REF_PREFIX in txn.reference:
                matched_count += 1

                # Extract import ID and check for duplicates
                import_ids = self._extract_import_ids(txn.reference)
                for import_id in import_ids:
                    if import_id in seen_import_ids:
                        duplicate_count += 1
                        exceptions.append(f"Duplicate import ID: {import_id}")
                    seen_import_ids.add(import_id)
            else:
                unmatched_count += 1

        return ReconciliationSummary(
            total_imported=total_count,
            matched_count=matched_count,
            unmatched_count=unmatched_count,
            duplicate_count=duplicate_count,
            exceptions=exceptions,
        )

    def _extract_import_ids(self, reference: str) -> list[str]:
        """Extract import IDs from a reference string.

        Args:
            reference: Reference string potentially containing import IDs.

        Returns:
            List of import ID strings.
        """
        import_ids: list[str] = []
        parts = reference.split(";")
        for part in parts:
            if part.startswith(self.IMPORT_REF_PREFIX):
                import_ids.append(part[len(self.IMPORT_REF_PREFIX) :])
        return import_ids

    def create_session(
        self,
        account_id: UUID,
        file_path: str,
        file_format: str,
    ) -> ReconciliationSession:
        """Create a new reconciliation session for an account.

        Imports transactions from file and creates matches against ledger.

        Args:
            account_id: Account to reconcile.
            file_path: Path to import file.
            file_format: File format (csv, ofx, qfx).

        Returns:
            Created session with matches.

        Raises:
            SessionExistsError: If pending session exists for account.
        """
        if self._session_repo is None:
            raise RuntimeError("Session repository not configured")

        existing = self._session_repo.get_pending_for_account(account_id)
        if existing is not None:
            raise SessionExistsError(
                f"Pending session already exists for account {account_id}"
            )

        imported = self.import_transactions(file_path, account_id, file_format)
        match_results = self.match_imported(imported, account_id)

        session = ReconciliationSession(
            account_id=account_id,
            file_name=file_path.split("/")[-1],
            file_format=file_format,
        )

        for imp, result in zip(imported, match_results, strict=True):
            imported_date = imp.get("date")
            imported_amount = imp.get("amount")

            if imported_date is None or imported_amount is None:
                continue

            match = ReconciliationMatch(
                session_id=session.id,
                imported_id=str(imp.get("import_id", "")),
                imported_date=imported_date,
                imported_amount=imported_amount,
                imported_description=str(
                    imp.get("description") or imp.get("memo") or ""
                ),
                suggested_ledger_txn_id=result.ledger_transaction_id
                if result.matched
                else None,
                confidence_score=result.confidence_score,
            )
            session.matches.append(match)

        self._session_repo.add(session)
        return session

    def get_session(self, session_id: UUID) -> ReconciliationSession | None:
        """Get a reconciliation session by ID.

        Args:
            session_id: Session ID.

        Returns:
            Session or None if not found.
        """
        if self._session_repo is None:
            raise RuntimeError("Session repository not configured")
        return self._session_repo.get(session_id)

    def list_matches(
        self,
        session_id: UUID,
        status: ReconciliationMatchStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ReconciliationMatch], int]:
        """List matches for a session with optional filtering and pagination.

        Args:
            session_id: Session ID.
            status: Optional status filter.
            limit: Max matches to return.
            offset: Offset for pagination.

        Returns:
            Tuple of (matches, total_count).

        Raises:
            SessionNotFoundError: If session not found.
        """
        if self._session_repo is None:
            raise RuntimeError("Session repository not configured")

        session = self._session_repo.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        matches = session.matches
        if status is not None:
            matches = [m for m in matches if m.status == status]

        total = len(matches)
        paginated = matches[offset : offset + limit]

        return paginated, total

    def confirm_session_match(
        self, session_id: UUID, match_id: UUID
    ) -> ReconciliationMatch:
        """Confirm a match in a session.

        Args:
            session_id: Session ID.
            match_id: Match ID.

        Returns:
            Updated match.

        Raises:
            SessionNotFoundError: If session not found.
            MatchNotFoundError: If match not found or has no suggested transaction.
        """
        if self._session_repo is None:
            raise RuntimeError("Session repository not configured")

        session = self._session_repo.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        match = next((m for m in session.matches if m.id == match_id), None)
        if match is None:
            raise MatchNotFoundError(f"Match not found: {match_id}")

        if match.suggested_ledger_txn_id is None:
            raise MatchNotFoundError("Cannot confirm: no suggested ledger transaction")

        match.status = ReconciliationMatchStatus.CONFIRMED
        match.actioned_at = datetime.now(UTC)

        self.confirm_match(match.imported_id, match.suggested_ledger_txn_id)

        self._session_repo.update(session)
        self._check_auto_close(session)

        return match

    def reject_session_match(
        self, session_id: UUID, match_id: UUID
    ) -> ReconciliationMatch:
        """Reject a match in a session.

        Args:
            session_id: Session ID.
            match_id: Match ID.

        Returns:
            Updated match.

        Raises:
            SessionNotFoundError: If session not found.
            MatchNotFoundError: If match not found.
        """
        if self._session_repo is None:
            raise RuntimeError("Session repository not configured")

        session = self._session_repo.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        match = next((m for m in session.matches if m.id == match_id), None)
        if match is None:
            raise MatchNotFoundError(f"Match not found: {match_id}")

        match.status = ReconciliationMatchStatus.REJECTED
        match.actioned_at = datetime.now(UTC)

        self._session_repo.update(session)
        self._check_auto_close(session)

        return match

    def skip_session_match(
        self, session_id: UUID, match_id: UUID
    ) -> ReconciliationMatch:
        """Skip a match in a session.

        Args:
            session_id: Session ID.
            match_id: Match ID.

        Returns:
            Updated match.

        Raises:
            SessionNotFoundError: If session not found.
            MatchNotFoundError: If match not found.
        """
        if self._session_repo is None:
            raise RuntimeError("Session repository not configured")

        session = self._session_repo.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        match = next((m for m in session.matches if m.id == match_id), None)
        if match is None:
            raise MatchNotFoundError(f"Match not found: {match_id}")

        match.status = ReconciliationMatchStatus.SKIPPED
        match.actioned_at = datetime.now(UTC)

        self._session_repo.update(session)

        return match

    def close_session(self, session_id: UUID) -> ReconciliationSession:
        """Manually close a session.

        Sets status to COMPLETED if all matches are resolved (no pending/skipped),
        otherwise sets to ABANDONED.

        Args:
            session_id: Session ID.

        Returns:
            Updated session.

        Raises:
            SessionNotFoundError: If session not found.
        """
        if self._session_repo is None:
            raise RuntimeError("Session repository not configured")

        session = self._session_repo.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        session.closed_at = datetime.now(UTC)

        if session.pending_count == 0 and session.skipped_count == 0:
            session.status = ReconciliationSessionStatus.COMPLETED
        else:
            session.status = ReconciliationSessionStatus.ABANDONED

        self._session_repo.update(session)
        return session

    def get_session_summary(self, session_id: UUID) -> SessionSummary:
        """Get summary statistics for a session.

        Args:
            session_id: Session ID.

        Returns:
            Summary with counts for each status.

        Raises:
            SessionNotFoundError: If session not found.
        """
        if self._session_repo is None:
            raise RuntimeError("Session repository not configured")

        session = self._session_repo.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        total = len(session.matches)
        return SessionSummary(
            total_imported=total,
            pending=session.pending_count,
            confirmed=session.confirmed_count,
            rejected=session.rejected_count,
            skipped=session.skipped_count,
            match_rate=session.match_rate,
        )

    def _check_auto_close(self, session: ReconciliationSession) -> None:
        """Check if session should auto-close.

        Auto-closes when pending_count == 0 AND skipped_count == 0.
        """
        if session.pending_count == 0 and session.skipped_count == 0:
            session.status = ReconciliationSessionStatus.COMPLETED
            session.closed_at = datetime.now(UTC)
            if self._session_repo is not None:
                self._session_repo.update(session)
