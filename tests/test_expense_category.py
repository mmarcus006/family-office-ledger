"""Tests for ExpenseCategory enum."""

import pytest

from family_office_ledger.domain.value_objects import ExpenseCategory


class TestExpenseCategoryEnum:
    """Test ExpenseCategory enum."""

    def test_all_enum_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        expected_values = {
            "PAYROLL",
            "RENT",
            "UTILITIES",
            "INSURANCE",
            "LEGAL",
            "ACCOUNTING",
            "CONSULTING",
            "TRAVEL",
            "MEALS",
            "ENTERTAINMENT",
            "SOFTWARE",
            "HARDWARE",
            "HOSTING",
            "BANK_FEES",
            "INTEREST_EXPENSE",
            "OFFICE_SUPPLIES",
            "MARKETING",
            "CHARITABLE",
            "OTHER",
        }
        actual_values = {member.name for member in ExpenseCategory}
        assert actual_values == expected_values

    def test_enum_is_str_based(self) -> None:
        """Test that ExpenseCategory inherits from str."""
        assert issubclass(ExpenseCategory, str)

    def test_enum_values_are_lowercase(self) -> None:
        """Test that all enum values are lowercase strings."""
        for member in ExpenseCategory:
            assert member.value == member.value.lower()
            assert isinstance(member.value, str)

    def test_can_iterate_over_categories(self) -> None:
        """Test that we can iterate over all categories."""
        categories = list(ExpenseCategory)
        assert len(categories) == 19
        assert all(isinstance(cat, ExpenseCategory) for cat in categories)

    def test_specific_enum_values(self) -> None:
        """Test specific enum value mappings."""
        assert ExpenseCategory.PAYROLL.value == "payroll"
        assert ExpenseCategory.RENT.value == "rent"
        assert ExpenseCategory.UTILITIES.value == "utilities"
        assert ExpenseCategory.INSURANCE.value == "insurance"
        assert ExpenseCategory.LEGAL.value == "legal"
        assert ExpenseCategory.ACCOUNTING.value == "accounting"
        assert ExpenseCategory.CONSULTING.value == "consulting"
        assert ExpenseCategory.TRAVEL.value == "travel"
        assert ExpenseCategory.MEALS.value == "meals"
        assert ExpenseCategory.ENTERTAINMENT.value == "entertainment"
        assert ExpenseCategory.SOFTWARE.value == "software"
        assert ExpenseCategory.HARDWARE.value == "hardware"
        assert ExpenseCategory.HOSTING.value == "hosting"
        assert ExpenseCategory.BANK_FEES.value == "bank_fees"
        assert ExpenseCategory.INTEREST_EXPENSE.value == "interest_expense"
        assert ExpenseCategory.OFFICE_SUPPLIES.value == "office_supplies"
        assert ExpenseCategory.MARKETING.value == "marketing"
        assert ExpenseCategory.CHARITABLE.value == "charitable"
        assert ExpenseCategory.OTHER.value == "other"

    def test_enum_string_comparison(self) -> None:
        """Test that enum members can be compared as strings."""
        assert ExpenseCategory.PAYROLL == "payroll"
        assert ExpenseCategory.RENT == "rent"

    def test_enum_json_serializable(self) -> None:
        """Test that enum values are JSON serializable."""
        import json

        # str-based enums should serialize to their string value
        category = ExpenseCategory.PAYROLL
        json_str = json.dumps(category.value)
        assert json_str == '"payroll"'
