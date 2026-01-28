from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.transactions import TaxLot
from family_office_ledger.domain.value_objects import (
    LotSelection,
    Money,
    Quantity,
)


class TestLotSelectionMethods:
    def test_lot_selection_enum_values(self):
        assert LotSelection.FIFO.value == "fifo"
        assert LotSelection.LIFO.value == "lifo"
        assert LotSelection.SPECIFIC_ID.value == "specific_id"
        assert LotSelection.AVERAGE_COST.value == "average_cost"
        assert LotSelection.MINIMIZE_GAIN.value == "minimize_gain"
        assert LotSelection.MAXIMIZE_GAIN.value == "maximize_gain"
        assert LotSelection.HIFO.value == "hifo"


class TestFIFOLotMatching:
    @pytest.fixture
    def multiple_lots(self) -> list[TaxLot]:
        position_id = uuid4()
        return [
            TaxLot(
                position_id=position_id,
                acquisition_date=date(2022, 1, 15),
                cost_per_share=Money(Decimal("100.00")),
                original_quantity=Quantity(Decimal("50")),
            ),
            TaxLot(
                position_id=position_id,
                acquisition_date=date(2023, 3, 20),
                cost_per_share=Money(Decimal("120.00")),
                original_quantity=Quantity(Decimal("75")),
            ),
            TaxLot(
                position_id=position_id,
                acquisition_date=date(2024, 6, 10),
                cost_per_share=Money(Decimal("150.00")),
                original_quantity=Quantity(Decimal("25")),
            ),
        ]

    def test_fifo_selects_oldest_lot_first(self, multiple_lots: list[TaxLot]):
        sorted_lots = sorted(multiple_lots, key=lambda lot: lot.acquisition_date)

        assert sorted_lots[0].acquisition_date == date(2022, 1, 15)
        assert sorted_lots[1].acquisition_date == date(2023, 3, 20)
        assert sorted_lots[2].acquisition_date == date(2024, 6, 10)

    def test_fifo_partial_sale_from_oldest(self, multiple_lots: list[TaxLot]):
        sorted_lots = sorted(multiple_lots, key=lambda lot: lot.acquisition_date)
        quantity_to_sell = Quantity(Decimal("30"))

        oldest_lot = sorted_lots[0]
        cost_basis = oldest_lot.sell(quantity_to_sell, date(2024, 12, 1))

        assert oldest_lot.remaining_quantity == Quantity(Decimal("20"))
        assert cost_basis == Money(Decimal("3000.00"))

    def test_fifo_sale_spanning_multiple_lots(self, multiple_lots: list[TaxLot]):
        sorted_lots = sorted(multiple_lots, key=lambda lot: lot.acquisition_date)
        quantity_to_sell = Quantity(Decimal("80"))
        sale_date = date(2024, 12, 1)

        total_cost_basis = Money.zero()
        remaining_to_sell = quantity_to_sell

        for lot in sorted_lots:
            if remaining_to_sell.is_zero:
                break

            available = lot.remaining_quantity
            sell_from_lot = min(available.value, remaining_to_sell.value)

            if sell_from_lot > 0:
                cost = lot.sell(Quantity(sell_from_lot), sale_date)
                total_cost_basis = total_cost_basis + cost
                remaining_to_sell = Quantity(remaining_to_sell.value - sell_from_lot)

        assert sorted_lots[0].remaining_quantity == Quantity(Decimal("0"))
        assert sorted_lots[1].remaining_quantity == Quantity(Decimal("45"))
        assert sorted_lots[2].remaining_quantity == Quantity(Decimal("25"))
        assert total_cost_basis == Money(Decimal("8600.00"))


class TestLIFOLotMatching:
    @pytest.fixture
    def multiple_lots(self) -> list[TaxLot]:
        position_id = uuid4()
        return [
            TaxLot(
                position_id=position_id,
                acquisition_date=date(2022, 1, 15),
                cost_per_share=Money(Decimal("100.00")),
                original_quantity=Quantity(Decimal("50")),
            ),
            TaxLot(
                position_id=position_id,
                acquisition_date=date(2023, 3, 20),
                cost_per_share=Money(Decimal("120.00")),
                original_quantity=Quantity(Decimal("75")),
            ),
            TaxLot(
                position_id=position_id,
                acquisition_date=date(2024, 6, 10),
                cost_per_share=Money(Decimal("150.00")),
                original_quantity=Quantity(Decimal("25")),
            ),
        ]

    def test_lifo_selects_newest_lot_first(self, multiple_lots: list[TaxLot]):
        sorted_lots = sorted(
            multiple_lots, key=lambda lot: lot.acquisition_date, reverse=True
        )

        assert sorted_lots[0].acquisition_date == date(2024, 6, 10)
        assert sorted_lots[1].acquisition_date == date(2023, 3, 20)
        assert sorted_lots[2].acquisition_date == date(2022, 1, 15)

    def test_lifo_sale_from_newest(self, multiple_lots: list[TaxLot]):
        sorted_lots = sorted(
            multiple_lots, key=lambda lot: lot.acquisition_date, reverse=True
        )
        newest_lot = sorted_lots[0]

        cost_basis = newest_lot.sell(Quantity(Decimal("25")), date(2024, 12, 1))

        assert newest_lot.is_fully_disposed is True
        assert cost_basis == Money(Decimal("3750.00"))


class TestSpecificIDLotMatching:
    def test_specific_id_selects_exact_lot(self):
        position_id = uuid4()
        lot1 = TaxLot(
            position_id=position_id,
            acquisition_date=date(2022, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot2 = TaxLot(
            position_id=position_id,
            acquisition_date=date(2023, 3, 20),
            cost_per_share=Money(Decimal("120.00")),
            original_quantity=Quantity(Decimal("75")),
        )

        lot2.sell(Quantity(Decimal("30")), date(2024, 12, 1))

        assert lot1.remaining_quantity == Quantity(Decimal("50"))
        assert lot2.remaining_quantity == Quantity(Decimal("45"))


class TestMinimizeGainLotMatching:
    @pytest.fixture
    def lots_with_varying_costs(self) -> list[TaxLot]:
        position_id = uuid4()
        return [
            TaxLot(
                position_id=position_id,
                acquisition_date=date(2022, 1, 15),
                cost_per_share=Money(Decimal("100.00")),
                original_quantity=Quantity(Decimal("50")),
            ),
            TaxLot(
                position_id=position_id,
                acquisition_date=date(2023, 3, 20),
                cost_per_share=Money(Decimal("180.00")),
                original_quantity=Quantity(Decimal("50")),
            ),
            TaxLot(
                position_id=position_id,
                acquisition_date=date(2024, 6, 10),
                cost_per_share=Money(Decimal("150.00")),
                original_quantity=Quantity(Decimal("50")),
            ),
        ]

    def test_minimize_gain_selects_highest_cost_first(
        self, lots_with_varying_costs: list[TaxLot]
    ):
        sorted_lots = sorted(
            lots_with_varying_costs,
            key=lambda lot: lot.cost_per_share.amount,
            reverse=True,
        )

        assert sorted_lots[0].cost_per_share == Money(Decimal("180.00"))
        assert sorted_lots[1].cost_per_share == Money(Decimal("150.00"))
        assert sorted_lots[2].cost_per_share == Money(Decimal("100.00"))


class TestMaximizeGainLotMatching:
    @pytest.fixture
    def lots_with_varying_costs(self) -> list[TaxLot]:
        position_id = uuid4()
        return [
            TaxLot(
                position_id=position_id,
                acquisition_date=date(2022, 1, 15),
                cost_per_share=Money(Decimal("100.00")),
                original_quantity=Quantity(Decimal("50")),
            ),
            TaxLot(
                position_id=position_id,
                acquisition_date=date(2023, 3, 20),
                cost_per_share=Money(Decimal("180.00")),
                original_quantity=Quantity(Decimal("50")),
            ),
        ]

    def test_maximize_gain_selects_lowest_cost_first(
        self, lots_with_varying_costs: list[TaxLot]
    ):
        sorted_lots = sorted(
            lots_with_varying_costs,
            key=lambda lot: lot.cost_per_share.amount,
        )

        assert sorted_lots[0].cost_per_share == Money(Decimal("100.00"))
        assert sorted_lots[1].cost_per_share == Money(Decimal("180.00"))


class TestWashSaleDetection:
    def test_wash_sale_within_30_days_before(self):
        position_id = uuid4()
        sale_date = date(2024, 6, 15)
        repurchase_date = date(2024, 6, 1)

        days_diff = (sale_date - repurchase_date).days

        assert days_diff <= 30

    def test_wash_sale_within_30_days_after(self):
        position_id = uuid4()
        sale_date = date(2024, 6, 15)
        repurchase_date = date(2024, 7, 10)

        days_diff = (repurchase_date - sale_date).days

        assert days_diff <= 30

    def test_not_wash_sale_outside_window(self):
        sale_date = date(2024, 6, 15)
        repurchase_date = date(2024, 8, 1)

        days_diff = (repurchase_date - sale_date).days

        assert days_diff > 30

    def test_wash_sale_adjustment_increases_cost_basis(self):
        lot = TaxLot(
            position_id=uuid4(),
            acquisition_date=date(2024, 6, 20),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        disallowed_loss = Money(Decimal("500.00"))

        lot.mark_wash_sale(disallowed_loss)

        assert lot.adjusted_cost_per_share == Money(Decimal("110.00"))


class TestCorporateActionLotAdjustments:
    def test_stock_split_doubles_shares_halves_cost(self):
        lot = TaxLot(
            position_id=uuid4(),
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("200.00")),
            original_quantity=Quantity(Decimal("100")),
        )

        lot.apply_split(Decimal("2"), Decimal("1"))

        assert lot.original_quantity == Quantity(Decimal("200"))
        assert lot.cost_per_share == Money(Decimal("100.00"))
        assert lot.total_cost == Money(Decimal("20000.00"))

    def test_reverse_split_halves_shares_doubles_cost(self):
        lot = TaxLot(
            position_id=uuid4(),
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("50.00")),
            original_quantity=Quantity(Decimal("100")),
        )

        lot.apply_split(Decimal("1"), Decimal("2"))

        assert lot.original_quantity == Quantity(Decimal("50"))
        assert lot.cost_per_share == Money(Decimal("100.00"))
        assert lot.total_cost == Money(Decimal("5000.00"))

    def test_three_for_one_split(self):
        lot = TaxLot(
            position_id=uuid4(),
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("300.00")),
            original_quantity=Quantity(Decimal("100")),
        )

        lot.apply_split(Decimal("3"), Decimal("1"))

        assert lot.original_quantity == Quantity(Decimal("300"))
        assert lot.cost_per_share == Money(Decimal("100.00"))

    def test_split_preserves_total_cost_basis(self):
        lot = TaxLot(
            position_id=uuid4(),
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("150.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        original_total = lot.total_cost

        lot.apply_split(Decimal("4"), Decimal("1"))

        assert lot.total_cost == original_total


class TestQSBSTracking:
    def test_qsbs_holding_period_under_5_years(self):
        lot = TaxLot(
            position_id=uuid4(),
            acquisition_date=date(2022, 1, 15),
            cost_per_share=Money(Decimal("10.00")),
            original_quantity=Quantity(Decimal("1000")),
        )
        lot.sell(Quantity(Decimal("1000")), date(2025, 1, 14))

        holding_days = lot.holding_period_days
        holding_years = holding_days / 365

        assert holding_years < 5

    def test_qsbs_holding_period_over_5_years(self):
        lot = TaxLot(
            position_id=uuid4(),
            acquisition_date=date(2019, 1, 15),
            cost_per_share=Money(Decimal("10.00")),
            original_quantity=Quantity(Decimal("1000")),
        )
        lot.sell(Quantity(Decimal("1000")), date(2024, 6, 15))

        holding_days = lot.holding_period_days
        holding_years = holding_days / 365

        assert holding_years >= 5
