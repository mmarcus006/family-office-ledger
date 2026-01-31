"""Tests for Vendor domain model."""

from datetime import UTC, datetime
from uuid import UUID

from family_office_ledger.domain.vendors import Vendor


class TestVendorCreation:
    """Test Vendor creation with required and optional fields."""

    def test_vendor_creation_with_required_fields_only(self) -> None:
        """Test creating a vendor with only required fields."""
        vendor = Vendor(name="Acme Corp")

        assert vendor.name == "Acme Corp"
        assert isinstance(vendor.id, UUID)
        assert vendor.category is None
        assert vendor.tax_id is None
        assert vendor.is_1099_eligible is False
        assert vendor.default_account_id is None
        assert vendor.default_category is None
        assert vendor.contact_email is None
        assert vendor.contact_phone is None
        assert vendor.notes == ""
        assert vendor.is_active is True
        assert isinstance(vendor.created_at, datetime)
        assert isinstance(vendor.updated_at, datetime)

    def test_vendor_creation_with_all_fields(self) -> None:
        """Test creating a vendor with all optional fields."""
        vendor_id = UUID("12345678-1234-5678-1234-567812345678")
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        vendor = Vendor(
            name="Acme Corp",
            id=vendor_id,
            category="Office Supplies",
            tax_id="12-3456789",
            is_1099_eligible=True,
            default_account_id=UUID("87654321-4321-8765-4321-876543218765"),
            default_category="Supplies",
            contact_email="contact@acme.com",
            contact_phone="555-1234",
            notes="Primary vendor",
            is_active=True,
            created_at=created_at,
            updated_at=updated_at,
        )

        assert vendor.name == "Acme Corp"
        assert vendor.id == vendor_id
        assert vendor.category == "Office Supplies"
        assert vendor.tax_id == "12-3456789"
        assert vendor.is_1099_eligible is True
        assert vendor.default_account_id == UUID("87654321-4321-8765-4321-876543218765")
        assert vendor.default_category == "Supplies"
        assert vendor.contact_email == "contact@acme.com"
        assert vendor.contact_phone == "555-1234"
        assert vendor.notes == "Primary vendor"
        assert vendor.is_active is True
        assert vendor.created_at == created_at
        assert vendor.updated_at == updated_at

    def test_vendor_default_values(self) -> None:
        """Test that vendor has correct default values."""
        vendor = Vendor(name="Test Vendor")

        assert vendor.is_active is True
        assert vendor.is_1099_eligible is False
        assert vendor.notes == ""
        assert vendor.category is None
        assert vendor.tax_id is None


class TestVendorDeactivation:
    """Test vendor activation/deactivation."""

    def test_vendor_deactivation(self) -> None:
        """Test deactivating a vendor."""
        vendor = Vendor(name="Active Vendor")
        assert vendor.is_active is True

        original_updated_at = vendor.updated_at
        vendor.deactivate()

        assert vendor.is_active is False
        assert vendor.updated_at > original_updated_at

    def test_vendor_activation(self) -> None:
        """Test activating a vendor."""
        vendor = Vendor(name="Inactive Vendor", is_active=False)
        assert vendor.is_active is False

        original_updated_at = vendor.updated_at
        vendor.activate()

        assert vendor.is_active is True
        assert vendor.updated_at > original_updated_at

    def test_vendor_deactivate_then_activate(self) -> None:
        """Test deactivating and then reactivating a vendor."""
        vendor = Vendor(name="Toggle Vendor")

        vendor.deactivate()
        assert vendor.is_active is False

        vendor.activate()
        assert vendor.is_active is True


class TestVendor1099Eligibility:
    """Test 1099 eligibility flag."""

    def test_vendor_1099_eligible_flag(self) -> None:
        """Test setting 1099 eligibility flag."""
        vendor = Vendor(name="1099 Vendor", is_1099_eligible=True)
        assert vendor.is_1099_eligible is True

    def test_vendor_1099_with_tax_id(self) -> None:
        """Test vendor with tax ID for 1099 reporting."""
        vendor = Vendor(
            name="Contractor",
            tax_id="12-3456789",
            is_1099_eligible=True,
        )

        assert vendor.tax_id == "12-3456789"
        assert vendor.is_1099_eligible is True

    def test_vendor_1099_default_false(self) -> None:
        """Test that 1099 eligibility defaults to False."""
        vendor = Vendor(name="Regular Vendor")
        assert vendor.is_1099_eligible is False
