from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.transactions import (
    Entry,
    InsufficientQuantityError,
    InvalidLotOperationError,
    TaxLot,
    Transaction,
    UnbalancedTransactionError,
)
from family_office_ledger.domain.value_objects import (
    AcquisitionType,
    Money,
    Quantity,
)


class TestEntry:
    def test_entry_creation_with_debit(self):
        account_id = uuid4()
        entry = Entry(
            account_id=account_id,
            debit_amount=Money(Decimal("1000.00")),
        )

        assert entry.account_id == account_id
        assert entry.debit_amount == Money(Decimal("1000.00"))
        assert entry.credit_amount.is_zero
        assert entry.is_debit is True
        assert entry.is_credit is False

    def test_entry_creation_with_credit(self):
        account_id = uuid4()
        entry = Entry(
            account_id=account_id,
            credit_amount=Money(Decimal("1000.00")),
        )

        assert entry.credit_amount == Money(Decimal("1000.00"))
        assert entry.debit_amount.is_zero
        assert entry.is_credit is True
        assert entry.is_debit is False

    def test_entry_net_amount_for_debit(self):
        entry = Entry(
            account_id=uuid4(),
            debit_amount=Money(Decimal("500.00")),
        )

        assert entry.net_amount == Money(Decimal("500.00"))

    def test_entry_net_amount_for_credit(self):
        entry = Entry(
            account_id=uuid4(),
            credit_amount=Money(Decimal("500.00")),
        )

        assert entry.net_amount == Money(Decimal("-500.00"))


class TestTransaction:
    def test_transaction_creation_with_date(self):
        txn = Transaction(transaction_date=date(2024, 6, 15))

        assert txn.transaction_date == date(2024, 6, 15)
        assert txn.posted_date == date(2024, 6, 15)
        assert txn.is_reversed is False
        assert txn.entries == []

    def test_transaction_with_balanced_entries(self):
        cash_account = uuid4()
        revenue_account = uuid4()

        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            memo="Client payment received",
            entries=[
                Entry(account_id=cash_account, debit_amount=Money(Decimal("5000.00"))),
                Entry(
                    account_id=revenue_account, credit_amount=Money(Decimal("5000.00"))
                ),
            ],
        )

        assert txn.is_balanced is True
        assert txn.total_debits == Money(Decimal("5000.00"))
        assert txn.total_credits == Money(Decimal("5000.00"))

    def test_transaction_with_unbalanced_entries_detected(self):
        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(account_id=uuid4(), debit_amount=Money(Decimal("5000.00"))),
                Entry(account_id=uuid4(), credit_amount=Money(Decimal("4000.00"))),
            ],
        )

        assert txn.is_balanced is False

    def test_transaction_validate_raises_on_unbalanced(self):
        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(account_id=uuid4(), debit_amount=Money(Decimal("5000.00"))),
                Entry(account_id=uuid4(), credit_amount=Money(Decimal("4000.00"))),
            ],
        )

        with pytest.raises(UnbalancedTransactionError):
            txn.validate()

    def test_transaction_validate_passes_when_balanced(self):
        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(account_id=uuid4(), debit_amount=Money(Decimal("5000.00"))),
                Entry(account_id=uuid4(), credit_amount=Money(Decimal("5000.00"))),
            ],
        )

        txn.validate()

    def test_transaction_add_entry(self):
        txn = Transaction(transaction_date=date(2024, 6, 15))
        entry = Entry(account_id=uuid4(), debit_amount=Money(Decimal("100.00")))

        txn.add_entry(entry)

        assert len(txn.entries) == 1
        assert txn.entries[0] == entry

    def test_transaction_account_ids_returns_unique_accounts(self):
        account1 = uuid4()
        account2 = uuid4()

        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(account_id=account1, debit_amount=Money(Decimal("1000.00"))),
                Entry(account_id=account2, credit_amount=Money(Decimal("1000.00"))),
            ],
        )

        assert txn.account_ids == {account1, account2}

    def test_transaction_reversal_tracking(self):
        original_txn_id = uuid4()

        reversal = Transaction(
            transaction_date=date(2024, 6, 20),
            memo="Reversal of original transaction",
            reverses_transaction_id=original_txn_id,
        )

        assert reversal.is_reversal is True
        assert reversal.reverses_transaction_id == original_txn_id

    def test_transaction_multi_entry_balanced(self):
        checking = uuid4()
        savings = uuid4()
        expense = uuid4()

        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            memo="Split transaction",
            entries=[
                Entry(account_id=expense, debit_amount=Money(Decimal("300.00"))),
                Entry(account_id=expense, debit_amount=Money(Decimal("200.00"))),
                Entry(account_id=checking, credit_amount=Money(Decimal("400.00"))),
                Entry(account_id=savings, credit_amount=Money(Decimal("100.00"))),
            ],
        )

        assert txn.is_balanced is True
        assert txn.total_debits == Money(Decimal("500.00"))
        assert txn.total_credits == Money(Decimal("500.00"))


class TestTaxLot:
    def test_tax_lot_creation_sets_remaining_to_original(self):
        position_id = uuid4()
        lot = TaxLot(
            position_id=position_id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("150.00")),
            original_quantity=Quantity(Decimal("100")),
        )

        assert lot.position_id == position_id
        assert lot.original_quantity == Quantity(Decimal("100"))
        assert lot.remaining_quantity == Quantity(Decimal("100"))
        assert lot.cost_per_share == Money(Decimal("150.00"))

    def test_tax_lot_total_cost_calculation(self, sample_tax_lot: TaxLot):
        assert sample_tax_lot.total_cost == Money(Decimal("15000.00"))

    def test_tax_lot_remaining_cost_calculation(self, sample_tax_lot: TaxLot):
        assert sample_tax_lot.remaining_cost == Money(Decimal("15000.00"))

    def test_tax_lot_sell_reduces_remaining_quantity(self, sample_tax_lot: TaxLot):
        cost_basis = sample_tax_lot.sell(
            quantity=Quantity(Decimal("25")),
            disposition_date=date(2024, 8, 1),
        )

        assert sample_tax_lot.remaining_quantity == Quantity(Decimal("75"))
        assert cost_basis == Money(Decimal("3750.00"))

    def test_tax_lot_sell_full_quantity_sets_disposition_date(
        self, sample_tax_lot: TaxLot
    ):
        sample_tax_lot.sell(
            quantity=Quantity(Decimal("100")),
            disposition_date=date(2024, 8, 1),
        )

        assert sample_tax_lot.is_fully_disposed is True
        assert sample_tax_lot.disposition_date == date(2024, 8, 1)

    def test_tax_lot_sell_raises_on_insufficient_quantity(self, sample_tax_lot: TaxLot):
        with pytest.raises(InsufficientQuantityError):
            sample_tax_lot.sell(
                quantity=Quantity(Decimal("150")),
                disposition_date=date(2024, 8, 1),
            )

    def test_tax_lot_sell_raises_on_invalid_disposition_date(
        self, sample_tax_lot: TaxLot
    ):
        with pytest.raises(InvalidLotOperationError):
            sample_tax_lot.sell(
                quantity=Quantity(Decimal("50")),
                disposition_date=date(2023, 1, 1),
            )

    def test_tax_lot_apply_split_adjusts_quantities_and_cost(
        self, sample_tax_lot: TaxLot
    ):
        sample_tax_lot.apply_split(
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
        )

        assert sample_tax_lot.original_quantity == Quantity(Decimal("200"))
        assert sample_tax_lot.remaining_quantity == Quantity(Decimal("200"))
        assert sample_tax_lot.cost_per_share == Money(Decimal("75.00"))

    def test_tax_lot_reverse_split(self, sample_tax_lot: TaxLot):
        sample_tax_lot.apply_split(
            ratio_numerator=Decimal("1"),
            ratio_denominator=Decimal("2"),
        )

        assert sample_tax_lot.original_quantity == Quantity(Decimal("50"))
        assert sample_tax_lot.remaining_quantity == Quantity(Decimal("50"))
        assert sample_tax_lot.cost_per_share == Money(Decimal("300.00"))

    def test_tax_lot_holding_period_short_term(self):
        lot = TaxLot(
            position_id=uuid4(),
            acquisition_date=date(2024, 6, 1),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot.sell(Quantity(Decimal("50")), date(2024, 12, 1))

        assert lot.is_short_term is True
        assert lot.is_long_term is False

    def test_tax_lot_holding_period_long_term(self):
        lot = TaxLot(
            position_id=uuid4(),
            acquisition_date=date(2023, 1, 1),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot.sell(Quantity(Decimal("50")), date(2024, 6, 1))

        assert lot.is_long_term is True
        assert lot.is_short_term is False

    def test_tax_lot_wash_sale_marking(self, sample_tax_lot: TaxLot):
        disallowed = Money(Decimal("500.00"))

        sample_tax_lot.mark_wash_sale(disallowed)

        assert sample_tax_lot.wash_sale_disallowed is True
        assert sample_tax_lot.wash_sale_adjustment == disallowed

    def test_tax_lot_adjusted_cost_with_wash_sale(self, sample_tax_lot: TaxLot):
        sample_tax_lot.mark_wash_sale(Money(Decimal("1000.00")))

        adjusted = sample_tax_lot.adjusted_cost_per_share

        assert adjusted == Money(Decimal("160.00"))

    def test_tax_lot_is_open_when_remaining_quantity(self, sample_tax_lot: TaxLot):
        assert sample_tax_lot.is_open is True
        assert sample_tax_lot.is_fully_disposed is False

    def test_tax_lot_partial_disposal_status(self, sample_tax_lot: TaxLot):
        sample_tax_lot.sell(Quantity(Decimal("50")), date(2024, 8, 1))

        assert sample_tax_lot.is_partially_disposed is True
        assert sample_tax_lot.is_fully_disposed is False
        assert sample_tax_lot.is_open is True

    def test_tax_lot_acquisition_types(self):
        assert AcquisitionType.PURCHASE.value == "purchase"
        assert AcquisitionType.GIFT.value == "gift"
        assert AcquisitionType.INHERITANCE.value == "inheritance"
        assert AcquisitionType.TRANSFER.value == "transfer"
        assert AcquisitionType.EXERCISE.value == "exercise"
        assert AcquisitionType.SPINOFF.value == "spinoff"
        assert AcquisitionType.MERGER.value == "merger"
