from uuid import uuid4

import pytest

from family_office_ledger.domain.vendors import Vendor
from family_office_ledger.repositories.sqlite import (
    SQLiteDatabase,
    SQLiteVendorRepository,
)


@pytest.fixture
def db() -> SQLiteDatabase:
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database


@pytest.fixture
def vendor_repo(db: SQLiteDatabase) -> SQLiteVendorRepository:
    return SQLiteVendorRepository(db)


class TestSQLiteVendorRepository:
    def test_add_and_get_vendor(self, vendor_repo: SQLiteVendorRepository):
        vendor = Vendor(
            name="Acme Corp",
            category="Supplies",
            tax_id="12-3456789",
            is_1099_eligible=True,
            contact_email="billing@acme.com",
            contact_phone="555-1234",
            notes="Preferred supplier",
        )

        vendor_repo.add(vendor)
        retrieved = vendor_repo.get(vendor.id)

        assert retrieved is not None
        assert retrieved.id == vendor.id
        assert retrieved.name == "Acme Corp"
        assert retrieved.category == "Supplies"
        assert retrieved.tax_id == "12-3456789"
        assert retrieved.is_1099_eligible is True
        assert retrieved.contact_email == "billing@acme.com"
        assert retrieved.contact_phone == "555-1234"
        assert retrieved.notes == "Preferred supplier"
        assert retrieved.is_active is True

    def test_get_nonexistent_vendor_returns_none(
        self, vendor_repo: SQLiteVendorRepository
    ):
        result = vendor_repo.get(uuid4())
        assert result is None

    def test_update_vendor(self, vendor_repo: SQLiteVendorRepository):
        vendor = Vendor(name="Old Name", category="Services")
        vendor_repo.add(vendor)

        vendor.name = "New Name"
        vendor.category = "Consulting"
        vendor.is_1099_eligible = True
        vendor.contact_email = "new@email.com"
        vendor_repo.update(vendor)

        retrieved = vendor_repo.get(vendor.id)
        assert retrieved is not None
        assert retrieved.name == "New Name"
        assert retrieved.category == "Consulting"
        assert retrieved.is_1099_eligible is True
        assert retrieved.contact_email == "new@email.com"

    def test_delete_vendor(self, vendor_repo: SQLiteVendorRepository):
        vendor = Vendor(name="To Delete")
        vendor_repo.add(vendor)

        vendor_repo.delete(vendor.id)

        assert vendor_repo.get(vendor.id) is None

    def test_list_all_active_only(self, vendor_repo: SQLiteVendorRepository):
        active_vendor = Vendor(name="Active Vendor")
        inactive_vendor = Vendor(name="Inactive Vendor", is_active=False)
        vendor_repo.add(active_vendor)
        vendor_repo.add(inactive_vendor)

        vendors = list(vendor_repo.list_all(include_inactive=False))

        assert len(vendors) == 1
        assert vendors[0].name == "Active Vendor"

    def test_list_all_include_inactive(self, vendor_repo: SQLiteVendorRepository):
        active_vendor = Vendor(name="Active Vendor")
        inactive_vendor = Vendor(name="Inactive Vendor", is_active=False)
        vendor_repo.add(active_vendor)
        vendor_repo.add(inactive_vendor)

        vendors = list(vendor_repo.list_all(include_inactive=True))

        assert len(vendors) == 2
        names = {v.name for v in vendors}
        assert names == {"Active Vendor", "Inactive Vendor"}

    def test_list_by_category(self, vendor_repo: SQLiteVendorRepository):
        vendor1 = Vendor(name="Supplier A", category="Supplies")
        vendor2 = Vendor(name="Supplier B", category="Supplies")
        vendor3 = Vendor(name="Consultant", category="Services")
        vendor_repo.add(vendor1)
        vendor_repo.add(vendor2)
        vendor_repo.add(vendor3)

        supplies = list(vendor_repo.list_by_category("Supplies"))

        assert len(supplies) == 2
        names = {v.name for v in supplies}
        assert names == {"Supplier A", "Supplier B"}

    def test_list_by_category_excludes_inactive(
        self, vendor_repo: SQLiteVendorRepository
    ):
        active = Vendor(name="Active Supplier", category="Supplies")
        inactive = Vendor(
            name="Inactive Supplier", category="Supplies", is_active=False
        )
        vendor_repo.add(active)
        vendor_repo.add(inactive)

        vendors = list(vendor_repo.list_by_category("Supplies"))

        assert len(vendors) == 1
        assert vendors[0].name == "Active Supplier"

    def test_search_by_name(self, vendor_repo: SQLiteVendorRepository):
        vendor1 = Vendor(name="Acme Corporation")
        vendor2 = Vendor(name="Acme Industries")
        vendor3 = Vendor(name="Beta Corp")
        vendor_repo.add(vendor1)
        vendor_repo.add(vendor2)
        vendor_repo.add(vendor3)

        results = list(vendor_repo.search_by_name("Acme"))

        assert len(results) == 2
        names = {v.name for v in results}
        assert names == {"Acme Corporation", "Acme Industries"}

    def test_search_by_name_partial_match(self, vendor_repo: SQLiteVendorRepository):
        vendor = Vendor(name="Acme Corporation Ltd")
        vendor_repo.add(vendor)

        results = list(vendor_repo.search_by_name("Corp"))

        assert len(results) == 1
        assert results[0].name == "Acme Corporation Ltd"

    def test_search_by_name_excludes_inactive(
        self, vendor_repo: SQLiteVendorRepository
    ):
        active = Vendor(name="Acme Active")
        inactive = Vendor(name="Acme Inactive", is_active=False)
        vendor_repo.add(active)
        vendor_repo.add(inactive)

        results = list(vendor_repo.search_by_name("Acme"))

        assert len(results) == 1
        assert results[0].name == "Acme Active"

    def test_get_by_tax_id(self, vendor_repo: SQLiteVendorRepository):
        vendor = Vendor(name="Tax Vendor", tax_id="98-7654321")
        vendor_repo.add(vendor)

        retrieved = vendor_repo.get_by_tax_id("98-7654321")

        assert retrieved is not None
        assert retrieved.name == "Tax Vendor"
        assert retrieved.tax_id == "98-7654321"

    def test_get_by_tax_id_not_found(self, vendor_repo: SQLiteVendorRepository):
        result = vendor_repo.get_by_tax_id("00-0000000")
        assert result is None

    def test_vendor_with_default_account(self, vendor_repo: SQLiteVendorRepository):
        account_id = uuid4()
        vendor = Vendor(
            name="Default Account Vendor",
            default_account_id=account_id,
            default_category="Office Expenses",
        )
        vendor_repo.add(vendor)

        retrieved = vendor_repo.get(vendor.id)

        assert retrieved is not None
        assert retrieved.default_account_id == account_id
        assert retrieved.default_category == "Office Expenses"

    def test_vendor_preserves_timestamps(self, vendor_repo: SQLiteVendorRepository):
        vendor = Vendor(name="Timestamp Test")
        original_created = vendor.created_at
        original_updated = vendor.updated_at

        vendor_repo.add(vendor)
        retrieved = vendor_repo.get(vendor.id)

        assert retrieved is not None
        assert retrieved.created_at == original_created
        assert retrieved.updated_at == original_updated

    def test_deactivate_vendor(self, vendor_repo: SQLiteVendorRepository):
        vendor = Vendor(name="To Deactivate")
        vendor_repo.add(vendor)

        vendor.deactivate()
        vendor_repo.update(vendor)

        retrieved = vendor_repo.get(vendor.id)
        assert retrieved is not None
        assert retrieved.is_active is False


class TestVendorSchemaMigration:
    def test_vendors_table_exists(self, db: SQLiteDatabase):
        conn = db.get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in tables}

        assert "vendors" in table_names

    def test_vendors_indexes_exist(self, db: SQLiteDatabase):
        conn = db.get_connection()
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        index_names = {row["name"] for row in indexes}

        assert "idx_vendors_name" in index_names
        assert "idx_vendors_category" in index_names
        assert "idx_vendors_tax_id" in index_names

    def test_transaction_expense_columns_exist(self, db: SQLiteDatabase):
        conn = db.get_connection()
        columns = conn.execute("PRAGMA table_info(transactions)").fetchall()
        column_names = {col["name"] for col in columns}

        assert "category" in column_names
        assert "tags" in column_names
        assert "vendor_id" in column_names
        assert "is_recurring" in column_names
        assert "recurring_frequency" in column_names

    def test_entry_category_column_exists(self, db: SQLiteDatabase):
        conn = db.get_connection()
        columns = conn.execute("PRAGMA table_info(entries)").fetchall()
        column_names = {col["name"] for col in columns}

        assert "category" in column_names
