"""Comprehensive tests for the IngestionService.

Tests cover:
- Entity auto-creation (LLC, Trust, Holdings patterns)
- Account auto-creation (no duplicates)
- Each transaction type books correct journal entries
- Investment purchases create tax lots
- Investment sales dispose tax lots via LotMatchingService
- UNCLASSIFIED transactions book to Suspense
- Idempotency (re-import doesn't duplicate entities/accounts)
"""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from family_office_ledger.domain.entities import Account, Entity, Position, Security
from family_office_ledger.domain.transactions import TaxLot, Transaction
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    AcquisitionType,
    EntityType,
    LotSelection,
    Money,
    Quantity,
    TransactionType,
)
from family_office_ledger.parsers.bank_parsers import ParsedTransaction
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    EntityRepository,
    PositionRepository,
    SecurityRepository,
    TaxLotRepository,
    TransactionRepository,
)
from family_office_ledger.services.ingestion import (
    IngestionResult,
    IngestionService,
)
from family_office_ledger.services.interfaces import (
    LedgerService,
    LotDisposition,
    LotMatchingService,
)
from family_office_ledger.services.transaction_classifier import TransactionClassifier

# =============================================================================
# Mock Repository Implementations
# =============================================================================


class MockEntityRepository(EntityRepository):
    """In-memory entity repository for testing."""

    def __init__(self) -> None:
        self._entities: dict[UUID, Entity] = {}
        self._by_name: dict[str, Entity] = {}

    def add(self, entity: Entity) -> None:
        self._entities[entity.id] = entity
        self._by_name[entity.name] = entity

    def get(self, entity_id: UUID) -> Entity | None:
        return self._entities.get(entity_id)

    def get_by_name(self, name: str) -> Entity | None:
        return self._by_name.get(name)

    def list_all(self) -> Iterable[Entity]:
        return self._entities.values()

    def list_active(self) -> Iterable[Entity]:
        return [e for e in self._entities.values() if e.is_active]

    def update(self, entity: Entity) -> None:
        self._entities[entity.id] = entity
        self._by_name[entity.name] = entity

    def delete(self, entity_id: UUID) -> None:
        entity = self._entities.pop(entity_id, None)
        if entity:
            self._by_name.pop(entity.name, None)


class MockAccountRepository(AccountRepository):
    """In-memory account repository for testing."""

    def __init__(self) -> None:
        self._accounts: dict[UUID, Account] = {}
        self._by_entity: dict[UUID, dict[str, Account]] = {}

    def add(self, account: Account) -> None:
        self._accounts[account.id] = account
        if account.entity_id not in self._by_entity:
            self._by_entity[account.entity_id] = {}
        self._by_entity[account.entity_id][account.name] = account

    def get(self, account_id: UUID) -> Account | None:
        return self._accounts.get(account_id)

    def get_by_name(self, name: str, entity_id: UUID) -> Account | None:
        entity_accounts = self._by_entity.get(entity_id, {})
        return entity_accounts.get(name)

    def list_by_entity(self, entity_id: UUID) -> Iterable[Account]:
        return self._by_entity.get(entity_id, {}).values()

    def list_investment_accounts(
        self, entity_id: UUID | None = None
    ) -> Iterable[Account]:
        accounts = []
        for acct in self._accounts.values():
            if acct.is_investment_account:
                if entity_id is None or acct.entity_id == entity_id:
                    accounts.append(acct)
        return accounts

    def update(self, account: Account) -> None:
        self._accounts[account.id] = account
        if account.entity_id not in self._by_entity:
            self._by_entity[account.entity_id] = {}
        self._by_entity[account.entity_id][account.name] = account

    def delete(self, account_id: UUID) -> None:
        account = self._accounts.pop(account_id, None)
        if account:
            entity_accounts = self._by_entity.get(account.entity_id, {})
            entity_accounts.pop(account.name, None)


class MockSecurityRepository(SecurityRepository):
    """In-memory security repository for testing."""

    def __init__(self) -> None:
        self._securities: dict[UUID, Security] = {}
        self._by_symbol: dict[str, Security] = {}
        self._by_cusip: dict[str, Security] = {}

    def add(self, security: Security) -> None:
        self._securities[security.id] = security
        if security.symbol:
            self._by_symbol[security.symbol] = security
        if security.cusip:
            self._by_cusip[security.cusip] = security

    def get(self, security_id: UUID) -> Security | None:
        return self._securities.get(security_id)

    def get_by_symbol(self, symbol: str) -> Security | None:
        return self._by_symbol.get(symbol)

    def get_by_cusip(self, cusip: str) -> Security | None:
        return self._by_cusip.get(cusip)

    def list_all(self) -> Iterable[Security]:
        return self._securities.values()

    def list_qsbs_eligible(self) -> Iterable[Security]:
        return [s for s in self._securities.values() if s.is_qsbs_eligible]

    def update(self, security: Security) -> None:
        self._securities[security.id] = security
        if security.symbol:
            self._by_symbol[security.symbol] = security
        if security.cusip:
            self._by_cusip[security.cusip] = security


class MockPositionRepository(PositionRepository):
    """In-memory position repository for testing."""

    def __init__(self) -> None:
        self._positions: dict[UUID, Position] = {}
        self._by_account_security: dict[tuple[UUID, UUID], Position] = {}

    def add(self, position: Position) -> None:
        self._positions[position.id] = position
        self._by_account_security[(position.account_id, position.security_id)] = (
            position
        )

    def get(self, position_id: UUID) -> Position | None:
        return self._positions.get(position_id)

    def get_by_account_and_security(
        self, account_id: UUID, security_id: UUID
    ) -> Position | None:
        return self._by_account_security.get((account_id, security_id))

    def list_by_account(self, account_id: UUID) -> Iterable[Position]:
        return [p for p in self._positions.values() if p.account_id == account_id]

    def list_by_security(self, security_id: UUID) -> Iterable[Position]:
        return [p for p in self._positions.values() if p.security_id == security_id]

    def list_by_entity(self, entity_id: UUID) -> Iterable[Position]:
        # Would need account repo to implement properly
        return []

    def update(self, position: Position) -> None:
        self._positions[position.id] = position
        self._by_account_security[(position.account_id, position.security_id)] = (
            position
        )


class MockTaxLotRepository(TaxLotRepository):
    """In-memory tax lot repository for testing."""

    def __init__(self) -> None:
        self._lots: dict[UUID, TaxLot] = {}
        self._by_position: dict[UUID, list[TaxLot]] = {}

    def add(self, lot: TaxLot) -> None:
        self._lots[lot.id] = lot
        if lot.position_id not in self._by_position:
            self._by_position[lot.position_id] = []
        self._by_position[lot.position_id].append(lot)

    def get(self, lot_id: UUID) -> TaxLot | None:
        return self._lots.get(lot_id)

    def list_by_position(self, position_id: UUID) -> Iterable[TaxLot]:
        return self._by_position.get(position_id, [])

    def list_open_by_position(self, position_id: UUID) -> Iterable[TaxLot]:
        return [
            lot
            for lot in self._by_position.get(position_id, [])
            if not lot.is_fully_disposed
        ]

    def list_by_acquisition_date_range(
        self, position_id: UUID, start_date: date, end_date: date
    ) -> Iterable[TaxLot]:
        return [
            lot
            for lot in self._by_position.get(position_id, [])
            if start_date <= lot.acquisition_date <= end_date
        ]

    def list_wash_sale_candidates(
        self, position_id: UUID, sale_date: date
    ) -> Iterable[TaxLot]:
        return []

    def update(self, lot: TaxLot) -> None:
        self._lots[lot.id] = lot


class MockTransactionRepository(TransactionRepository):
    """In-memory transaction repository for testing."""

    def __init__(self) -> None:
        self._transactions: dict[UUID, Transaction] = {}

    def add(self, txn: Transaction) -> None:
        self._transactions[txn.id] = txn

    def get(self, txn_id: UUID) -> Transaction | None:
        return self._transactions.get(txn_id)

    def list_by_account(
        self,
        account_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Iterable[Transaction]:
        results = []
        for txn in self._transactions.values():
            if account_id in txn.account_ids:
                if start_date and txn.transaction_date < start_date:
                    continue
                if end_date and txn.transaction_date > end_date:
                    continue
                results.append(txn)
        return results

    def list_by_entity(
        self,
        entity_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Iterable[Transaction]:
        return []

    def list_by_date_range(
        self, start_date: date, end_date: date
    ) -> Iterable[Transaction]:
        return [
            txn
            for txn in self._transactions.values()
            if start_date <= txn.transaction_date <= end_date
        ]

    def get_reversals(self, txn_id: UUID) -> Iterable[Transaction]:
        return [
            txn
            for txn in self._transactions.values()
            if txn.reverses_transaction_id == txn_id
        ]

    def update(self, txn: Transaction) -> None:
        self._transactions[txn.id] = txn


# =============================================================================
# Mock Service Implementations
# =============================================================================


class MockLedgerService(LedgerService):
    """Mock ledger service that validates and stores transactions."""

    def __init__(
        self, txn_repo: MockTransactionRepository, account_repo: MockAccountRepository
    ) -> None:
        self._txn_repo = txn_repo
        self._account_repo = account_repo
        self.posted_transactions: list[Transaction] = []

    def post_transaction(self, txn: Transaction) -> None:
        self.validate_transaction(txn)
        self._txn_repo.add(txn)
        self.posted_transactions.append(txn)

    def validate_transaction(self, txn: Transaction) -> None:
        # Check all accounts exist
        for entry in txn.entries:
            account = self._account_repo.get(entry.account_id)
            if account is None:
                raise ValueError(f"Account not found: {entry.account_id}")

        # Check balanced
        if not txn.is_balanced:
            raise ValueError(
                f"Transaction is unbalanced: debits={txn.total_debits.amount}, "
                f"credits={txn.total_credits.amount}"
            )

    def reverse_transaction(
        self, txn_id: UUID, reversal_date: date, memo: str
    ) -> Transaction:
        raise NotImplementedError

    def get_account_balance(
        self, account_id: UUID, as_of_date: date | None = None
    ) -> Money:
        return Money.zero()

    def get_entity_balance(
        self, entity_id: UUID, as_of_date: date | None = None
    ) -> Money:
        return Money.zero()


class MockLotMatchingService(LotMatchingService):
    """Mock lot matching service for testing."""

    def __init__(self, tax_lot_repo: MockTaxLotRepository) -> None:
        self._tax_lot_repo = tax_lot_repo
        self.sales_executed: list[tuple[UUID, Quantity, Money]] = []

    def match_sale(
        self,
        position_id: UUID,
        quantity: Quantity,
        method: LotSelection,
        specific_lot_ids: list[UUID] | None = None,
    ) -> list[TaxLot]:
        return list(self._tax_lot_repo.list_open_by_position(position_id))

    def execute_sale(
        self,
        position_id: UUID,
        quantity: Quantity,
        proceeds: Money,
        sale_date: date,
        method: LotSelection,
        specific_lot_ids: list[UUID] | None = None,
    ) -> list[LotDisposition]:
        self.sales_executed.append((position_id, quantity, proceeds))
        open_lots = list(self._tax_lot_repo.list_open_by_position(position_id))

        dispositions = []
        remaining_qty = quantity.value

        for lot in open_lots:
            if remaining_qty <= 0:
                break

            sell_qty = min(remaining_qty, lot.remaining_quantity.value)
            cost_basis = lot.sell(Quantity(sell_qty), sale_date)

            proportion = sell_qty / quantity.value
            lot_proceeds = Money(
                (proceeds.amount * Decimal(str(proportion))).quantize(Decimal("0.01"))
            )

            dispositions.append(
                LotDisposition(
                    lot_id=lot.id,
                    quantity_sold=Quantity(sell_qty),
                    cost_basis=cost_basis,
                    proceeds=lot_proceeds,
                    acquisition_date=lot.acquisition_date,
                    disposition_date=sale_date,
                )
            )

            self._tax_lot_repo.update(lot)
            remaining_qty -= sell_qty

        return dispositions

    def detect_wash_sales(
        self,
        position_id: UUID,
        sale_date: date,
        loss_amount: Money,
    ) -> list[TaxLot]:
        return []

    def get_open_lots(self, position_id: UUID) -> list[TaxLot]:
        return list(self._tax_lot_repo.list_open_by_position(position_id))

    def get_position_cost_basis(self, position_id: UUID) -> Money:
        lots = list(self._tax_lot_repo.list_open_by_position(position_id))
        total = sum(lot.remaining_cost.amount for lot in lots)
        return Money(total)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def entity_repo() -> MockEntityRepository:
    return MockEntityRepository()


@pytest.fixture
def account_repo() -> MockAccountRepository:
    return MockAccountRepository()


@pytest.fixture
def security_repo() -> MockSecurityRepository:
    return MockSecurityRepository()


@pytest.fixture
def position_repo() -> MockPositionRepository:
    return MockPositionRepository()


@pytest.fixture
def tax_lot_repo() -> MockTaxLotRepository:
    return MockTaxLotRepository()


@pytest.fixture
def txn_repo() -> MockTransactionRepository:
    return MockTransactionRepository()


@pytest.fixture
def ledger_service(
    txn_repo: MockTransactionRepository,
    account_repo: MockAccountRepository,
) -> MockLedgerService:
    return MockLedgerService(txn_repo, account_repo)


@pytest.fixture
def lot_matching_service(tax_lot_repo: MockTaxLotRepository) -> MockLotMatchingService:
    return MockLotMatchingService(tax_lot_repo)


@pytest.fixture
def classifier() -> TransactionClassifier:
    return TransactionClassifier()


@pytest.fixture
def ingestion_service(
    entity_repo: MockEntityRepository,
    account_repo: MockAccountRepository,
    security_repo: MockSecurityRepository,
    position_repo: MockPositionRepository,
    tax_lot_repo: MockTaxLotRepository,
    ledger_service: MockLedgerService,
    lot_matching_service: MockLotMatchingService,
    classifier: TransactionClassifier,
) -> IngestionService:
    return IngestionService(
        entity_repo=entity_repo,
        account_repo=account_repo,
        security_repo=security_repo,
        position_repo=position_repo,
        tax_lot_repo=tax_lot_repo,
        ledger_service=ledger_service,
        lot_matching_service=lot_matching_service,
        transaction_classifier=classifier,
    )


def create_parsed_transaction(
    amount: Decimal,
    description: str = "Test transaction",
    account_name: str = "Test Entity - 1234",
    account_number: str = "1234",
    other_party: str | None = None,
    symbol: str | None = None,
    cusip: str | None = None,
    quantity: Decimal | None = None,
    price: Decimal | None = None,
    activity_type: str | None = None,
    txn_date: date | None = None,
) -> ParsedTransaction:
    """Helper to create ParsedTransaction for testing."""
    return ParsedTransaction(
        import_id=f"test_{uuid4().hex[:8]}",
        date=txn_date or date(2026, 1, 15),
        description=description,
        amount=amount,
        account_number=account_number,
        account_name=account_name,
        other_party=other_party,
        symbol=symbol,
        cusip=cusip,
        quantity=quantity,
        price=price,
        activity_type=activity_type,
        raw_data={},
    )


# =============================================================================
# Entity Detection Tests
# =============================================================================


class TestEntityDetection:
    """Test entity type detection from names."""

    def test_detect_llc(self, ingestion_service: IngestionService) -> None:
        """LLC keyword detected."""
        entity_type = ingestion_service._detect_entity_type("Acme Holdings LLC")
        assert entity_type == EntityType.LLC

    def test_detect_llc_period_format(
        self, ingestion_service: IngestionService
    ) -> None:
        """L.L.C. format detected."""
        entity_type = ingestion_service._detect_entity_type("Acme L.L.C.")
        assert entity_type == EntityType.LLC

    def test_detect_trust(self, ingestion_service: IngestionService) -> None:
        """Trust keyword detected."""
        entity_type = ingestion_service._detect_entity_type("The Ketov Family Trust")
        assert entity_type == EntityType.TRUST

    def test_detect_holdings(self, ingestion_service: IngestionService) -> None:
        """Holdings keyword maps to HOLDING_CO."""
        entity_type = ingestion_service._detect_entity_type("ABC Holdings")
        assert entity_type == EntityType.HOLDING_CO

    def test_detect_investments(self, ingestion_service: IngestionService) -> None:
        """Investments keyword maps to HOLDING_CO."""
        entity_type = ingestion_service._detect_entity_type("XYZ Investments")
        assert entity_type == EntityType.HOLDING_CO

    def test_detect_partnership(self, ingestion_service: IngestionService) -> None:
        """Partnership keyword detected."""
        entity_type = ingestion_service._detect_entity_type("ABC Partnership")
        assert entity_type == EntityType.PARTNERSHIP

    def test_detect_lp(self, ingestion_service: IngestionService) -> None:
        """LP keyword maps to Partnership."""
        entity_type = ingestion_service._detect_entity_type("Zigg Capital LP")
        assert entity_type == EntityType.PARTNERSHIP

    def test_default_to_individual(self, ingestion_service: IngestionService) -> None:
        """No pattern match defaults to INDIVIDUAL."""
        entity_type = ingestion_service._detect_entity_type("John Smith")
        assert entity_type == EntityType.INDIVIDUAL

    def test_case_insensitive(self, ingestion_service: IngestionService) -> None:
        """Detection is case-insensitive."""
        entity_type = ingestion_service._detect_entity_type("acme llc")
        assert entity_type == EntityType.LLC


# =============================================================================
# Account Name Parsing Tests
# =============================================================================


class TestAccountNameParsing:
    """Test account name parsing to entity and account suffix."""

    def test_parse_with_separator(self, ingestion_service: IngestionService) -> None:
        """Standard format with ' - ' separator."""
        entity, suffix = ingestion_service._parse_account_name(
            "ENTROPY MANAGEMENT GROUP - 7111", "7111"
        )
        assert entity == "ENTROPY MANAGEMENT GROUP"
        assert suffix == "7111"

    def test_parse_multiple_separators(
        self, ingestion_service: IngestionService
    ) -> None:
        """Multiple ' - ' separators use last part."""
        entity, suffix = ingestion_service._parse_account_name(
            "Kaneda - 8231 - 8231", "8231"
        )
        assert entity == "Kaneda"
        assert suffix == "8231"

    def test_parse_no_separator(self, ingestion_service: IngestionService) -> None:
        """No separator uses whole name as entity."""
        entity, suffix = ingestion_service._parse_account_name("Atlantic Blue", "9999")
        assert entity == "Atlantic Blue"
        assert suffix == "9999"

    def test_parse_empty_account_name(
        self, ingestion_service: IngestionService
    ) -> None:
        """Empty account name uses account number."""
        entity, suffix = ingestion_service._parse_account_name("", "1234")
        assert entity == ""
        assert suffix == "1234"

    def test_parse_default_main(self, ingestion_service: IngestionService) -> None:
        """Missing account number defaults to 'Main'."""
        entity, suffix = ingestion_service._parse_account_name("Test Entity", "")
        assert entity == "Test Entity"
        assert suffix == "Main"


# =============================================================================
# Get or Create Entity Tests
# =============================================================================


class TestGetOrCreateEntity:
    """Test entity get_or_create pattern."""

    def test_creates_new_entity(
        self,
        ingestion_service: IngestionService,
        entity_repo: MockEntityRepository,
    ) -> None:
        """Creates entity when not exists."""
        entity = ingestion_service._get_or_create_entity("New Entity LLC")

        assert entity.name == "New Entity LLC"
        assert entity.entity_type == EntityType.LLC
        assert entity_repo.get_by_name("New Entity LLC") is not None

    def test_returns_existing_entity(
        self,
        ingestion_service: IngestionService,
        entity_repo: MockEntityRepository,
    ) -> None:
        """Returns existing entity without duplicate."""
        # Create first
        entity1 = ingestion_service._get_or_create_entity("Existing Entity")
        # Get again
        entity2 = ingestion_service._get_or_create_entity("Existing Entity")

        assert entity1.id == entity2.id
        assert len(list(entity_repo.list_all())) == 1

    def test_cache_prevents_duplicate_lookup(
        self,
        ingestion_service: IngestionService,
        entity_repo: MockEntityRepository,
    ) -> None:
        """Cache prevents duplicate repository lookups."""
        # First call
        entity1 = ingestion_service._get_or_create_entity("Cache Test")
        # Clear repo but keep cache
        entity_repo._entities.clear()
        entity_repo._by_name.clear()
        # Second call should use cache
        entity2 = ingestion_service._get_or_create_entity("Cache Test")

        assert entity1.id == entity2.id


# =============================================================================
# Get or Create Account Tests
# =============================================================================


class TestGetOrCreateAccount:
    """Test account get_or_create pattern."""

    def test_creates_new_account(
        self,
        ingestion_service: IngestionService,
        entity_repo: MockEntityRepository,
        account_repo: MockAccountRepository,
    ) -> None:
        """Creates account when not exists."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        account = ingestion_service._get_or_create_account(
            entity, "Test Account", AccountType.ASSET, AccountSubType.CHECKING
        )

        assert account.name == "Test Account"
        assert account.entity_id == entity.id
        assert account_repo.get_by_name("Test Account", entity.id) is not None

    def test_returns_existing_account(
        self,
        ingestion_service: IngestionService,
        entity_repo: MockEntityRepository,
        account_repo: MockAccountRepository,
    ) -> None:
        """Returns existing account without duplicate."""
        entity = ingestion_service._get_or_create_entity("Test Entity")

        # Create first
        account1 = ingestion_service._get_or_create_account(
            entity, "Test Account", AccountType.ASSET, AccountSubType.CHECKING
        )
        # Get again
        account2 = ingestion_service._get_or_create_account(
            entity, "Test Account", AccountType.ASSET, AccountSubType.CHECKING
        )

        assert account1.id == account2.id
        assert len(list(account_repo.list_by_entity(entity.id))) == 1

    def test_same_name_different_entities(
        self,
        ingestion_service: IngestionService,
        entity_repo: MockEntityRepository,
        account_repo: MockAccountRepository,
    ) -> None:
        """Same account name under different entities creates separate accounts."""
        entity1 = ingestion_service._get_or_create_entity("Entity One")
        entity2 = ingestion_service._get_or_create_entity("Entity Two")

        account1 = ingestion_service._get_or_create_account(
            entity1, "Cash", AccountType.ASSET, AccountSubType.CHECKING
        )
        account2 = ingestion_service._get_or_create_account(
            entity2, "Cash", AccountType.ASSET, AccountSubType.CHECKING
        )

        assert account1.id != account2.id


# =============================================================================
# Transaction Booking Tests - Individual Types
# =============================================================================


class TestBookInterest:
    """Test INTEREST transaction booking."""

    def test_books_interest_correctly(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
        entity_repo: MockEntityRepository,
    ) -> None:
        """INTEREST: Dr Cash, Cr Interest Income."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )
        income_account = ingestion_service._get_standard_account(
            "Interest Income", entity
        )

        parsed = create_parsed_transaction(
            amount=Decimal("100.00"),
            description="Interest payment",
        )

        ingestion_service._book_interest(parsed, entity, cash_account)

        assert len(ledger_service.posted_transactions) == 1
        txn = ledger_service.posted_transactions[0]

        assert txn.is_balanced
        assert len(txn.entries) == 2

        # Check debit to cash
        debit_entry = next(e for e in txn.entries if e.debit_amount.is_positive)
        assert debit_entry.account_id == cash_account.id
        assert debit_entry.debit_amount.amount == Decimal("100.00")

        # Check credit to income
        credit_entry = next(e for e in txn.entries if e.credit_amount.is_positive)
        assert credit_entry.account_id == income_account.id
        assert credit_entry.credit_amount.amount == Decimal("100.00")


class TestBookExpense:
    """Test EXPENSE transaction booking."""

    def test_books_expense_correctly(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
        entity_repo: MockEntityRepository,
    ) -> None:
        """EXPENSE: Dr Expense, Cr Cash."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )
        expense_account = ingestion_service._get_standard_account(
            "Legal & Professional Fees", entity
        )

        parsed = create_parsed_transaction(
            amount=Decimal("-500.00"),  # Negative for expense
            description="Legal fees",
        )

        ingestion_service._book_expense(parsed, entity, cash_account)

        assert len(ledger_service.posted_transactions) == 1
        txn = ledger_service.posted_transactions[0]

        assert txn.is_balanced

        # Check debit to expense
        debit_entry = next(e for e in txn.entries if e.debit_amount.is_positive)
        assert debit_entry.account_id == expense_account.id
        assert debit_entry.debit_amount.amount == Decimal("500.00")

        # Check credit to cash
        credit_entry = next(e for e in txn.entries if e.credit_amount.is_positive)
        assert credit_entry.account_id == cash_account.id


class TestBookTransfer:
    """Test TRANSFER transaction booking."""

    def test_books_transfer_inflow(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """TRANSFER inflow: Dr Cash, Cr Due From/To Affiliates."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("1000.00"),  # Positive = inflow
            description="Wire transfer in",
        )

        ingestion_service._book_transfer(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced

    def test_books_transfer_outflow(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """TRANSFER outflow: Dr Due From/To Affiliates, Cr Cash."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("-1000.00"),  # Negative = outflow
            description="Wire transfer out",
        )

        ingestion_service._book_transfer(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced


class TestBookTrustTransfer:
    """Test TRUST_TRANSFER transaction booking."""

    def test_books_trust_transfer_outflow(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """TRUST_TRANSFER outflow: Dr Due From Trust, Cr Cash."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )
        trust_account = ingestion_service._get_standard_account(
            "Due From Trust", entity
        )

        parsed = create_parsed_transaction(
            amount=Decimal("-50000.00"),
            description="Wire to trust",
            other_party="THE KETOV TRUST",
        )

        ingestion_service._book_trust_transfer(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced

        # Check debit to trust receivable
        debit_entry = next(e for e in txn.entries if e.debit_amount.is_positive)
        assert debit_entry.account_id == trust_account.id


class TestBookContributionDistribution:
    """Test CONTRIBUTION_DISTRIBUTION transaction booking."""

    def test_books_capital_call(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """Capital call: Dr Investment - Fund, Cr Cash."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("-125000.00"),  # Negative = capital call
            description="Capital call",
            other_party="ZIGG CAPITAL I LP",
        )

        ingestion_service._book_contribution_distribution(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced

    def test_books_distribution(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """Distribution: Dr Cash, Cr Investment - Fund."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("75000.00"),  # Positive = distribution
            description="Distribution",
            other_party="ZIGG CAPITAL I LP",
        )

        ingestion_service._book_contribution_distribution(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced


class TestBookContributionToEntity:
    """Test CONTRIBUTION_TO_ENTITY transaction booking."""

    def test_books_capital_contribution(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """Capital contribution: Dr Cash, Cr Member's Capital."""
        entity = ingestion_service._get_or_create_entity("Test Entity LLC")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )
        capital_account = ingestion_service._get_standard_account(
            "Member's Capital", entity
        )

        parsed = create_parsed_transaction(
            amount=Decimal("250.00"),
            description="Capital contribution",
        )

        ingestion_service._book_contribution_to_entity(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced

        # Check credit to capital
        credit_entry = next(e for e in txn.entries if e.credit_amount.is_positive)
        assert credit_entry.account_id == capital_account.id


class TestBookLoan:
    """Test LOAN transaction booking."""

    def test_books_loan(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """LOAN: Dr Notes Receivable, Cr Cash."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("-101600.00"),
            description="Loan to trust",
            other_party="THE KANEDA TRUST",
        )

        ingestion_service._book_loan(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced


class TestBookLoanRepayment:
    """Test LOAN_REPAYMENT transaction booking."""

    def test_books_loan_repayment(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """LOAN_REPAYMENT: Dr Cash, Cr Notes Receivable + Interest Income."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("2817062.58"),
            description="Loan repayment received",
        )

        ingestion_service._book_loan_repayment(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced
        assert len(txn.entries) == 3  # Cash, Notes Receivable, Interest Income


class TestBookPurchaseQSBS:
    """Test PURCHASE_QSBS transaction booking."""

    def test_books_purchase_and_creates_tax_lot(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
        tax_lot_repo: MockTaxLotRepository,
    ) -> None:
        """PURCHASE_QSBS: Dr Investment, Cr Cash + CREATE TAX LOT."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("-400000.00"),
            description="Investment purchase",
            other_party="COGNITION AI INC",
            symbol="COGN",
            quantity=Decimal("10000"),
            price=Decimal("40.00"),
        )

        lots_created = ingestion_service._book_purchase_qsbs(
            parsed, entity, cash_account
        )

        assert lots_created == 1
        assert len(ledger_service.posted_transactions) == 1
        assert ledger_service.posted_transactions[0].is_balanced

        # Verify tax lot created
        all_lots = list(tax_lot_repo._lots.values())
        assert len(all_lots) == 1
        lot = all_lots[0]
        assert lot.original_quantity.value == Decimal("10000")
        assert lot.cost_per_share.amount == Decimal("40.00")
        assert lot.acquisition_type == AcquisitionType.PURCHASE


class TestBookPurchaseNonQSBS:
    """Test PURCHASE_NON_QSBS transaction booking."""

    def test_books_purchase_and_creates_tax_lot(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
        tax_lot_repo: MockTaxLotRepository,
    ) -> None:
        """PURCHASE_NON_QSBS: Dr Investment, Cr Cash + CREATE TAX LOT."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("-224999.56"),
            description="Non-QSBS investment",
            other_party="TOGETHER COMPUTER INC",
            cusip="12345678",
        )

        lots_created = ingestion_service._book_purchase_non_qsbs(
            parsed, entity, cash_account
        )

        assert lots_created == 1
        assert ledger_service.posted_transactions[0].is_balanced


class TestBookPurchaseOZFund:
    """Test PURCHASE_OZ_FUND transaction booking."""

    def test_books_oz_fund_purchase(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
        tax_lot_repo: MockTaxLotRepository,
    ) -> None:
        """PURCHASE_OZ_FUND: Dr Investment - OZ Fund, Cr Cash + CREATE TAX LOT."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("-595000.00"),
            description="OZ Fund investment",
            other_party="BV SOUTH SLC OZ FUND",
        )

        lots_created = ingestion_service._book_purchase_oz_fund(
            parsed, entity, cash_account
        )

        assert lots_created == 1


class TestBookSaleQSBS:
    """Test SALE_QSBS transaction booking."""

    def test_books_sale_with_gain(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
        tax_lot_repo: MockTaxLotRepository,
        position_repo: MockPositionRepository,
        security_repo: MockSecurityRepository,
        account_repo: MockAccountRepository,
    ) -> None:
        """SALE_QSBS with gain: Dr Cash, Cr Investment + Gain."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )
        investment_account = ingestion_service._get_standard_account(
            "Investment - QSBS Stock", entity
        )

        # Create security and position with existing tax lot
        security = Security(symbol="DRGNR", name="Dragoneer", is_qsbs_eligible=True)
        security_repo.add(security)

        position = Position(account_id=investment_account.id, security_id=security.id)
        position_repo.add(position)

        # Create tax lot with cost basis
        lot = TaxLot(
            position_id=position.id,
            acquisition_date=date(2020, 1, 1),
            cost_per_share=Money(Decimal("10.00")),
            original_quantity=Quantity(Decimal("1000")),
            acquisition_type=AcquisitionType.PURCHASE,
        )
        tax_lot_repo.add(lot)

        parsed = create_parsed_transaction(
            amount=Decimal("200000.00"),  # Proceeds
            description="QSBS sale",
            symbol="DRGNR",
            quantity=Decimal("1000"),
        )

        ingestion_service._book_sale_qsbs(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced


class TestBookSaleNonQSBS:
    """Test SALE_NON_QSBS transaction booking."""

    def test_books_sale(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """SALE_NON_QSBS: Dr Cash, Cr Investment + Gain/Loss."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("419742.41"),
            description="Non-QSBS sale",
            other_party="PARIAN GLOBAL US FUND",
        )

        ingestion_service._book_sale_non_qsbs(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced


class TestBookLiquidation:
    """Test LIQUIDATION transaction booking."""

    def test_books_liquidation(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """LIQUIDATION: Dr Cash, Cr Investment + Gain/Loss."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("50000.00"),
            description="Company liquidation",
            other_party="VENUE BUSINESS CORP",
        )

        ingestion_service._book_liquidation(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced


class TestBookBrokerFees:
    """Test BROKER_FEES transaction booking."""

    def test_books_broker_fees(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """BROKER_FEES: Dr Investment (capitalize), Cr Cash."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("-23500.00"),
            description="Secondary market fees",
            other_party="BGC EUROPEAN HOLDINGS",
        )

        ingestion_service._book_broker_fees(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced


class TestBookReturnOfFunds:
    """Test RETURN_OF_FUNDS transaction booking."""

    def test_books_return_of_funds(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """RETURN_OF_FUNDS: Dr Cash, Cr Investment."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("4945.47"),
            description="Refund received",
            other_party="ALFRED LAKE INC",
        )

        ingestion_service._book_return_of_funds(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced


class TestBookPublicMarket:
    """Test PUBLIC_MARKET transaction booking."""

    def test_books_tbill_purchase(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """T-Bill purchase: Dr T-Bills, Cr Cash."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("-3479931.88"),
            description="Treasury Bill Purchase",
            other_party="US TREASURIES",
        )

        ingestion_service._book_public_market(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced

    def test_books_crypto_sale(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """Crypto sale: Dr Cash, Cr Digital Assets."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("1985283.76"),
            description="Crypto sale",
            other_party="HYPERLIQUID",
        )

        ingestion_service._book_public_market(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced


class TestBookUnclassified:
    """Test UNCLASSIFIED transaction booking."""

    def test_books_unclassified_inflow(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """UNCLASSIFIED inflow: Dr Cash, Cr Suspense."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("1000.00"),
            description="Unknown deposit",
        )

        ingestion_service._book_unclassified(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced

    def test_books_unclassified_outflow(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """UNCLASSIFIED outflow: Dr Suspense, Cr Cash."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("-500.00"),
            description="Unknown payment",
        )

        ingestion_service._book_unclassified(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced


# =============================================================================
# Integration Tests
# =============================================================================


class TestProcessTransaction:
    """Test full transaction processing flow."""

    def test_process_creates_entity_and_account(
        self,
        ingestion_service: IngestionService,
        entity_repo: MockEntityRepository,
        account_repo: MockAccountRepository,
    ) -> None:
        """Processing transaction creates entity and cash account."""
        result = IngestionResult()

        parsed = create_parsed_transaction(
            amount=Decimal("100.00"),
            account_name="New Entity LLC - 5678",
            description="Interest income",
        )

        ingestion_service._process_transaction(parsed, None, result)

        # Check entity created
        entity = entity_repo.get_by_name("New Entity LLC")
        assert entity is not None
        assert entity.entity_type == EntityType.LLC

        # Check cash account created
        cash_account = account_repo.get_by_name("Cash - 5678", entity.id)
        assert cash_account is not None

    def test_process_uses_default_entity_name(
        self,
        ingestion_service: IngestionService,
        entity_repo: MockEntityRepository,
    ) -> None:
        """Uses default entity name when none can be parsed."""
        result = IngestionResult()

        parsed = create_parsed_transaction(
            amount=Decimal("100.00"),
            account_name="",
            account_number="1234",
            description="Interest income",
        )

        ingestion_service._process_transaction(parsed, "Default Entity", result)

        entity = entity_repo.get_by_name("Default Entity")
        assert entity is not None


class TestIdempotency:
    """Test that re-importing doesn't create duplicates."""

    def test_no_duplicate_entities(
        self,
        ingestion_service: IngestionService,
        entity_repo: MockEntityRepository,
    ) -> None:
        """Re-processing same entity name doesn't create duplicate."""
        result = IngestionResult()

        parsed1 = create_parsed_transaction(
            amount=Decimal("100.00"),
            account_name="Test Entity - 1234",
            description="Interest",
        )
        parsed2 = create_parsed_transaction(
            amount=Decimal("200.00"),
            account_name="Test Entity - 1234",
            description="More interest",
        )

        ingestion_service._process_transaction(parsed1, None, result)
        ingestion_service._process_transaction(parsed2, None, result)

        entities = list(entity_repo.list_all())
        test_entities = [e for e in entities if e.name == "Test Entity"]
        assert len(test_entities) == 1

    def test_no_duplicate_accounts(
        self,
        ingestion_service: IngestionService,
        entity_repo: MockEntityRepository,
        account_repo: MockAccountRepository,
    ) -> None:
        """Re-processing same account doesn't create duplicate."""
        entity = ingestion_service._get_or_create_entity("Test Entity")

        # Create same account twice
        account1 = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )
        account2 = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        assert account1.id == account2.id

        accounts = list(account_repo.list_by_entity(entity.id))
        cash_accounts = [a for a in accounts if a.name == "Cash - Main"]
        assert len(cash_accounts) == 1


class TestIngestionResult:
    """Test IngestionResult tracking."""

    def test_result_tracks_counts(
        self,
        ingestion_service: IngestionService,
        entity_repo: MockEntityRepository,
    ) -> None:
        """Result accurately tracks transaction counts."""
        result = IngestionResult()

        # Process multiple transactions
        for i in range(5):
            parsed = create_parsed_transaction(
                amount=Decimal("100.00"),
                account_name=f"Entity {i % 2} - 1234",  # 2 unique entities
                description="Interest income",
            )
            ingestion_service._process_transaction(parsed, None, result)

        assert result.transaction_count == 0  # Not incremented by _process_transaction
        assert TransactionType.INTEREST in result.type_breakdown
        assert result.type_breakdown[TransactionType.INTEREST] == 5


class TestTaxLotIntegration:
    """Test tax lot creation and disposal integration."""

    def test_purchase_creates_lot_sale_disposes(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
        tax_lot_repo: MockTaxLotRepository,
        lot_matching_service: MockLotMatchingService,
    ) -> None:
        """Full cycle: purchase creates lot, sale disposes it."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        # Purchase
        purchase = create_parsed_transaction(
            amount=Decimal("-100000.00"),
            description="Stock purchase",
            symbol="TEST",
            quantity=Decimal("1000"),
            price=Decimal("100.00"),
            txn_date=date(2025, 1, 1),
        )

        lots_created = ingestion_service._book_purchase_qsbs(
            purchase, entity, cash_account
        )
        assert lots_created == 1

        # Get the created lot and position info
        lots = list(tax_lot_repo._lots.values())
        assert len(lots) == 1
        lot = lots[0]
        assert lot.remaining_quantity.value == Decimal("1000")

        # Now sell half
        sale = create_parsed_transaction(
            amount=Decimal("75000.00"),  # Sold at gain
            description="Stock sale",
            symbol="TEST",
            quantity=Decimal("500"),
            txn_date=date(2026, 6, 1),
        )

        ingestion_service._book_sale_qsbs(sale, entity, cash_account)

        # Verify sale executed
        assert len(lot_matching_service.sales_executed) == 1


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_description(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """Handles empty description gracefully."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("100.00"),
            description="",
        )

        # Should not raise
        ingestion_service._book_interest(parsed, entity, cash_account)
        assert len(ledger_service.posted_transactions) == 1

    def test_zero_amount_treated_correctly(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """Zero amount transactions are balanced."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        parsed = create_parsed_transaction(
            amount=Decimal("0.00"),
            description="Zero transaction",
        )

        ingestion_service._book_unclassified(parsed, entity, cash_account)

        txn = ledger_service.posted_transactions[0]
        assert txn.is_balanced

    def test_all_transaction_types_book_balanced(
        self,
        ingestion_service: IngestionService,
        ledger_service: MockLedgerService,
    ) -> None:
        """Every transaction type produces balanced entries."""
        entity = ingestion_service._get_or_create_entity("Test Entity")
        cash_account = ingestion_service._get_or_create_account(
            entity, "Cash - Main", AccountType.ASSET, AccountSubType.CHECKING
        )

        # Test each booking method
        test_cases = [
            ("_book_interest", Decimal("100.00")),
            ("_book_expense", Decimal("-100.00")),
            ("_book_transfer", Decimal("100.00")),
            ("_book_trust_transfer", Decimal("-100.00")),
            ("_book_contribution_distribution", Decimal("-100.00")),
            ("_book_contribution_to_entity", Decimal("100.00")),
            ("_book_loan", Decimal("-100.00")),
            ("_book_loan_repayment", Decimal("100.00")),
            ("_book_liquidation", Decimal("100.00")),
            ("_book_broker_fees", Decimal("-100.00")),
            ("_book_return_of_funds", Decimal("100.00")),
            ("_book_unclassified", Decimal("100.00")),
        ]

        for method_name, amount in test_cases:
            ledger_service.posted_transactions.clear()

            parsed = create_parsed_transaction(
                amount=amount,
                description=f"Test {method_name}",
            )

            method = getattr(ingestion_service, method_name)
            method(parsed, entity, cash_account)

            assert len(ledger_service.posted_transactions) == 1, (
                f"{method_name} failed to post"
            )
            assert ledger_service.posted_transactions[0].is_balanced, (
                f"{method_name} unbalanced"
            )


# =============================================================================
# Real File Integration Tests
# =============================================================================


class TestRealFileIntegration:
    """Integration tests with real bank statement files.

    These tests ingest actual bank files and verify that the ingestion service
    correctly processes real file formats and creates appropriate entities,
    accounts, and transactions.
    """

    @pytest.mark.skipif(
        not Path(
            "/mnt/c/Users/Miller/Downloads/Transactions_CITI_01_28_2026_YTD.csv"
        ).exists(),
        reason="Real CITI file not available",
    )
    def test_ingest_real_citi_file(self) -> None:
        """Ingest real CITI CSV file and verify counts."""
        # Create in-memory repositories
        entity_repo = MockEntityRepository()
        account_repo = MockAccountRepository()
        security_repo = MockSecurityRepository()
        position_repo = MockPositionRepository()
        tax_lot_repo = MockTaxLotRepository()
        txn_repo = MockTransactionRepository()

        # Create services
        ledger_service = MockLedgerService(txn_repo, account_repo)
        lot_matching_service = MockLotMatchingService(tax_lot_repo)
        classifier = TransactionClassifier()

        # Create ingestion service
        service = IngestionService(
            entity_repo=entity_repo,
            account_repo=account_repo,
            security_repo=security_repo,
            position_repo=position_repo,
            tax_lot_repo=tax_lot_repo,
            ledger_service=ledger_service,
            lot_matching_service=lot_matching_service,
            transaction_classifier=classifier,
        )

        # Ingest file
        file_path = "/mnt/c/Users/Miller/Downloads/Transactions_CITI_01_28_2026_YTD.csv"
        result = service.ingest_file(file_path)

        # Print summary
        print(f"\n{'=' * 60}")
        print("CITI File Ingestion Summary")
        print(f"{'=' * 60}")
        print(f"File: {file_path}")
        print(f"Transactions ingested: {result.transaction_count}")
        print(f"Entities created: {result.entity_count}")
        print(f"Accounts created: {result.account_count}")
        print(f"Tax lots created: {result.tax_lot_count}")
        print(f"Errors: {len(result.errors)}")

        if result.type_breakdown:
            print("\nTransaction Type Breakdown:")
            for txn_type, count in sorted(
                result.type_breakdown.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {txn_type.value}: {count}")

        if result.errors:
            print("\nErrors encountered:")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")

        # Verify basic counts
        assert result.transaction_count > 0, "No transactions ingested"
        assert result.entity_count > 0, "No entities created"
        assert result.account_count > 0, "No accounts created"
        # CITI file should have ~144 transactions
        assert result.transaction_count >= 100, (
            f"Expected ~144 transactions, got {result.transaction_count}"
        )

    @pytest.mark.skipif(
        not Path(
            "/mnt/c/Users/Miller/Downloads/Transactions_UBS_01_28_2026_YTD.csv"
        ).exists(),
        reason="Real UBS file not available",
    )
    def test_ingest_real_ubs_file(self) -> None:
        """Ingest real UBS CSV file and verify counts."""
        # Create in-memory repositories
        entity_repo = MockEntityRepository()
        account_repo = MockAccountRepository()
        security_repo = MockSecurityRepository()
        position_repo = MockPositionRepository()
        tax_lot_repo = MockTaxLotRepository()
        txn_repo = MockTransactionRepository()

        # Create services
        ledger_service = MockLedgerService(txn_repo, account_repo)
        lot_matching_service = MockLotMatchingService(tax_lot_repo)
        classifier = TransactionClassifier()

        # Create ingestion service
        service = IngestionService(
            entity_repo=entity_repo,
            account_repo=account_repo,
            security_repo=security_repo,
            position_repo=position_repo,
            tax_lot_repo=tax_lot_repo,
            ledger_service=ledger_service,
            lot_matching_service=lot_matching_service,
            transaction_classifier=classifier,
        )

        # Ingest file
        file_path = "/mnt/c/Users/Miller/Downloads/Transactions_UBS_01_28_2026_YTD.csv"
        result = service.ingest_file(file_path)

        # Print summary
        print(f"\n{'=' * 60}")
        print("UBS File Ingestion Summary")
        print(f"{'=' * 60}")
        print(f"File: {file_path}")
        print(f"Transactions ingested: {result.transaction_count}")
        print(f"Entities created: {result.entity_count}")
        print(f"Accounts created: {result.account_count}")
        print(f"Tax lots created: {result.tax_lot_count}")
        print(f"Errors: {len(result.errors)}")

        if result.type_breakdown:
            print("\nTransaction Type Breakdown:")
            for txn_type, count in sorted(
                result.type_breakdown.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {txn_type.value}: {count}")

        if result.errors:
            print("\nErrors encountered:")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")

        # Verify basic counts
        assert result.transaction_count > 0, "No transactions ingested"
        assert result.entity_count > 0, "No entities created"
        assert result.account_count > 0, "No accounts created"
        # UBS file should have ~758 transactions
        assert result.transaction_count >= 500, (
            f"Expected ~758 transactions, got {result.transaction_count}"
        )

    @pytest.mark.skipif(
        not Path(
            "/mnt/c/Users/Miller/Downloads/Transactions_MS_01_28_2026_YTD.xlsx"
        ).exists(),
        reason="Real Morgan Stanley file not available",
    )
    def test_ingest_real_ms_file(self) -> None:
        """Ingest real Morgan Stanley Excel file and verify counts."""
        # Create in-memory repositories
        entity_repo = MockEntityRepository()
        account_repo = MockAccountRepository()
        security_repo = MockSecurityRepository()
        position_repo = MockPositionRepository()
        tax_lot_repo = MockTaxLotRepository()
        txn_repo = MockTransactionRepository()

        # Create services
        ledger_service = MockLedgerService(txn_repo, account_repo)
        lot_matching_service = MockLotMatchingService(tax_lot_repo)
        classifier = TransactionClassifier()

        # Create ingestion service
        service = IngestionService(
            entity_repo=entity_repo,
            account_repo=account_repo,
            security_repo=security_repo,
            position_repo=position_repo,
            tax_lot_repo=tax_lot_repo,
            ledger_service=ledger_service,
            lot_matching_service=lot_matching_service,
            transaction_classifier=classifier,
        )

        # Ingest file
        file_path = "/mnt/c/Users/Miller/Downloads/Transactions_MS_01_28_2026_YTD.xlsx"
        result = service.ingest_file(file_path)

        # Print summary
        print(f"\n{'=' * 60}")
        print("Morgan Stanley File Ingestion Summary")
        print(f"{'=' * 60}")
        print(f"File: {file_path}")
        print(f"Transactions ingested: {result.transaction_count}")
        print(f"Entities created: {result.entity_count}")
        print(f"Accounts created: {result.account_count}")
        print(f"Tax lots created: {result.tax_lot_count}")
        print(f"Errors: {len(result.errors)}")

        if result.type_breakdown:
            print("\nTransaction Type Breakdown:")
            for txn_type, count in sorted(
                result.type_breakdown.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {txn_type.value}: {count}")

        if result.errors:
            print("\nErrors encountered:")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")

        # Verify basic counts
        assert result.transaction_count > 0, "No transactions ingested"
        assert result.entity_count > 0, "No entities created"
        assert result.account_count > 0, "No accounts created"
        # Morgan Stanley file should have ~216 transactions
        assert result.transaction_count >= 150, (
            f"Expected ~216 transactions, got {result.transaction_count}"
        )
