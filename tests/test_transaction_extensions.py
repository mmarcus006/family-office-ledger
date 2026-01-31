"""Tests for Transaction and Entry model extensions (category, tags, vendor, recurring)."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.value_objects import Money


class TestTransactionExtensions:
    """Tests for new Transaction fields: category, tags, vendor_id, is_recurring, recurring_frequency."""

    def test_transaction_with_category(self):
        """Transaction can have an optional category field."""
        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            category="utilities",
        )

        assert txn.category == "utilities"

    def test_transaction_category_default_is_none(self):
        """Transaction category defaults to None for backward compatibility."""
        txn = Transaction(transaction_date=date(2024, 6, 15))

        assert txn.category is None

    def test_transaction_with_tags(self):
        """Transaction can have a list of tags."""
        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            tags=["tax-deductible", "business", "q2-2024"],
        )

        assert txn.tags == ["tax-deductible", "business", "q2-2024"]
        assert len(txn.tags) == 3

    def test_transaction_tags_default_is_empty_list(self):
        """Transaction tags defaults to empty list for backward compatibility."""
        txn = Transaction(transaction_date=date(2024, 6, 15))

        assert txn.tags == []
        assert isinstance(txn.tags, list)

    def test_transaction_with_vendor_id(self):
        """Transaction can have an optional vendor_id."""
        vendor_id = uuid4()
        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            vendor_id=vendor_id,
        )

        assert txn.vendor_id == vendor_id

    def test_transaction_vendor_id_default_is_none(self):
        """Transaction vendor_id defaults to None for backward compatibility."""
        txn = Transaction(transaction_date=date(2024, 6, 15))

        assert txn.vendor_id is None

    def test_transaction_with_is_recurring(self):
        """Transaction can be marked as recurring."""
        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            is_recurring=True,
        )

        assert txn.is_recurring is True

    def test_transaction_is_recurring_default_is_false(self):
        """Transaction is_recurring defaults to False for backward compatibility."""
        txn = Transaction(transaction_date=date(2024, 6, 15))

        assert txn.is_recurring is False

    def test_transaction_with_recurring_frequency(self):
        """Transaction can have a recurring frequency."""
        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            is_recurring=True,
            recurring_frequency="monthly",
        )

        assert txn.recurring_frequency == "monthly"

    def test_transaction_recurring_frequency_values(self):
        """Transaction supports various recurring frequency values."""
        frequencies = ["monthly", "quarterly", "annual"]

        for freq in frequencies:
            txn = Transaction(
                transaction_date=date(2024, 6, 15),
                is_recurring=True,
                recurring_frequency=freq,
            )
            assert txn.recurring_frequency == freq

    def test_transaction_recurring_frequency_default_is_none(self):
        """Transaction recurring_frequency defaults to None for backward compatibility."""
        txn = Transaction(transaction_date=date(2024, 6, 15))

        assert txn.recurring_frequency is None

    def test_transaction_with_all_new_fields(self):
        """Transaction can be created with all new fields together."""
        vendor_id = uuid4()
        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            memo="Monthly rent payment",
            category="housing",
            tags=["recurring", "tax-deductible", "rent"],
            vendor_id=vendor_id,
            is_recurring=True,
            recurring_frequency="monthly",
        )

        assert txn.transaction_date == date(2024, 6, 15)
        assert txn.memo == "Monthly rent payment"
        assert txn.category == "housing"
        assert txn.tags == ["recurring", "tax-deductible", "rent"]
        assert txn.vendor_id == vendor_id
        assert txn.is_recurring is True
        assert txn.recurring_frequency == "monthly"

    def test_transaction_backward_compatibility_with_entries(self):
        """Transaction with new fields still works with entries and validation."""
        cash_account = uuid4()
        expense_account = uuid4()
        vendor_id = uuid4()

        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            memo="Office supplies",
            category="office",
            tags=["supplies", "deductible"],
            vendor_id=vendor_id,
            entries=[
                Entry(
                    account_id=expense_account, debit_amount=Money(Decimal("150.00"))
                ),
                Entry(account_id=cash_account, credit_amount=Money(Decimal("150.00"))),
            ],
        )

        assert txn.is_balanced is True
        txn.validate()  # Should not raise
        assert txn.total_debits == Money(Decimal("150.00"))
        assert txn.total_credits == Money(Decimal("150.00"))


class TestEntryExtensions:
    """Tests for new Entry field: category override."""

    def test_entry_with_category_override(self):
        """Entry can have an optional category to override transaction category."""
        entry = Entry(
            account_id=uuid4(),
            debit_amount=Money(Decimal("100.00")),
            category="utilities",
        )

        assert entry.category == "utilities"

    def test_entry_category_default_is_none(self):
        """Entry category defaults to None for backward compatibility."""
        entry = Entry(
            account_id=uuid4(),
            debit_amount=Money(Decimal("100.00")),
        )

        assert entry.category is None

    def test_entry_category_override_different_from_transaction(self):
        """Entry can have different category than its parent transaction."""
        expense_account = uuid4()
        cash_account = uuid4()

        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            category="general",
            entries=[
                Entry(
                    account_id=expense_account,
                    debit_amount=Money(Decimal("100.00")),
                    category="utilities",  # Override transaction category
                ),
                Entry(
                    account_id=cash_account,
                    credit_amount=Money(Decimal("100.00")),
                    # No category override, inherits from transaction
                ),
            ],
        )

        assert txn.category == "general"
        assert txn.entries[0].category == "utilities"
        assert txn.entries[1].category is None

    def test_entry_backward_compatibility_all_properties(self):
        """Entry with category still has all existing properties working."""
        account_id = uuid4()
        entry = Entry(
            account_id=account_id,
            debit_amount=Money(Decimal("500.00")),
            memo="Test entry",
            category="test-category",
        )

        assert entry.account_id == account_id
        assert entry.debit_amount == Money(Decimal("500.00"))
        assert entry.credit_amount.is_zero
        assert entry.memo == "Test entry"
        assert entry.is_debit is True
        assert entry.is_credit is False
        assert entry.net_amount == Money(Decimal("500.00"))
        assert entry.category == "test-category"


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility - all new fields are optional with sensible defaults."""

    def test_transaction_minimal_creation_unchanged(self):
        """Minimal transaction creation still works without new fields."""
        txn = Transaction(transaction_date=date(2024, 6, 15))

        # Original fields work as before
        assert txn.transaction_date == date(2024, 6, 15)
        assert txn.posted_date == date(2024, 6, 15)
        assert txn.entries == []
        assert txn.memo == ""
        assert txn.reference == ""
        assert txn.is_reversed is False
        assert txn.reverses_transaction_id is None
        assert txn.created_by is None

        # New fields have safe defaults
        assert txn.category is None
        assert txn.tags == []
        assert txn.vendor_id is None
        assert txn.is_recurring is False
        assert txn.recurring_frequency is None

    def test_entry_minimal_creation_unchanged(self):
        """Minimal entry creation still works without new fields."""
        account_id = uuid4()
        entry = Entry(account_id=account_id)

        # Original fields work as before
        assert entry.account_id == account_id
        assert entry.debit_amount.is_zero
        assert entry.credit_amount.is_zero
        assert entry.memo == ""
        assert entry.tax_lot_id is None

        # New field has safe default
        assert entry.category is None

    def test_tags_list_independence(self):
        """Each transaction should have its own tags list (no shared mutable default)."""
        txn1 = Transaction(transaction_date=date(2024, 6, 15))
        txn2 = Transaction(transaction_date=date(2024, 6, 16))

        txn1.tags.append("modified")

        assert txn1.tags == ["modified"]
        assert txn2.tags == []  # Should NOT be affected
