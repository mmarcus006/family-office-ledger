"""Corporate action service implementation."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from family_office_ledger.domain.transactions import TaxLot
from family_office_ledger.domain.value_objects import AcquisitionType, Money, Quantity
from family_office_ledger.repositories.interfaces import (
    PositionRepository,
    SecurityRepository,
    TaxLotRepository,
)
from family_office_ledger.services.interfaces import CorporateActionService


class CorporateActionServiceImpl(CorporateActionService):
    """Implementation of the CorporateActionService interface."""

    def __init__(
        self,
        tax_lot_repo: TaxLotRepository,
        position_repo: PositionRepository,
        security_repo: SecurityRepository,
    ) -> None:
        self._tax_lot_repo = tax_lot_repo
        self._position_repo = position_repo
        self._security_repo = security_repo

    def apply_split(
        self,
        security_id: UUID,
        ratio_numerator: Decimal,
        ratio_denominator: Decimal,
        effective_date: date,
    ) -> int:
        """Apply a stock split to all open lots for the security.

        For each open lot, multiplies quantity by ratio and divides
        cost_per_share by ratio, preserving total cost basis.

        Args:
            security_id: The security undergoing the split.
            ratio_numerator: Split ratio numerator (e.g., 2 for 2-for-1).
            ratio_denominator: Split ratio denominator (e.g., 1 for 2-for-1).
            effective_date: The date the split is effective.

        Returns:
            Number of lots affected by the split.
        """
        affected_count = 0

        # Get all positions for this security
        positions = list(self._position_repo.list_by_security(security_id))

        for position in positions:
            # Get all open lots for this position
            open_lots = list(self._tax_lot_repo.list_open_by_position(position.id))

            for lot in open_lots:
                # Use the TaxLot's built-in apply_split method
                lot.apply_split(ratio_numerator, ratio_denominator)
                self._tax_lot_repo.update(lot)
                affected_count += 1

        return affected_count

    def apply_spinoff(
        self,
        parent_security_id: UUID,
        child_security_id: UUID,
        allocation_ratio: Decimal,
        effective_date: date,
    ) -> int:
        """Apply a spinoff, allocating cost basis to the child security.

        Creates new lots for the child security with a portion of the parent's
        cost basis. The parent lots' cost basis is reduced accordingly.

        Args:
            parent_security_id: The security spinning off the child.
            child_security_id: The new child security being created.
            allocation_ratio: Portion of cost basis to allocate to child (0-1).
            effective_date: The date the spinoff is effective.

        Returns:
            Number of parent lots affected (and child lots created).
        """
        affected_count = 0

        # Get parent positions
        parent_positions = list(
            self._position_repo.list_by_security(parent_security_id)
        )

        for parent_position in parent_positions:
            # Find or get the child position for the same account
            child_position = self._position_repo.get_by_account_and_security(
                parent_position.account_id, child_security_id
            )

            if child_position is None:
                continue  # Skip if no child position exists

            # Get open lots for parent position
            open_lots = list(
                self._tax_lot_repo.list_open_by_position(parent_position.id)
            )

            for parent_lot in open_lots:
                # Calculate cost basis allocation
                parent_cost_per_share = parent_lot.cost_per_share
                child_cost_per_share = Money(
                    parent_cost_per_share.amount * allocation_ratio,
                    parent_cost_per_share.currency,
                )
                new_parent_cost_per_share = Money(
                    parent_cost_per_share.amount * (1 - allocation_ratio),
                    parent_cost_per_share.currency,
                )

                # Update parent lot cost basis
                parent_lot.cost_per_share = new_parent_cost_per_share
                self._tax_lot_repo.update(parent_lot)

                # Create child lot
                child_lot = TaxLot(
                    position_id=child_position.id,
                    acquisition_date=parent_lot.acquisition_date,
                    cost_per_share=child_cost_per_share,
                    original_quantity=parent_lot.original_quantity,
                    acquisition_type=AcquisitionType.SPINOFF,
                    is_covered=parent_lot.is_covered,
                )
                # Set remaining quantity to match the proportion
                child_lot.remaining_quantity = parent_lot.remaining_quantity
                self._tax_lot_repo.add(child_lot)

                affected_count += 1

        return affected_count

    def apply_merger(
        self,
        old_security_id: UUID,
        new_security_id: UUID,
        exchange_ratio: Decimal,
        effective_date: date,
        cash_in_lieu_per_share: Money | None = None,
    ) -> int:
        """Apply a merger, converting lots to the new security.

        Creates new lots for the new security based on the exchange ratio.
        The old lots are closed. Cash in lieu reduces the cost basis.

        Args:
            old_security_id: The security being acquired/merged.
            new_security_id: The acquiring/surviving security.
            exchange_ratio: Number of new shares per old share.
            effective_date: The date the merger is effective.
            cash_in_lieu_per_share: Optional cash payment per old share.

        Returns:
            Number of lots converted.
        """
        affected_count = 0

        # Get old positions
        old_positions = list(self._position_repo.list_by_security(old_security_id))

        for old_position in old_positions:
            # Find the new position for the same account
            new_position = self._position_repo.get_by_account_and_security(
                old_position.account_id, new_security_id
            )

            if new_position is None:
                continue  # Skip if no new position exists

            # Get open lots for old position
            open_lots = list(self._tax_lot_repo.list_open_by_position(old_position.id))

            for old_lot in open_lots:
                # Calculate new quantity
                old_quantity = old_lot.remaining_quantity
                new_quantity = Quantity(old_quantity.value * exchange_ratio)

                # Calculate cost basis
                old_cost_basis = old_lot.cost_per_share * old_quantity.value

                # Adjust for cash in lieu if present
                if cash_in_lieu_per_share is not None:
                    cash_received = cash_in_lieu_per_share * old_quantity.value
                    adjusted_cost_basis = Money(
                        old_cost_basis.amount - cash_received.amount,
                        old_cost_basis.currency,
                    )
                else:
                    adjusted_cost_basis = old_cost_basis

                # Calculate new cost per share
                new_cost_per_share = Money(
                    adjusted_cost_basis.amount / new_quantity.value,
                    adjusted_cost_basis.currency,
                )

                # Close old lot by selling all remaining shares
                old_lot.sell(old_quantity, effective_date)
                self._tax_lot_repo.update(old_lot)

                # Create new lot
                new_lot = TaxLot(
                    position_id=new_position.id,
                    acquisition_date=old_lot.acquisition_date,
                    cost_per_share=new_cost_per_share,
                    original_quantity=new_quantity,
                    acquisition_type=AcquisitionType.MERGER,
                    is_covered=old_lot.is_covered,
                )
                self._tax_lot_repo.add(new_lot)

                affected_count += 1

        return affected_count

    def apply_symbol_change(
        self,
        security_id: UUID,
        new_symbol: str,
        effective_date: date,
    ) -> None:
        """Apply a symbol change to a security.

        Updates the security's symbol. This does not affect lots.

        Args:
            security_id: The security changing symbols.
            new_symbol: The new ticker symbol.
            effective_date: The date the change is effective.
        """
        security = self._security_repo.get(security_id)
        if security is not None:
            security.symbol = new_symbol
            self._security_repo.update(security)
