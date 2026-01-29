"""QSBS (Qualified Small Business Stock) eligibility tracking service.

IRC §1202 allows exclusion of gain from QSBS held for more than 5 years.
Exclusion limit: greater of $10M or 10x adjusted basis per issuer.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from family_office_ledger.domain.entities import Position, Security
from family_office_ledger.domain.transactions import TaxLot
from family_office_ledger.repositories.interfaces import (
    PositionRepository,
    SecurityRepository,
    TaxLotRepository,
)


QSBS_HOLDING_PERIOD_DAYS = 5 * 365  # 5 years for full exclusion
QSBS_MAX_EXCLUSION = Decimal("10_000_000")  # $10M per issuer


class SecurityNotFoundError(Exception):
    pass


@dataclass
class QSBSHolding:
    security_id: UUID
    security_symbol: str
    security_name: str
    position_id: UUID
    acquisition_date: date
    quantity: Decimal
    cost_basis: Decimal
    holding_period_days: int
    is_qualified: bool  # True if held 5+ years
    days_until_qualified: int
    potential_exclusion: Decimal
    issuer: str | None


@dataclass
class QSBSSummary:
    total_qsbs_holdings: int
    qualified_holdings: int
    pending_holdings: int
    total_cost_basis: Decimal
    total_potential_exclusion: Decimal
    holdings: list[QSBSHolding]


class QSBSService:
    # IRC §1202: 5-year holding period, $10M or 10x basis exclusion
    HOLDING_PERIOD_DAYS = QSBS_HOLDING_PERIOD_DAYS
    MAX_EXCLUSION_PER_ISSUER = QSBS_MAX_EXCLUSION

    def __init__(
        self,
        security_repo: SecurityRepository,
        position_repo: PositionRepository,
        tax_lot_repo: TaxLotRepository,
    ) -> None:
        self._security_repo = security_repo
        self._position_repo = position_repo
        self._tax_lot_repo = tax_lot_repo

    def mark_security_qsbs_eligible(
        self,
        security_id: UUID,
        qualification_date: date,
    ) -> Security:
        security = self._security_repo.get(security_id)
        if security is None:
            raise SecurityNotFoundError(f"Security {security_id} not found")

        security.mark_qsbs_eligible(qualification_date)
        self._security_repo.update(security)
        return security

    def remove_qsbs_eligibility(self, security_id: UUID) -> Security:
        security = self._security_repo.get(security_id)
        if security is None:
            raise SecurityNotFoundError(f"Security {security_id} not found")

        security.is_qsbs_eligible = False
        security.qsbs_qualification_date = None
        self._security_repo.update(security)
        return security

    def list_qsbs_eligible_securities(self) -> list[Security]:
        return list(self._security_repo.list_qsbs_eligible())

    def get_qsbs_summary(
        self,
        entity_ids: list[UUID] | None = None,
        as_of_date: date | None = None,
    ) -> QSBSSummary:
        if as_of_date is None:
            as_of_date = date.today()

        qsbs_securities = {s.id: s for s in self._security_repo.list_qsbs_eligible()}
        if not qsbs_securities:
            return QSBSSummary(
                total_qsbs_holdings=0,
                qualified_holdings=0,
                pending_holdings=0,
                total_cost_basis=Decimal("0"),
                total_potential_exclusion=Decimal("0"),
                holdings=[],
            )

        holdings: list[QSBSHolding] = []

        for security_id, security in qsbs_securities.items():
            positions = list(self._position_repo.list_by_security(security_id))

            for position in positions:
                if position.quantity.is_zero:
                    continue

                lots = list(self._tax_lot_repo.list_open_by_position(position.id))

                for lot in lots:
                    if lot.remaining_quantity.is_zero:
                        continue

                    holding_days = (as_of_date - lot.acquisition_date).days
                    is_qualified = holding_days >= self.HOLDING_PERIOD_DAYS
                    days_until = max(0, self.HOLDING_PERIOD_DAYS - holding_days)

                    potential_exclusion = min(
                        self.MAX_EXCLUSION_PER_ISSUER,
                        lot.total_cost.amount * 10,
                    )

                    holdings.append(
                        QSBSHolding(
                            security_id=security.id,
                            security_symbol=security.symbol,
                            security_name=security.name,
                            position_id=position.id,
                            acquisition_date=lot.acquisition_date,
                            quantity=lot.remaining_quantity.value,
                            cost_basis=lot.total_cost.amount,
                            holding_period_days=holding_days,
                            is_qualified=is_qualified,
                            days_until_qualified=days_until,
                            potential_exclusion=potential_exclusion,
                            issuer=security.issuer,
                        )
                    )

        qualified = [h for h in holdings if h.is_qualified]
        pending = [h for h in holdings if not h.is_qualified]

        return QSBSSummary(
            total_qsbs_holdings=len(holdings),
            qualified_holdings=len(qualified),
            pending_holdings=len(pending),
            total_cost_basis=sum((h.cost_basis for h in holdings), Decimal("0")),
            total_potential_exclusion=sum(
                (h.potential_exclusion for h in holdings), Decimal("0")
            ),
            holdings=sorted(holdings, key=lambda h: h.days_until_qualified),
        )

    def calculate_exclusion_available(
        self,
        security_id: UUID,
        as_of_date: date | None = None,
    ) -> Decimal:
        if as_of_date is None:
            as_of_date = date.today()

        security = self._security_repo.get(security_id)
        if security is None or not security.is_qsbs_eligible:
            return Decimal("0")

        positions = list(self._position_repo.list_by_security(security_id))
        total_qualified_basis = Decimal("0")

        for position in positions:
            lots = list(self._tax_lot_repo.list_open_by_position(position.id))
            for lot in lots:
                holding_days = (as_of_date - lot.acquisition_date).days
                if holding_days >= self.HOLDING_PERIOD_DAYS:
                    total_qualified_basis += lot.total_cost.amount

        return min(
            self.MAX_EXCLUSION_PER_ISSUER,
            total_qualified_basis * 10,
        )


__all__ = [
    "QSBSService",
    "QSBSHolding",
    "QSBSSummary",
    "SecurityNotFoundError",
    "QSBS_HOLDING_PERIOD_DAYS",
    "QSBS_MAX_EXCLUSION",
]
