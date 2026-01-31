"""Tests for tax document service."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.entities import Account, Entity, Position, Security
from family_office_ledger.domain.transactions import TaxLot
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    AssetClass,
    EntityType,
    Money,
    Quantity,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLitePositionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
)
from family_office_ledger.services.interfaces import LotDisposition
from family_office_ledger.services.tax_documents import (
    AdjustmentCode,
    Form8949,
    Form8949Box,
    Form8949Entry,
    Form8949Part,
    ScheduleD,
    TaxDocumentService,
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
def account_repo(db: SQLiteDatabase) -> SQLiteAccountRepository:
    return SQLiteAccountRepository(db)


@pytest.fixture
def security_repo(db: SQLiteDatabase) -> SQLiteSecurityRepository:
    return SQLiteSecurityRepository(db)


@pytest.fixture
def position_repo(db: SQLiteDatabase) -> SQLitePositionRepository:
    return SQLitePositionRepository(db)


@pytest.fixture
def tax_lot_repo(db: SQLiteDatabase) -> SQLiteTaxLotRepository:
    return SQLiteTaxLotRepository(db)


@pytest.fixture
def entity(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(
        name="Test LLC",
        entity_type=EntityType.LLC,
    )
    entity_repo.add(entity)
    return entity


@pytest.fixture
def account(account_repo: SQLiteAccountRepository, entity: Entity) -> Account:
    account = Account(
        name="Brokerage",
        entity_id=entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.BROKERAGE,
    )
    account_repo.add(account)
    return account


@pytest.fixture
def security(security_repo: SQLiteSecurityRepository) -> Security:
    security = Security(
        symbol="AAPL",
        name="Apple Inc",
        asset_class=AssetClass.EQUITY,
    )
    security_repo.add(security)
    return security


@pytest.fixture
def position(
    position_repo: SQLitePositionRepository, account: Account, security: Security
) -> Position:
    position = Position(
        account_id=account.id,
        security_id=security.id,
    )
    position_repo.add(position)
    return position


@pytest.fixture
def service(
    entity_repo: SQLiteEntityRepository,
    position_repo: SQLitePositionRepository,
    tax_lot_repo: SQLiteTaxLotRepository,
    security_repo: SQLiteSecurityRepository,
) -> TaxDocumentService:
    return TaxDocumentService(
        entity_repo=entity_repo,
        position_repo=position_repo,
        tax_lot_repo=tax_lot_repo,
        security_repo=security_repo,
    )


class TestForm8949Entry:
    def test_short_term_gain(self):
        entry = Form8949Entry(
            description="AAPL - Apple Inc",
            date_acquired=date(2024, 6, 1),
            date_sold=date(2024, 12, 1),
            proceeds=Money(Decimal("1500"), "USD"),
            cost_basis=Money(Decimal("1000"), "USD"),
        )

        assert entry.gain_or_loss.amount == Decimal("500")
        assert entry.is_long_term is False
        assert entry.box == Form8949Box.A

    def test_long_term_loss(self):
        entry = Form8949Entry(
            description="MSFT - Microsoft",
            date_acquired=date(2022, 1, 1),
            date_sold=date(2024, 6, 1),
            proceeds=Money(Decimal("800"), "USD"),
            cost_basis=Money(Decimal("1000"), "USD"),
        )

        assert entry.gain_or_loss.amount == Decimal("-200")
        assert entry.is_long_term is True
        assert entry.box == Form8949Box.D

    def test_non_covered_short_term(self):
        entry = Form8949Entry(
            description="GOOG",
            date_acquired=date(2024, 6, 1),
            date_sold=date(2024, 12, 1),
            proceeds=Money(Decimal("1000"), "USD"),
            cost_basis=Money(Decimal("900"), "USD"),
            is_covered=False,
        )

        assert entry.box == Form8949Box.B

    def test_non_covered_long_term(self):
        entry = Form8949Entry(
            description="GOOG",
            date_acquired=date(2020, 1, 1),
            date_sold=date(2024, 6, 1),
            proceeds=Money(Decimal("1000"), "USD"),
            cost_basis=Money(Decimal("900"), "USD"),
            is_covered=False,
        )

        assert entry.box == Form8949Box.E

    def test_adjustment_affects_gain(self):
        entry = Form8949Entry(
            description="AAPL",
            date_acquired=date(2024, 1, 1),
            date_sold=date(2024, 6, 1),
            proceeds=Money(Decimal("1000"), "USD"),
            cost_basis=Money(Decimal("1200"), "USD"),
            adjustment_code=AdjustmentCode.W,
            adjustment_amount=Money(Decimal("100"), "USD"),
        )

        # proceeds - cost_basis + adjustment = 1000 - 1200 + 100 = -100
        assert entry.gain_or_loss.amount == Decimal("-100")


class TestForm8949Part:
    def test_totals(self):
        entries = [
            Form8949Entry(
                description="AAPL",
                date_acquired=date(2024, 1, 1),
                date_sold=date(2024, 6, 1),
                proceeds=Money(Decimal("1500"), "USD"),
                cost_basis=Money(Decimal("1000"), "USD"),
            ),
            Form8949Entry(
                description="MSFT",
                date_acquired=date(2024, 2, 1),
                date_sold=date(2024, 7, 1),
                proceeds=Money(Decimal("2000"), "USD"),
                cost_basis=Money(Decimal("2200"), "USD"),
            ),
        ]

        part = Form8949Part(box=Form8949Box.A, entries=entries)

        assert part.total_proceeds.amount == Decimal("3500")
        assert part.total_cost_basis.amount == Decimal("3200")
        assert part.total_gain_or_loss.amount == Decimal("300")
        assert part.is_short_term is True

    def test_empty_part(self):
        part = Form8949Part(box=Form8949Box.D, entries=[])

        assert part.total_proceeds.amount == Decimal("0")
        assert part.total_cost_basis.amount == Decimal("0")
        assert part.total_gain_or_loss.amount == Decimal("0")
        assert part.is_short_term is False


class TestForm8949:
    def test_short_term_and_long_term_totals(self):
        short_term_part = Form8949Part(
            box=Form8949Box.A,
            entries=[
                Form8949Entry(
                    description="AAPL",
                    date_acquired=date(2024, 1, 1),
                    date_sold=date(2024, 6, 1),
                    proceeds=Money(Decimal("1500"), "USD"),
                    cost_basis=Money(Decimal("1000"), "USD"),
                ),
            ],
        )

        long_term_part = Form8949Part(
            box=Form8949Box.D,
            entries=[
                Form8949Entry(
                    description="MSFT",
                    date_acquired=date(2020, 1, 1),
                    date_sold=date(2024, 6, 1),
                    proceeds=Money(Decimal("5000"), "USD"),
                    cost_basis=Money(Decimal("2000"), "USD"),
                ),
            ],
        )

        form = Form8949(
            tax_year=2024,
            taxpayer_name="Test LLC",
            parts=[short_term_part, long_term_part],
        )

        assert form.total_short_term_proceeds.amount == Decimal("1500")
        assert form.total_short_term_gain_or_loss.amount == Decimal("500")
        assert form.total_long_term_proceeds.amount == Decimal("5000")
        assert form.total_long_term_gain_or_loss.amount == Decimal("3000")


class TestScheduleD:
    def test_line_calculations(self):
        schedule = ScheduleD(
            tax_year=2024,
            taxpayer_name="Test LLC",
            line_1a=Money(Decimal("500"), "USD"),
            line_1b=Money(Decimal("-200"), "USD"),
            line_8a=Money(Decimal("3000"), "USD"),
            line_8b=Money(Decimal("1000"), "USD"),
        )

        assert schedule.line_7.amount == Decimal("300")
        assert schedule.line_15.amount == Decimal("4000")
        assert schedule.line_16.amount == Decimal("4300")


class TestTaxDocumentServiceGenerateForm8949:
    def test_generates_form_from_dispositions(self, service: TaxDocumentService):
        dispositions = [
            LotDisposition(
                lot_id=uuid4(),
                quantity_sold=Quantity(Decimal("100")),
                cost_basis=Money(Decimal("1000"), "USD"),
                proceeds=Money(Decimal("1500"), "USD"),
                acquisition_date=date(2024, 1, 15),
                disposition_date=date(2024, 6, 15),
            ),
            LotDisposition(
                lot_id=uuid4(),
                quantity_sold=Quantity(Decimal("50")),
                cost_basis=Money(Decimal("5000"), "USD"),
                proceeds=Money(Decimal("8000"), "USD"),
                acquisition_date=date(2020, 3, 1),
                disposition_date=date(2024, 9, 1),
            ),
        ]

        form = service.generate_form_8949(
            dispositions=dispositions,
            tax_year=2024,
            taxpayer_name="Test Entity",
        )

        assert form.tax_year == 2024
        assert form.taxpayer_name == "Test Entity"
        assert len(form.short_term_parts) == 1
        assert len(form.long_term_parts) == 1
        assert form.total_short_term_gain_or_loss.amount == Decimal("500")
        assert form.total_long_term_gain_or_loss.amount == Decimal("3000")

    def test_filters_by_tax_year(self, service: TaxDocumentService):
        dispositions = [
            LotDisposition(
                lot_id=uuid4(),
                quantity_sold=Quantity(Decimal("100")),
                cost_basis=Money(Decimal("1000"), "USD"),
                proceeds=Money(Decimal("1500"), "USD"),
                acquisition_date=date(2023, 1, 15),
                disposition_date=date(2023, 6, 15),
            ),
            LotDisposition(
                lot_id=uuid4(),
                quantity_sold=Quantity(Decimal("100")),
                cost_basis=Money(Decimal("2000"), "USD"),
                proceeds=Money(Decimal("2500"), "USD"),
                acquisition_date=date(2024, 1, 15),
                disposition_date=date(2024, 6, 15),
            ),
        ]

        form_2024 = service.generate_form_8949(
            dispositions=dispositions,
            tax_year=2024,
            taxpayer_name="Test",
        )

        assert len(form_2024.short_term_parts) == 1
        assert form_2024.total_short_term_gain_or_loss.amount == Decimal("500")


class TestTaxDocumentServiceGenerateScheduleD:
    def test_generates_schedule_from_form_8949(self, service: TaxDocumentService):
        short_term_part = Form8949Part(
            box=Form8949Box.A,
            entries=[
                Form8949Entry(
                    description="AAPL",
                    date_acquired=date(2024, 1, 1),
                    date_sold=date(2024, 6, 1),
                    proceeds=Money(Decimal("1500"), "USD"),
                    cost_basis=Money(Decimal("1000"), "USD"),
                ),
            ],
        )

        form_8949 = Form8949(
            tax_year=2024,
            taxpayer_name="Test",
            parts=[short_term_part],
        )

        schedule_d = service.generate_schedule_d(form_8949)

        assert schedule_d.line_1a.amount == Decimal("500")
        assert schedule_d.line_7.amount == Decimal("500")
        assert schedule_d.line_16.amount == Decimal("500")


class TestTaxDocumentServiceGenerateFromEntity:
    def test_generates_documents_for_entity(
        self,
        service: TaxDocumentService,
        entity: Entity,
        position: Position,
        tax_lot_repo: SQLiteTaxLotRepository,
    ):
        lot = TaxLot(
            position_id=position.id,
            acquisition_date=date(2024, 1, 1),
            cost_per_share=Money(Decimal("10"), "USD"),
            original_quantity=Quantity(Decimal("100")),
        )
        lot.remaining_quantity = Quantity(Decimal("0"))
        lot.disposition_date = date(2024, 6, 15)
        tax_lot_repo.add(lot)

        form_8949, schedule_d, summary = service.generate_from_entity(
            entity_id=entity.id,
            tax_year=2024,
        )

        assert form_8949.tax_year == 2024
        assert form_8949.taxpayer_name == "Test LLC"
        assert summary.short_term_transactions == 1
        assert summary.entity_name == "Test LLC"

    def test_raises_for_missing_entity(self, service: TaxDocumentService):
        with pytest.raises(ValueError, match="Entity not found"):
            service.generate_from_entity(
                entity_id=uuid4(),
                tax_year=2024,
            )


class TestTaxDocumentServiceExportCsv:
    def test_exports_form_8949_to_csv(self, service: TaxDocumentService):
        short_term_part = Form8949Part(
            box=Form8949Box.A,
            entries=[
                Form8949Entry(
                    description="AAPL - Apple Inc",
                    date_acquired=date(2024, 1, 15),
                    date_sold=date(2024, 6, 15),
                    proceeds=Money(Decimal("1500"), "USD"),
                    cost_basis=Money(Decimal("1000"), "USD"),
                ),
            ],
        )

        form_8949 = Form8949(
            tax_year=2024,
            taxpayer_name="Test",
            parts=[short_term_part],
        )

        csv_content = service.export_form_8949_csv(form_8949)

        assert "Description" in csv_content
        assert "AAPL - Apple Inc" in csv_content
        assert "2024-01-15" in csv_content
        assert "2024-06-15" in csv_content
        assert "1500" in csv_content
        assert "1000" in csv_content
        assert "Short-term" in csv_content
        assert "A" in csv_content


class TestTaxDocumentServiceExportScheduleDSummary:
    def test_exports_schedule_d_summary(self, service: TaxDocumentService):
        schedule = ScheduleD(
            tax_year=2024,
            taxpayer_name="Test LLC",
            line_1a=Money(Decimal("500"), "USD"),
            line_8a=Money(Decimal("3000"), "USD"),
        )

        summary = service.export_schedule_d_summary(schedule)

        assert summary["tax_year"] == 2024
        assert summary["taxpayer_name"] == "Test LLC"
        assert summary["part_i_short_term"]["line_1a_box_a"] == "500"
        assert summary["part_ii_long_term"]["line_8a_box_d"] == "3000"
        assert summary["line_16_combined"] == "3500"
