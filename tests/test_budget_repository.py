from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.budgets import (
    Budget,
    BudgetLineItem,
    BudgetPeriodType,
)
from family_office_ledger.domain.entities import Entity
from family_office_ledger.domain.value_objects import EntityType, Money
from family_office_ledger.repositories.sqlite import (
    SQLiteBudgetRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
)


@pytest.fixture
def db() -> SQLiteDatabase:
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database


@pytest.fixture
def entity_repo(db: SQLiteDatabase) -> SQLiteEntityRepository:
    return SQLiteEntityRepository(db)


@pytest.fixture
def budget_repo(db: SQLiteDatabase) -> SQLiteBudgetRepository:
    return SQLiteBudgetRepository(db)


@pytest.fixture
def sample_entity(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(
        name="Test Family Trust",
        entity_type=EntityType.TRUST,
        fiscal_year_end=date(2025, 12, 31),
    )
    entity_repo.add(entity)
    return entity


class TestSQLiteBudgetRepository:
    def test_add_and_get_budget(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="2025 Annual Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        budget_repo.add(budget)
        retrieved = budget_repo.get(budget.id)

        assert retrieved is not None
        assert retrieved.id == budget.id
        assert retrieved.name == "2025 Annual Budget"
        assert retrieved.entity_id == sample_entity.id
        assert retrieved.period_type == BudgetPeriodType.ANNUAL
        assert retrieved.start_date == date(2025, 1, 1)
        assert retrieved.end_date == date(2025, 12, 31)
        assert retrieved.is_active is True

    def test_get_nonexistent_budget_returns_none(
        self, budget_repo: SQLiteBudgetRepository
    ):
        result = budget_repo.get(uuid4())
        assert result is None

    def test_update_budget(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="Original Name",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        budget_repo.add(budget)

        budget.name = "Updated Name"
        budget.period_type = BudgetPeriodType.QUARTERLY
        budget.end_date = date(2025, 3, 31)
        budget_repo.update(budget)

        retrieved = budget_repo.get(budget.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"
        assert retrieved.period_type == BudgetPeriodType.QUARTERLY
        assert retrieved.end_date == date(2025, 3, 31)

    def test_delete_budget(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="To Delete",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        budget_repo.add(budget)

        budget_repo.delete(budget.id)

        assert budget_repo.get(budget.id) is None

    def test_list_by_entity_active_only(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        active = Budget(
            name="Active Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        inactive = Budget(
            name="Inactive Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            is_active=False,
        )
        budget_repo.add(active)
        budget_repo.add(inactive)

        budgets = list(
            budget_repo.list_by_entity(sample_entity.id, include_inactive=False)
        )

        assert len(budgets) == 1
        assert budgets[0].name == "Active Budget"

    def test_list_by_entity_include_inactive(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        active = Budget(
            name="Active Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        inactive = Budget(
            name="Inactive Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            is_active=False,
        )
        budget_repo.add(active)
        budget_repo.add(inactive)

        budgets = list(
            budget_repo.list_by_entity(sample_entity.id, include_inactive=True)
        )

        assert len(budgets) == 2
        names = {b.name for b in budgets}
        assert names == {"Active Budget", "Inactive Budget"}

    def test_get_active_for_date(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="Q1 2025 Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.QUARTERLY,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
        )
        budget_repo.add(budget)

        retrieved = budget_repo.get_active_for_date(sample_entity.id, date(2025, 2, 15))

        assert retrieved is not None
        assert retrieved.name == "Q1 2025 Budget"

    def test_get_active_for_date_outside_range(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="Q1 2025 Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.QUARTERLY,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
        )
        budget_repo.add(budget)

        retrieved = budget_repo.get_active_for_date(sample_entity.id, date(2025, 5, 15))

        assert retrieved is None

    def test_get_active_for_date_excludes_inactive(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="Inactive Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_active=False,
        )
        budget_repo.add(budget)

        retrieved = budget_repo.get_active_for_date(sample_entity.id, date(2025, 6, 15))

        assert retrieved is None

    def test_budget_preserves_timestamps(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="Timestamp Test",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        original_created = budget.created_at
        original_updated = budget.updated_at

        budget_repo.add(budget)
        retrieved = budget_repo.get(budget.id)

        assert retrieved is not None
        assert retrieved.created_at == original_created
        assert retrieved.updated_at == original_updated

    def test_deactivate_budget(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="To Deactivate",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        budget_repo.add(budget)

        budget.deactivate()
        budget_repo.update(budget)

        retrieved = budget_repo.get(budget.id)
        assert retrieved is not None
        assert retrieved.is_active is False


class TestBudgetLineItems:
    def test_add_and_get_line_items(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="2025 Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        budget_repo.add(budget)

        line_item = BudgetLineItem(
            budget_id=budget.id,
            category="Marketing",
            budgeted_amount=Money(Decimal("50000.00"), "USD"),
            notes="Q1-Q4 marketing campaigns",
        )
        budget_repo.add_line_item(line_item)

        items = list(budget_repo.get_line_items(budget.id))

        assert len(items) == 1
        assert items[0].id == line_item.id
        assert items[0].category == "Marketing"
        assert items[0].budgeted_amount == Money(Decimal("50000.00"), "USD")
        assert items[0].notes == "Q1-Q4 marketing campaigns"

    def test_add_line_item_with_account(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="2025 Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        budget_repo.add(budget)

        account_id = uuid4()
        line_item = BudgetLineItem(
            budget_id=budget.id,
            category="Payroll",
            budgeted_amount=Money(Decimal("100000.00"), "USD"),
            account_id=account_id,
        )
        budget_repo.add_line_item(line_item)

        items = list(budget_repo.get_line_items(budget.id))

        assert len(items) == 1
        assert items[0].account_id == account_id

    def test_update_line_item(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="2025 Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        budget_repo.add(budget)

        line_item = BudgetLineItem(
            budget_id=budget.id,
            category="Marketing",
            budgeted_amount=Money(Decimal("50000.00"), "USD"),
        )
        budget_repo.add_line_item(line_item)

        line_item.category = "Advertising"
        line_item.budgeted_amount = Money(Decimal("75000.00"), "USD")
        line_item.notes = "Increased budget"
        budget_repo.update_line_item(line_item)

        items = list(budget_repo.get_line_items(budget.id))

        assert len(items) == 1
        assert items[0].category == "Advertising"
        assert items[0].budgeted_amount == Money(Decimal("75000.00"), "USD")
        assert items[0].notes == "Increased budget"

    def test_delete_line_item(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="2025 Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        budget_repo.add(budget)

        line_item1 = BudgetLineItem(
            budget_id=budget.id,
            category="Marketing",
            budgeted_amount=Money(Decimal("50000.00"), "USD"),
        )
        line_item2 = BudgetLineItem(
            budget_id=budget.id,
            category="Payroll",
            budgeted_amount=Money(Decimal("100000.00"), "USD"),
        )
        budget_repo.add_line_item(line_item1)
        budget_repo.add_line_item(line_item2)

        budget_repo.delete_line_item(line_item1.id)

        items = list(budget_repo.get_line_items(budget.id))
        assert len(items) == 1
        assert items[0].category == "Payroll"

    def test_cascade_delete_line_items(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="2025 Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        budget_repo.add(budget)

        line_item = BudgetLineItem(
            budget_id=budget.id,
            category="Marketing",
            budgeted_amount=Money(Decimal("50000.00"), "USD"),
        )
        budget_repo.add_line_item(line_item)

        budget_repo.delete(budget.id)

        items = list(budget_repo.get_line_items(budget.id))
        assert len(items) == 0

    def test_multiple_line_items(
        self, budget_repo: SQLiteBudgetRepository, sample_entity: Entity
    ):
        budget = Budget(
            name="2025 Budget",
            entity_id=sample_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        budget_repo.add(budget)

        categories = ["Marketing", "Payroll", "Office Supplies", "Travel", "Software"]
        for i, category in enumerate(categories):
            line_item = BudgetLineItem(
                budget_id=budget.id,
                category=category,
                budgeted_amount=Money(Decimal(str((i + 1) * 10000)), "USD"),
            )
            budget_repo.add_line_item(line_item)

        items = list(budget_repo.get_line_items(budget.id))

        assert len(items) == 5
        retrieved_categories = {item.category for item in items}
        assert retrieved_categories == set(categories)


class TestBudgetSchemaMigration:
    def test_budgets_table_exists(self, db: SQLiteDatabase):
        conn = db.get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in tables}

        assert "budgets" in table_names
        assert "budget_line_items" in table_names

    def test_budgets_indexes_exist(self, db: SQLiteDatabase):
        conn = db.get_connection()
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        index_names = {row["name"] for row in indexes}

        assert "idx_budgets_entity" in index_names
        assert "idx_budgets_dates" in index_names
        assert "idx_budget_line_items_budget" in index_names
