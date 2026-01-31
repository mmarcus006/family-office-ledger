"""Tax document generation service for Form 8949 and Schedule D."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from io import StringIO
from typing import Any
from uuid import UUID

from family_office_ledger.domain.value_objects import Money
from family_office_ledger.repositories.interfaces import (
    EntityRepository,
    PositionRepository,
    SecurityRepository,
    TaxLotRepository,
)
from family_office_ledger.services.interfaces import LotDisposition


class Form8949Box(str, Enum):
    """Form 8949 checkbox categories."""

    A = "A"  # Short-term, basis reported to IRS
    B = "B"  # Short-term, basis NOT reported to IRS
    C = "C"  # Short-term, Form 1099-B not received
    D = "D"  # Long-term, basis reported to IRS
    E = "E"  # Long-term, basis NOT reported to IRS
    F = "F"  # Long-term, Form 1099-B not received


class AdjustmentCode(str, Enum):
    """IRS adjustment codes for Form 8949 column (f)."""

    W = "W"  # Wash sale loss disallowed
    D = "D"  # Market discount
    E = "E"  # Accrued market discount as ordinary income
    H = "H"  # Short-term gain from installment sale
    L = "L"  # Long-term gain from installment sale
    M = "M"  # Multiple transactions on same date
    O = "O"  # Loss not allowed due to amount at risk
    Q = "Q"  # Nondeductible loss from wash sale
    S = "S"  # Exclusion of gain on sale of QSBS
    T = "T"  # Collectibles (28%) gain
    X = "X"  # Section 1256 60/40 split


@dataclass
class Form8949Entry:
    """Single entry on Form 8949."""

    description: str  # Column (a) - Description of property
    date_acquired: date  # Column (b)
    date_sold: date  # Column (c)
    proceeds: Money  # Column (d)
    cost_basis: Money  # Column (e)
    adjustment_code: AdjustmentCode | None = None  # Column (f)
    adjustment_amount: Money | None = None  # Column (g)
    lot_id: UUID | None = None
    is_covered: bool = True  # Basis reported to IRS

    @property
    def gain_or_loss(self) -> Money:
        """Column (h) - Gain or (loss)."""
        adjustment = self.adjustment_amount if self.adjustment_amount else Money.zero()
        return self.proceeds - self.cost_basis + adjustment

    @property
    def is_long_term(self) -> bool:
        """Whether holding period exceeds 1 year."""
        return (self.date_sold - self.date_acquired).days > 365

    @property
    def box(self) -> Form8949Box:
        """Determine which Form 8949 box this entry belongs to."""
        if self.is_long_term:
            if self.is_covered:
                return Form8949Box.D
            else:
                return Form8949Box.E
        else:
            if self.is_covered:
                return Form8949Box.A
            else:
                return Form8949Box.B


@dataclass
class Form8949Part:
    """One part of Form 8949 (Part I short-term or Part II long-term)."""

    box: Form8949Box
    entries: list[Form8949Entry] = field(default_factory=list)

    @property
    def total_proceeds(self) -> Money:
        if not self.entries:
            return Money.zero()
        currency = self.entries[0].proceeds.currency
        return Money(
            sum((e.proceeds.amount for e in self.entries), Decimal("0")),
            currency,
        )

    @property
    def total_cost_basis(self) -> Money:
        if not self.entries:
            return Money.zero()
        currency = self.entries[0].cost_basis.currency
        return Money(
            sum((e.cost_basis.amount for e in self.entries), Decimal("0")),
            currency,
        )

    @property
    def total_adjustments(self) -> Money:
        if not self.entries:
            return Money.zero()
        currency = self.entries[0].proceeds.currency
        total = Decimal("0")
        for e in self.entries:
            if e.adjustment_amount:
                total += e.adjustment_amount.amount
        return Money(total, currency)

    @property
    def total_gain_or_loss(self) -> Money:
        if not self.entries:
            return Money.zero()
        currency = self.entries[0].proceeds.currency
        return Money(
            sum((e.gain_or_loss.amount for e in self.entries), Decimal("0")),
            currency,
        )

    @property
    def is_short_term(self) -> bool:
        return self.box in (Form8949Box.A, Form8949Box.B, Form8949Box.C)


@dataclass
class Form8949:
    """IRS Form 8949 - Sales and Other Dispositions of Capital Assets."""

    tax_year: int
    taxpayer_name: str
    taxpayer_ssn: str | None = None
    parts: list[Form8949Part] = field(default_factory=list)

    @property
    def short_term_parts(self) -> list[Form8949Part]:
        """Part I - Short-term transactions."""
        return [p for p in self.parts if p.is_short_term]

    @property
    def long_term_parts(self) -> list[Form8949Part]:
        """Part II - Long-term transactions."""
        return [p for p in self.parts if not p.is_short_term]

    @property
    def total_short_term_proceeds(self) -> Money:
        parts = self.short_term_parts
        if not parts:
            return Money.zero()
        return Money(
            sum((p.total_proceeds.amount for p in parts), Decimal("0")),
            "USD",
        )

    @property
    def total_short_term_cost_basis(self) -> Money:
        parts = self.short_term_parts
        if not parts:
            return Money.zero()
        return Money(
            sum((p.total_cost_basis.amount for p in parts), Decimal("0")),
            "USD",
        )

    @property
    def total_short_term_gain_or_loss(self) -> Money:
        parts = self.short_term_parts
        if not parts:
            return Money.zero()
        return Money(
            sum((p.total_gain_or_loss.amount for p in parts), Decimal("0")),
            "USD",
        )

    @property
    def total_long_term_proceeds(self) -> Money:
        parts = self.long_term_parts
        if not parts:
            return Money.zero()
        return Money(
            sum((p.total_proceeds.amount for p in parts), Decimal("0")),
            "USD",
        )

    @property
    def total_long_term_cost_basis(self) -> Money:
        parts = self.long_term_parts
        if not parts:
            return Money.zero()
        return Money(
            sum((p.total_cost_basis.amount for p in parts), Decimal("0")),
            "USD",
        )

    @property
    def total_long_term_gain_or_loss(self) -> Money:
        parts = self.long_term_parts
        if not parts:
            return Money.zero()
        return Money(
            sum((p.total_gain_or_loss.amount for p in parts), Decimal("0")),
            "USD",
        )


@dataclass
class ScheduleD:
    """IRS Schedule D - Capital Gains and Losses."""

    tax_year: int
    taxpayer_name: str

    # Part I - Short-Term Capital Gains and Losses
    line_1a: Money = field(default_factory=Money.zero)  # From Form 8949 Box A
    line_1b: Money = field(default_factory=Money.zero)  # From Form 8949 Box B
    line_1c: Money = field(default_factory=Money.zero)  # From Form 8949 Box C

    # Part II - Long-Term Capital Gains and Losses
    line_8a: Money = field(default_factory=Money.zero)  # From Form 8949 Box D
    line_8b: Money = field(default_factory=Money.zero)  # From Form 8949 Box E
    line_8c: Money = field(default_factory=Money.zero)  # From Form 8949 Box F

    @property
    def line_7(self) -> Money:
        """Net short-term capital gain or (loss)."""
        return Money(
            self.line_1a.amount + self.line_1b.amount + self.line_1c.amount,
            "USD",
        )

    @property
    def line_15(self) -> Money:
        """Net long-term capital gain or (loss)."""
        return Money(
            self.line_8a.amount + self.line_8b.amount + self.line_8c.amount,
            "USD",
        )

    @property
    def line_16(self) -> Money:
        """Combine lines 7 and 15."""
        return Money(
            self.line_7.amount + self.line_15.amount,
            "USD",
        )


@dataclass
class TaxDocumentSummary:
    """Summary of generated tax documents."""

    tax_year: int
    entity_name: str
    short_term_transactions: int
    long_term_transactions: int
    total_short_term_proceeds: Money
    total_short_term_cost_basis: Money
    total_short_term_gain: Money
    total_long_term_proceeds: Money
    total_long_term_cost_basis: Money
    total_long_term_gain: Money
    wash_sale_adjustments: Money
    net_capital_gain: Money


class TaxDocumentService:
    """Service for generating IRS tax documents (Form 8949, Schedule D)."""

    def __init__(
        self,
        entity_repo: EntityRepository,
        position_repo: PositionRepository,
        tax_lot_repo: TaxLotRepository,
        security_repo: SecurityRepository,
    ) -> None:
        self._entity_repo = entity_repo
        self._position_repo = position_repo
        self._tax_lot_repo = tax_lot_repo
        self._security_repo = security_repo

    def generate_form_8949(
        self,
        dispositions: list[LotDisposition],
        tax_year: int,
        taxpayer_name: str,
        taxpayer_ssn: str | None = None,
        security_descriptions: dict[UUID, str] | None = None,
    ) -> Form8949:
        """
        Generate Form 8949 from lot dispositions.

        Args:
            dispositions: List of lot dispositions with proceeds
            tax_year: Tax year for the form
            taxpayer_name: Name of taxpayer
            taxpayer_ssn: Social security number (optional)
            security_descriptions: Mapping of lot_id to security description

        Returns:
            Form8949 with entries grouped by box type
        """
        year_start = date(tax_year, 1, 1)
        year_end = date(tax_year, 12, 31)

        year_dispositions = [
            d for d in dispositions if year_start <= d.disposition_date <= year_end
        ]

        entries: list[Form8949Entry] = []
        for disp in year_dispositions:
            description = "Security"
            if security_descriptions and disp.lot_id in security_descriptions:
                description = security_descriptions[disp.lot_id]

            entry = Form8949Entry(
                description=description,
                date_acquired=disp.acquisition_date,
                date_sold=disp.disposition_date,
                proceeds=disp.proceeds,
                cost_basis=disp.cost_basis,
                lot_id=disp.lot_id,
            )
            entries.append(entry)

        box_entries: dict[Form8949Box, list[Form8949Entry]] = {}
        for entry in entries:
            box = entry.box
            if box not in box_entries:
                box_entries[box] = []
            box_entries[box].append(entry)

        parts: list[Form8949Part] = []
        for box in Form8949Box:
            if box in box_entries:
                parts.append(Form8949Part(box=box, entries=box_entries[box]))

        return Form8949(
            tax_year=tax_year,
            taxpayer_name=taxpayer_name,
            taxpayer_ssn=taxpayer_ssn,
            parts=parts,
        )

    def generate_schedule_d(self, form_8949: Form8949) -> ScheduleD:
        """
        Generate Schedule D from Form 8949.

        Args:
            form_8949: Completed Form 8949

        Returns:
            ScheduleD with totals from Form 8949
        """
        schedule = ScheduleD(
            tax_year=form_8949.tax_year,
            taxpayer_name=form_8949.taxpayer_name,
        )

        for part in form_8949.parts:
            gain = part.total_gain_or_loss
            if part.box == Form8949Box.A:
                schedule.line_1a = gain
            elif part.box == Form8949Box.B:
                schedule.line_1b = gain
            elif part.box == Form8949Box.C:
                schedule.line_1c = gain
            elif part.box == Form8949Box.D:
                schedule.line_8a = gain
            elif part.box == Form8949Box.E:
                schedule.line_8b = gain
            elif part.box == Form8949Box.F:
                schedule.line_8c = gain

        return schedule

    def generate_from_entity(
        self,
        entity_id: UUID,
        tax_year: int,
        lot_proceeds: dict[UUID, Money] | None = None,
    ) -> tuple[Form8949, ScheduleD, TaxDocumentSummary]:
        """
        Generate tax documents for an entity's disposed lots.

        Args:
            entity_id: Entity to generate documents for
            tax_year: Tax year
            lot_proceeds: Mapping of lot_id to sale proceeds (required for gain calc)

        Returns:
            Tuple of (Form8949, ScheduleD, TaxDocumentSummary)
        """
        entity = self._entity_repo.get(entity_id)
        if entity is None:
            raise ValueError(f"Entity not found: {entity_id}")

        positions = list(self._position_repo.list_by_entity(entity_id))
        dispositions: list[LotDisposition] = []
        security_descriptions: dict[UUID, str] = {}
        wash_sale_total = Decimal("0")

        year_start = date(tax_year, 1, 1)
        year_end = date(tax_year, 12, 31)

        for position in positions:
            security = self._security_repo.get(position.security_id)
            security_desc = (
                f"{security.symbol} - {security.name}"
                if security
                else "Unknown Security"
            )

            lots = list(self._tax_lot_repo.list_by_position(position.id))

            for lot in lots:
                if lot.disposition_date is None:
                    continue
                if not (year_start <= lot.disposition_date <= year_end):
                    continue
                if not lot.is_fully_disposed:
                    continue

                if lot_proceeds and lot.id in lot_proceeds:
                    proceeds = lot_proceeds[lot.id]
                else:
                    proceeds = lot.total_cost

                security_descriptions[lot.id] = security_desc

                if lot.wash_sale_disallowed:
                    wash_sale_total += lot.wash_sale_adjustment.amount

                disp = LotDisposition(
                    lot_id=lot.id,
                    quantity_sold=lot.original_quantity,
                    cost_basis=lot.total_cost,
                    proceeds=proceeds,
                    acquisition_date=lot.acquisition_date,
                    disposition_date=lot.disposition_date,
                )
                dispositions.append(disp)

        form_8949 = self.generate_form_8949(
            dispositions=dispositions,
            tax_year=tax_year,
            taxpayer_name=entity.name,
            security_descriptions=security_descriptions,
        )

        schedule_d = self.generate_schedule_d(form_8949)
        short_term_count = sum(len(p.entries) for p in form_8949.short_term_parts)
        long_term_count = sum(len(p.entries) for p in form_8949.long_term_parts)

        summary = TaxDocumentSummary(
            tax_year=tax_year,
            entity_name=entity.name,
            short_term_transactions=short_term_count,
            long_term_transactions=long_term_count,
            total_short_term_proceeds=form_8949.total_short_term_proceeds,
            total_short_term_cost_basis=form_8949.total_short_term_cost_basis,
            total_short_term_gain=form_8949.total_short_term_gain_or_loss,
            total_long_term_proceeds=form_8949.total_long_term_proceeds,
            total_long_term_cost_basis=form_8949.total_long_term_cost_basis,
            total_long_term_gain=form_8949.total_long_term_gain_or_loss,
            wash_sale_adjustments=Money(wash_sale_total, "USD"),
            net_capital_gain=schedule_d.line_16,
        )

        return form_8949, schedule_d, summary

    def export_form_8949_csv(
        self,
        form_8949: Form8949,
        output_path: str | None = None,
    ) -> str:
        """
        Export Form 8949 to CSV format for tax software import.

        Args:
            form_8949: Form 8949 to export
            output_path: Path to write CSV (if None, returns string)

        Returns:
            CSV content as string
        """
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "Description",
                "Date Acquired",
                "Date Sold",
                "Proceeds",
                "Cost Basis",
                "Adjustment Code",
                "Adjustment Amount",
                "Gain/Loss",
                "Term",
                "Box",
            ]
        )

        for part in form_8949.parts:
            term = "Short-term" if part.is_short_term else "Long-term"
            for entry in part.entries:
                writer.writerow(
                    [
                        entry.description,
                        entry.date_acquired.isoformat(),
                        entry.date_sold.isoformat(),
                        str(entry.proceeds.amount),
                        str(entry.cost_basis.amount),
                        entry.adjustment_code.value if entry.adjustment_code else "",
                        str(entry.adjustment_amount.amount)
                        if entry.adjustment_amount
                        else "",
                        str(entry.gain_or_loss.amount),
                        term,
                        part.box.value,
                    ]
                )

        csv_content = output.getvalue()

        if output_path:
            with open(output_path, "w", newline="") as f:
                f.write(csv_content)

        return csv_content

    def export_schedule_d_summary(
        self,
        schedule_d: ScheduleD,
    ) -> dict[str, Any]:
        """
        Export Schedule D as a summary dictionary.

        Args:
            schedule_d: Schedule D to export

        Returns:
            Dictionary with Schedule D line items
        """
        return {
            "tax_year": schedule_d.tax_year,
            "taxpayer_name": schedule_d.taxpayer_name,
            "part_i_short_term": {
                "line_1a_box_a": str(schedule_d.line_1a.amount),
                "line_1b_box_b": str(schedule_d.line_1b.amount),
                "line_1c_box_c": str(schedule_d.line_1c.amount),
                "line_7_net_short_term": str(schedule_d.line_7.amount),
            },
            "part_ii_long_term": {
                "line_8a_box_d": str(schedule_d.line_8a.amount),
                "line_8b_box_e": str(schedule_d.line_8b.amount),
                "line_8c_box_f": str(schedule_d.line_8c.amount),
                "line_15_net_long_term": str(schedule_d.line_15.amount),
            },
            "line_16_combined": str(schedule_d.line_16.amount),
        }

    def get_tax_document_summary(
        self,
        entity_id: UUID,
        tax_year: int,
        lot_proceeds: dict[UUID, Money] | None = None,
    ) -> TaxDocumentSummary:
        """
        Get summary of tax documents without generating full forms.

        Args:
            entity_id: Entity to summarize
            tax_year: Tax year
            lot_proceeds: Optional mapping of lot_id to proceeds

        Returns:
            TaxDocumentSummary with totals
        """
        _, _, summary = self.generate_from_entity(entity_id, tax_year, lot_proceeds)
        return summary
