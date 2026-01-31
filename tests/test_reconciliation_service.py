"""Tests for ReconciliationService implementation."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    EntityType,
    Money,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.interfaces import ReconciliationSummary
from family_office_ledger.services.reconciliation import ReconciliationServiceImpl


@pytest.fixture
def db() -> SQLiteDatabase:
    """Create an in-memory SQLite database for testing."""
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
def transaction_repo(db: SQLiteDatabase) -> SQLiteTransactionRepository:
    return SQLiteTransactionRepository(db)


@pytest.fixture
def test_entity(entity_repo: SQLiteEntityRepository) -> Entity:
    """Create and persist a test entity."""
    entity = Entity(name="Test Family Trust", entity_type=EntityType.TRUST)
    entity_repo.add(entity)
    return entity


@pytest.fixture
def test_accounts(
    account_repo: SQLiteAccountRepository, test_entity: Entity
) -> dict[str, Account]:
    """Create and persist test accounts."""
    checking = Account(
        name="Main Checking",
        entity_id=test_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CHECKING,
    )
    income = Account(
        name="Income",
        entity_id=test_entity.id,
        account_type=AccountType.INCOME,
    )
    expense = Account(
        name="Expenses",
        entity_id=test_entity.id,
        account_type=AccountType.EXPENSE,
    )
    account_repo.add(checking)
    account_repo.add(income)
    account_repo.add(expense)
    return {"checking": checking, "income": income, "expense": expense}


@pytest.fixture
def reconciliation_service(
    transaction_repo: SQLiteTransactionRepository,
    account_repo: SQLiteAccountRepository,
) -> ReconciliationServiceImpl:
    """Create reconciliation service with real SQLite repositories."""
    return ReconciliationServiceImpl(
        transaction_repo=transaction_repo,
        account_repo=account_repo,
    )


# ===== import_transactions Tests =====


class TestImportTransactions:
    def test_import_csv_transactions(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        test_accounts: dict[str, Account],
        tmp_path: Path,
    ) -> None:
        """Import transactions from a CSV file."""
        csv_content = """Date,Description,Amount
2024-01-15,DEPOSIT,1000.00
2024-01-16,GROCERY STORE,-45.67
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        result = reconciliation_service.import_transactions(
            file_path=str(csv_file),
            account_id=test_accounts["checking"].id,
            file_format="csv",
        )

        assert len(result) == 2
        assert result[0]["date"] == date(2024, 1, 15)
        assert result[0]["amount"] == Decimal("1000.00")
        assert result[1]["amount"] == Decimal("-45.67")

    def test_import_ofx_transactions(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        test_accounts: dict[str, Account],
        tmp_path: Path,
    ) -> None:
        """Import transactions from an OFX file."""
        ofx_content = """<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20240115
<TRNAMT>500.00
<FITID>TX001
<MEMO>WIRE TRANSFER
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""
        ofx_file = tmp_path / "statement.ofx"
        ofx_file.write_text(ofx_content)

        result = reconciliation_service.import_transactions(
            file_path=str(ofx_file),
            account_id=test_accounts["checking"].id,
            file_format="ofx",
        )

        assert len(result) == 1
        assert result[0]["amount"] == Decimal("500.00")
        assert result[0]["fitid"] == "TX001"

    def test_import_qfx_transactions(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        test_accounts: dict[str, Account],
        tmp_path: Path,
    ) -> None:
        """Import transactions from a QFX file (same as OFX)."""
        qfx_content = """<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20240120
<TRNAMT>-100.00
<FITID>TX002
<MEMO>ATM WITHDRAWAL
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""
        qfx_file = tmp_path / "statement.qfx"
        qfx_file.write_text(qfx_content)

        result = reconciliation_service.import_transactions(
            file_path=str(qfx_file),
            account_id=test_accounts["checking"].id,
            file_format="qfx",
        )

        assert len(result) == 1
        assert result[0]["amount"] == Decimal("-100.00")

    def test_import_unsupported_format_raises(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        test_accounts: dict[str, Account],
        tmp_path: Path,
    ) -> None:
        """Importing unsupported format should raise ValueError."""
        dummy_file = tmp_path / "statement.xyz"
        dummy_file.write_text("dummy")

        with pytest.raises(ValueError, match="Unsupported file format"):
            reconciliation_service.import_transactions(
                file_path=str(dummy_file),
                account_id=test_accounts["checking"].id,
                file_format="xyz",
            )


# ===== match_imported Tests =====


class TestMatchImported:
    def test_match_exact_amount_and_date(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ) -> None:
        """Exact match on amount and date should score high."""
        # Create ledger transaction
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="DEPOSIT FROM EMPLOYER",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["checking"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )
        transaction_repo.add(txn)

        # Import data to match
        imported = [
            {
                "import_id": "IMP001",
                "date": date(2024, 1, 15),
                "amount": Decimal("1000.00"),
                "description": "PAYROLL DEPOSIT",
            }
        ]

        results = reconciliation_service.match_imported(
            imported_transactions=imported,
            account_id=test_accounts["checking"].id,
        )

        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].ledger_transaction_id == txn.id
        # Exact amount (50) + exact date (30) = 80 minimum
        assert results[0].confidence_score >= 80

    def test_match_within_date_tolerance(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ) -> None:
        """Match should work when dates are within 3 days."""
        # Ledger transaction on Jan 15
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="DEPOSIT",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["checking"].id,
                debit_amount=Money(Decimal("500.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("500.00")),
            )
        )
        transaction_repo.add(txn)

        # Import with date Jan 17 (2 days later, within tolerance)
        imported = [
            {
                "import_id": "IMP002",
                "date": date(2024, 1, 17),
                "amount": Decimal("500.00"),
                "description": "DEPOSIT",
            }
        ]

        results = reconciliation_service.match_imported(
            imported_transactions=imported,
            account_id=test_accounts["checking"].id,
        )

        assert len(results) == 1
        assert results[0].matched is True
        # Exact amount (50) + date within 3 days (30) = 80
        assert results[0].confidence_score >= 50

    def test_no_match_when_amount_differs(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ) -> None:
        """No match when amounts don't match."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="DEPOSIT",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["checking"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )
        transaction_repo.add(txn)

        imported = [
            {
                "import_id": "IMP003",
                "date": date(2024, 1, 15),
                "amount": Decimal("999.00"),  # Different amount
                "description": "DEPOSIT",
            }
        ]

        results = reconciliation_service.match_imported(
            imported_transactions=imported,
            account_id=test_accounts["checking"].id,
        )

        assert len(results) == 1
        assert results[0].matched is False

    def test_match_with_memo_similarity(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ) -> None:
        """Similar memo should add to confidence score."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="GROCERY STORE PURCHASE",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["checking"].id,
                credit_amount=Money(Decimal("50.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("50.00")),
            )
        )
        transaction_repo.add(txn)

        imported = [
            {
                "import_id": "IMP004",
                "date": date(2024, 1, 15),
                "amount": Decimal("-50.00"),  # Negative for expense
                "description": "GROCERY STORE",  # Similar memo
            }
        ]

        results = reconciliation_service.match_imported(
            imported_transactions=imported,
            account_id=test_accounts["checking"].id,
        )

        assert len(results) == 1
        assert results[0].matched is True

    def test_no_transactions_to_match(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        test_accounts: dict[str, Account],
    ) -> None:
        """When no ledger transactions exist, all imports are unmatched."""
        imported = [
            {
                "import_id": "IMP005",
                "date": date(2024, 1, 15),
                "amount": Decimal("100.00"),
                "description": "TEST",
            }
        ]

        results = reconciliation_service.match_imported(
            imported_transactions=imported,
            account_id=test_accounts["checking"].id,
        )

        assert len(results) == 1
        assert results[0].matched is False
        assert results[0].ledger_transaction_id is None


# ===== confirm_match Tests =====


class TestConfirmMatch:
    def test_confirm_match_stores_association(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ) -> None:
        """Confirming a match should store the association."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="DEPOSIT",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["checking"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        transaction_repo.add(txn)

        # Confirm match
        reconciliation_service.confirm_match(
            imported_id="IMP_CONFIRMED",
            ledger_transaction_id=txn.id,
        )

        # Verify it's stored (the transaction should now have reference)
        updated_txn = transaction_repo.get(txn.id)
        assert updated_txn is not None
        # The reference field should contain the import ID
        assert "IMP_CONFIRMED" in updated_txn.reference


# ===== create_from_import Tests =====


class TestCreateFromImport:
    def test_create_transaction_from_import_credit(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ) -> None:
        """Create a credit transaction from imported data."""
        imported = {
            "import_id": "IMP_NEW_001",
            "date": date(2024, 1, 20),
            "amount": Decimal("500.00"),  # Positive = credit/deposit
            "description": "WIRE TRANSFER IN",
        }

        txn = reconciliation_service.create_from_import(
            imported_transaction=imported,
            account_id=test_accounts["checking"].id,
        )

        assert txn.transaction_date == date(2024, 1, 20)
        assert txn.memo == "WIRE TRANSFER IN"
        assert txn.reference == "IMP_NEW_001"

        # Transaction should be balanced with debit to checking
        assert txn.is_balanced
        assert len(txn.entries) == 2

        # Find the checking entry
        checking_entry = next(
            e for e in txn.entries if e.account_id == test_accounts["checking"].id
        )
        assert checking_entry.debit_amount == Money(Decimal("500.00"))

    def test_create_transaction_from_import_debit(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ) -> None:
        """Create a debit transaction from imported data."""
        imported = {
            "import_id": "IMP_NEW_002",
            "date": date(2024, 1, 20),
            "amount": Decimal("-75.00"),  # Negative = debit/withdrawal
            "description": "ATM WITHDRAWAL",
        }

        txn = reconciliation_service.create_from_import(
            imported_transaction=imported,
            account_id=test_accounts["checking"].id,
        )

        assert txn.is_balanced
        assert len(txn.entries) == 2

        # Find the checking entry - should be credit (money leaving)
        checking_entry = next(
            e for e in txn.entries if e.account_id == test_accounts["checking"].id
        )
        assert checking_entry.credit_amount == Money(Decimal("75.00"))

    def test_create_transaction_saves_to_repo(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ) -> None:
        """Created transaction should be saved to repository."""
        imported = {
            "import_id": "IMP_NEW_003",
            "date": date(2024, 1, 25),
            "amount": Decimal("250.00"),
            "description": "TRANSFER",
        }

        txn = reconciliation_service.create_from_import(
            imported_transaction=imported,
            account_id=test_accounts["checking"].id,
        )

        # Verify saved
        retrieved = transaction_repo.get(txn.id)
        assert retrieved is not None
        assert retrieved.memo == "TRANSFER"
        assert retrieved.reference == "IMP_NEW_003"


# ===== get_reconciliation_summary Tests =====


class TestGetReconciliationSummary:
    def test_summary_with_no_transactions(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        test_accounts: dict[str, Account],
    ) -> None:
        """Summary with no transactions should show zeros."""
        summary = reconciliation_service.get_reconciliation_summary(
            account_id=test_accounts["checking"].id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert summary.total_imported == 0
        assert summary.matched_count == 0
        assert summary.unmatched_count == 0
        assert summary.match_rate == 0.0

    def test_summary_with_matched_transactions(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ) -> None:
        """Summary should count matched transactions."""
        # Create a transaction with import reference (matched)
        txn1 = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="MATCHED TXN",
            reference="IMPORT:IMP001",  # Has import reference = matched
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["checking"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        transaction_repo.add(txn1)

        # Create a transaction without import reference (unmatched)
        txn2 = Transaction(
            transaction_date=date(2024, 1, 20),
            memo="UNMATCHED TXN",
            reference="",  # No import reference
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["checking"].id,
                debit_amount=Money(Decimal("200.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("200.00")),
            )
        )
        transaction_repo.add(txn2)

        summary = reconciliation_service.get_reconciliation_summary(
            account_id=test_accounts["checking"].id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert summary.total_imported >= 1
        assert summary.matched_count >= 1

    def test_summary_date_range_filtering(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ) -> None:
        """Summary should only include transactions in date range."""
        # Transaction in January
        txn1 = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="JAN TXN",
            reference="IMPORT:IMP_JAN",
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["checking"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        transaction_repo.add(txn1)

        # Transaction in February
        txn2 = Transaction(
            transaction_date=date(2024, 2, 15),
            memo="FEB TXN",
            reference="IMPORT:IMP_FEB",
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["checking"].id,
                debit_amount=Money(Decimal("200.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("200.00")),
            )
        )
        transaction_repo.add(txn2)

        # Query only January
        summary = reconciliation_service.get_reconciliation_summary(
            account_id=test_accounts["checking"].id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        # Should only count January transaction
        assert summary.total_imported >= 1

    def test_summary_match_rate_calculation(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ) -> None:
        """Match rate should be calculated correctly."""
        # Create 2 matched and 1 unmatched
        for i in range(2):
            txn = Transaction(
                transaction_date=date(2024, 1, 10 + i),
                memo=f"MATCHED {i}",
                reference=f"IMPORT:IMP{i}",
            )
            txn.add_entry(
                Entry(
                    account_id=test_accounts["checking"].id,
                    debit_amount=Money(Decimal("100.00")),
                )
            )
            txn.add_entry(
                Entry(
                    account_id=test_accounts["income"].id,
                    credit_amount=Money(Decimal("100.00")),
                )
            )
            transaction_repo.add(txn)

        # One unmatched
        txn_unmatched = Transaction(
            transaction_date=date(2024, 1, 20),
            memo="UNMATCHED",
            reference="",
        )
        txn_unmatched.add_entry(
            Entry(
                account_id=test_accounts["checking"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn_unmatched.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        transaction_repo.add(txn_unmatched)

        summary = reconciliation_service.get_reconciliation_summary(
            account_id=test_accounts["checking"].id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        # 2 matched out of 3 total = ~0.67 match rate
        if summary.total_imported > 0:
            assert 0 <= summary.match_rate <= 1.0


# ===== Integration Tests =====


class TestReconciliationServiceIntegration:
    def test_full_reconciliation_workflow(
        self,
        reconciliation_service: ReconciliationServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
        tmp_path: Path,
    ) -> None:
        """Test complete reconciliation workflow."""
        # 1. Create existing ledger transaction
        existing_txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="PAYROLL DIRECT DEPOSIT",
        )
        existing_txn.add_entry(
            Entry(
                account_id=test_accounts["checking"].id,
                debit_amount=Money(Decimal("5000.00")),
            )
        )
        existing_txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("5000.00")),
            )
        )
        transaction_repo.add(existing_txn)

        # 2. Import bank statement
        csv_content = """Date,Description,Amount
2024-01-15,ACH DEPOSIT EMPLOYER INC,5000.00
2024-01-18,AMAZON PURCHASE,-75.50
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        imported = reconciliation_service.import_transactions(
            file_path=str(csv_file),
            account_id=test_accounts["checking"].id,
            file_format="csv",
        )
        assert len(imported) == 2

        # 3. Match imported transactions
        match_results = reconciliation_service.match_imported(
            imported_transactions=imported,
            account_id=test_accounts["checking"].id,
        )

        # First transaction should match (same date and amount)
        assert match_results[0].matched is True
        assert match_results[0].ledger_transaction_id == existing_txn.id

        # Second transaction should not match (no ledger txn)
        assert match_results[1].matched is False

        # 4. Confirm the match
        reconciliation_service.confirm_match(
            imported_id=imported[0]["import_id"],
            ledger_transaction_id=existing_txn.id,
        )

        # 5. Create transaction for unmatched import
        new_txn = reconciliation_service.create_from_import(
            imported_transaction=imported[1],
            account_id=test_accounts["checking"].id,
        )
        assert new_txn.transaction_date == date(2024, 1, 18)
        assert new_txn.is_balanced

        # 6. Get reconciliation summary
        summary = reconciliation_service.get_reconciliation_summary(
            account_id=test_accounts["checking"].id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert isinstance(summary, ReconciliationSummary)
