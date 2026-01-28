"""Lot matching service implementation for tax lot selection and disposition."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from family_office_ledger.domain.transactions import TaxLot
from family_office_ledger.domain.value_objects import LotSelection, Money, Quantity
from family_office_ledger.repositories.interfaces import (
    PositionRepository,
    TaxLotRepository,
)
from family_office_ledger.services.interfaces import LotDisposition, LotMatchingService


class InsufficientLotsError(Exception):
    """Raised when there are not enough shares in open lots to fulfill a sale."""

    pass


class InvalidLotSelectionError(Exception):
    """Raised when a specific lot ID is not found or the lot is already closed."""

    pass


class LotMatchingServiceImpl(LotMatchingService):
    """Implementation of lot matching service for tax lot selection and disposition."""

    def __init__(
        self,
        tax_lot_repo: TaxLotRepository,
        position_repo: PositionRepository,
    ) -> None:
        self._tax_lot_repo = tax_lot_repo
        self._position_repo = position_repo

    def get_open_lots(self, position_id: UUID) -> list[TaxLot]:
        """Returns all open lots for a position."""
        return list(self._tax_lot_repo.list_open_by_position(position_id))

    def get_position_cost_basis(self, position_id: UUID) -> Money:
        """Sums remaining cost of all open lots for a position."""
        open_lots = self.get_open_lots(position_id)
        if not open_lots:
            return Money.zero()

        total = Decimal("0")
        currency = "USD"
        for lot in open_lots:
            total += lot.remaining_cost.amount
            currency = lot.remaining_cost.currency

        return Money(total, currency)

    def match_sale(
        self,
        position_id: UUID,
        quantity: Quantity,
        method: LotSelection,
        specific_lot_ids: list[UUID] | None = None,
    ) -> list[TaxLot]:
        """Returns list of lots to sell based on the specified method."""
        open_lots = self.get_open_lots(position_id)

        if method == LotSelection.SPECIFIC_ID:
            return self._match_specific_id(open_lots, quantity, specific_lot_ids or [])
        elif method == LotSelection.AVERAGE_COST:
            return self._match_average_cost(open_lots, quantity)
        else:
            sorted_lots = self._sort_lots_by_method(open_lots, method)
            return self._select_lots_for_quantity(sorted_lots, quantity)

    def execute_sale(
        self,
        position_id: UUID,
        quantity: Quantity,
        proceeds: Money,
        sale_date: date,
        method: LotSelection,
        specific_lot_ids: list[UUID] | None = None,
    ) -> list[LotDisposition]:
        """Executes a sale by disposing lots and returning disposition records."""
        matched_lots = self.match_sale(position_id, quantity, method, specific_lot_ids)

        if method == LotSelection.AVERAGE_COST:
            return self._execute_average_cost_sale(
                matched_lots, quantity, proceeds, sale_date
            )
        else:
            return self._execute_standard_sale(
                matched_lots, quantity, proceeds, sale_date
            )

    def detect_wash_sales(
        self,
        position_id: UUID,
        sale_date: date,
        loss_amount: Money,
    ) -> list[TaxLot]:
        """Finds replacement lots within 30 days that trigger wash sale rules."""
        # Wash sales only apply to losses, not gains
        if loss_amount.amount <= Decimal("0"):
            return []

        candidates = list(
            self._tax_lot_repo.list_wash_sale_candidates(position_id, sale_date)
        )
        return candidates

    def _match_specific_id(
        self,
        open_lots: list[TaxLot],
        quantity: Quantity,
        specific_lot_ids: list[UUID],
    ) -> list[TaxLot]:
        """Match lots by specific IDs."""
        open_lot_map = {lot.id: lot for lot in open_lots}
        selected_lots: list[TaxLot] = []
        total_available = Decimal("0")

        for lot_id in specific_lot_ids:
            if lot_id not in open_lot_map:
                # Check if lot exists but is closed
                lot = self._tax_lot_repo.get(lot_id)
                if lot is not None and lot.is_fully_disposed:
                    raise InvalidLotSelectionError(
                        f"Lot {lot_id} is already fully disposed"
                    )
                raise InvalidLotSelectionError(f"Lot {lot_id} not found or not open")

            selected_lot = open_lot_map[lot_id]
            selected_lots.append(selected_lot)
            total_available += selected_lot.remaining_quantity.value

        if total_available < quantity.value:
            raise InsufficientLotsError(
                f"Insufficient quantity in specified lots: "
                f"requested {quantity.value}, available {total_available}"
            )

        return selected_lots

    def _match_average_cost(
        self,
        open_lots: list[TaxLot],
        quantity: Quantity,
    ) -> list[TaxLot]:
        """Match all open lots for average cost method (pro-rata allocation)."""
        total_available = sum(lot.remaining_quantity.value for lot in open_lots)

        if total_available < quantity.value:
            raise InsufficientLotsError(
                f"Insufficient quantity in open lots: "
                f"requested {quantity.value}, available {total_available}"
            )

        return open_lots

    def _sort_lots_by_method(
        self,
        lots: list[TaxLot],
        method: LotSelection,
    ) -> list[TaxLot]:
        """Sort lots according to the specified selection method."""
        if method == LotSelection.FIFO:
            return sorted(lots, key=lambda lot: lot.acquisition_date)
        elif method == LotSelection.LIFO:
            return sorted(lots, key=lambda lot: lot.acquisition_date, reverse=True)
        elif method == LotSelection.HIFO:
            return sorted(lots, key=lambda lot: lot.cost_per_share.amount, reverse=True)
        elif method == LotSelection.MINIMIZE_GAIN:
            # Higher cost = lower gain, so sort by cost descending
            return sorted(lots, key=lambda lot: lot.cost_per_share.amount, reverse=True)
        elif method == LotSelection.MAXIMIZE_GAIN:
            # Lower cost = higher gain, so sort by cost ascending
            return sorted(lots, key=lambda lot: lot.cost_per_share.amount)
        else:
            # Default to FIFO
            return sorted(lots, key=lambda lot: lot.acquisition_date)

    def _select_lots_for_quantity(
        self,
        sorted_lots: list[TaxLot],
        quantity: Quantity,
    ) -> list[TaxLot]:
        """Select lots to fulfill the required quantity."""
        selected_lots: list[TaxLot] = []
        remaining_quantity = quantity.value

        for lot in sorted_lots:
            if remaining_quantity <= Decimal("0"):
                break

            selected_lots.append(lot)
            remaining_quantity -= lot.remaining_quantity.value

        if remaining_quantity > Decimal("0"):
            total_available = sum(lot.remaining_quantity.value for lot in sorted_lots)
            raise InsufficientLotsError(
                f"Insufficient quantity in open lots: "
                f"requested {quantity.value}, available {total_available}"
            )

        return selected_lots

    def _execute_standard_sale(
        self,
        matched_lots: list[TaxLot],
        quantity: Quantity,
        proceeds: Money,
        sale_date: date,
    ) -> list[LotDisposition]:
        """Execute a standard (non-average cost) sale."""
        dispositions: list[LotDisposition] = []
        remaining_quantity = quantity.value
        total_quantity = quantity.value

        for lot in matched_lots:
            if remaining_quantity <= Decimal("0"):
                break

            # Determine how many shares to sell from this lot
            sell_qty = min(remaining_quantity, lot.remaining_quantity.value)
            sell_quantity = Quantity(sell_qty)

            # Calculate cost basis for this disposition
            cost_basis = lot.sell(sell_quantity, sale_date)

            # Calculate proportional proceeds
            proportion = sell_qty / total_quantity
            lot_proceeds = Money(
                (proceeds.amount * proportion).quantize(Decimal("0.01")),
                proceeds.currency,
            )

            # Create disposition record
            disposition = LotDisposition(
                lot_id=lot.id,
                quantity_sold=sell_quantity,
                cost_basis=cost_basis,
                proceeds=lot_proceeds,
                acquisition_date=lot.acquisition_date,
                disposition_date=sale_date,
            )
            dispositions.append(disposition)

            # Update lot in repository
            self._tax_lot_repo.update(lot)

            remaining_quantity -= sell_qty

        return dispositions

    def _execute_average_cost_sale(
        self,
        matched_lots: list[TaxLot],
        quantity: Quantity,
        proceeds: Money,
        sale_date: date,
    ) -> list[LotDisposition]:
        """Execute an average cost sale (pro-rata from all lots)."""
        # Calculate total quantity and cost basis
        total_quantity: Decimal = sum(
            (lot.remaining_quantity.value for lot in matched_lots), Decimal("0")
        )
        total_cost: Decimal = sum(
            (lot.remaining_cost.amount for lot in matched_lots), Decimal("0")
        )

        # Calculate average cost per share
        avg_cost_per_share: Decimal = Decimal(str(total_cost / total_quantity))

        # Calculate the fraction of total position being sold
        sell_fraction = quantity.value / total_quantity

        dispositions: list[LotDisposition] = []
        quantity_sold_so_far = Decimal("0")
        lots_count = len(matched_lots)

        for i, lot in enumerate(matched_lots):
            is_last_lot = i == lots_count - 1

            # Calculate pro-rata quantity from this lot
            if is_last_lot:
                # Last lot gets the remainder to avoid rounding issues
                sell_qty = quantity.value - quantity_sold_so_far
            else:
                sell_qty = (lot.remaining_quantity.value * sell_fraction).quantize(
                    Decimal("0.0001")
                )

            if sell_qty <= Decimal("0"):
                continue

            sell_quantity = Quantity(sell_qty)

            # Calculate cost basis using average cost
            cost_basis = Money(
                (avg_cost_per_share * sell_qty).quantize(Decimal("0.01")),
                lot.cost_per_share.currency,
            )

            # Calculate proportional proceeds
            proportion = sell_qty / quantity.value
            lot_proceeds = Money(
                (proceeds.amount * proportion).quantize(Decimal("0.01")),
                proceeds.currency,
            )

            # Sell from the lot (this updates remaining_quantity)
            lot.sell(sell_quantity, sale_date)

            # Create disposition record
            disposition = LotDisposition(
                lot_id=lot.id,
                quantity_sold=sell_quantity,
                cost_basis=cost_basis,
                proceeds=lot_proceeds,
                acquisition_date=lot.acquisition_date,
                disposition_date=sale_date,
            )
            dispositions.append(disposition)

            # Update lot in repository
            self._tax_lot_repo.update(lot)

            quantity_sold_so_far += sell_qty

        return dispositions
