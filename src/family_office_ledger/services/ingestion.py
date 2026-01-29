"""Ingestion service for importing bank transactions and booking journal entries.

This service:
- Parses bank files using BankParserFactory
- Auto-creates entities from account names (LLC, Trust, Holdings patterns)
- Auto-creates accounts under entities
- Classifies transactions using TransactionClassifier
- Books balanced journal entries per TransactionType
- Creates/disposes tax lots for investment transactions
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from family_office_ledger.domain.entities import Account, Entity, Position, Security
from family_office_ledger.domain.transactions import Entry, TaxLot, Transaction
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    AcquisitionType,
    AssetClass,
    EntityType,
    LotSelection,
    Money,
    Quantity,
    TransactionType,
)
from family_office_ledger.parsers.bank_parsers import (
    BankParserFactory,
    ParsedTransaction,
)
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    EntityRepository,
    PositionRepository,
    SecurityRepository,
    TaxLotRepository,
)
from family_office_ledger.services.interfaces import LedgerService, LotMatchingService
from family_office_ledger.services.transaction_classifier import TransactionClassifier


@dataclass
class IngestionResult:
    """Result summary from an ingestion operation."""

    transaction_count: int = 0
    entity_count: int = 0
    account_count: int = 0
    tax_lot_count: int = 0
    type_breakdown: dict[TransactionType, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class IngestionError(Exception):
    """Raised when ingestion encounters an error."""

    pass


# Entity detection patterns - keywords to EntityType mapping
ENTITY_PATTERNS: dict[str, EntityType] = {
    "LLC": EntityType.LLC,
    "L.L.C.": EntityType.LLC,
    "HOLDINGS": EntityType.HOLDING_CO,
    "INVESTMENTS": EntityType.HOLDING_CO,
    "TRUST": EntityType.TRUST,
    "PARTNERSHIP": EntityType.PARTNERSHIP,
    "LP": EntityType.PARTNERSHIP,
}

# Standard account names used across all entities
SYSTEM_ENTITY_NAME = "System"
STANDARD_ACCOUNTS: dict[str, tuple[AccountType, AccountSubType]] = {
    "Interest Income": (AccountType.INCOME, AccountSubType.OTHER),
    "Legal & Professional Fees": (AccountType.EXPENSE, AccountSubType.OTHER),
    "Member's Capital": (AccountType.EQUITY, AccountSubType.OTHER),
    "Due From Trust": (AccountType.ASSET, AccountSubType.OTHER),
    "Due From/To Affiliates": (AccountType.ASSET, AccountSubType.OTHER),
    "Notes Receivable": (AccountType.ASSET, AccountSubType.LOAN),
    "Investment - Fund": (AccountType.ASSET, AccountSubType.PRIVATE_EQUITY),
    "Investment - QSBS Stock": (AccountType.ASSET, AccountSubType.VENTURE_CAPITAL),
    "Investment - Non-QSBS": (AccountType.ASSET, AccountSubType.PRIVATE_EQUITY),
    "Investment - OZ Fund": (AccountType.ASSET, AccountSubType.PRIVATE_EQUITY),
    "Investment - Portfolio Co": (AccountType.ASSET, AccountSubType.PRIVATE_EQUITY),
    "Gain on Sale - QSBS": (AccountType.INCOME, AccountSubType.OTHER),
    "Gain/Loss on Sale": (AccountType.INCOME, AccountSubType.OTHER),
    "Gain/Loss on Liquidation": (AccountType.INCOME, AccountSubType.OTHER),
    "Gain/Loss - Digital Assets": (AccountType.INCOME, AccountSubType.OTHER),
    "Marketable Securities - T-Bills": (AccountType.ASSET, AccountSubType.BROKERAGE),
    "Digital Assets - Crypto": (AccountType.ASSET, AccountSubType.CRYPTO),
    "Suspense / Unclassified": (AccountType.LIABILITY, AccountSubType.OTHER),
    "Escrow Receivable": (AccountType.ASSET, AccountSubType.OTHER),
}


class IngestionService:
    """Service for ingesting bank transactions and booking journal entries.

    This is the main entry point for importing bank statements. It handles:
    - File parsing via BankParserFactory
    - Entity and account auto-creation
    - Transaction classification
    - Journal entry booking with double-entry accounting
    - Tax lot creation and disposal for investment transactions
    """

    def __init__(
        self,
        entity_repo: EntityRepository,
        account_repo: AccountRepository,
        security_repo: SecurityRepository,
        position_repo: PositionRepository,
        tax_lot_repo: TaxLotRepository,
        ledger_service: LedgerService,
        lot_matching_service: LotMatchingService,
        transaction_classifier: TransactionClassifier,
    ) -> None:
        """Initialize the ingestion service.

        Args:
            entity_repo: Repository for Entity operations
            account_repo: Repository for Account operations
            security_repo: Repository for Security operations
            position_repo: Repository for Position operations
            tax_lot_repo: Repository for TaxLot operations
            ledger_service: Service for posting journal entries
            lot_matching_service: Service for tax lot matching and disposal
            transaction_classifier: Classifier for determining transaction types
        """
        self._entity_repo = entity_repo
        self._account_repo = account_repo
        self._security_repo = security_repo
        self._position_repo = position_repo
        self._tax_lot_repo = tax_lot_repo
        self._ledger_service = ledger_service
        self._lot_matching_service = lot_matching_service
        self._classifier = transaction_classifier

        # Cache for entities and accounts to avoid repeated lookups
        self._entity_cache: dict[str, Entity] = {}
        self._account_cache: dict[tuple[UUID, str], Account] = {}

    def ingest_file(
        self,
        file_path: str,
        default_entity_name: str | None = None,
    ) -> IngestionResult:
        """Ingest a bank statement file and book journal entries.

        Main entry point for ingestion. Parses the file, classifies each
        transaction, and books balanced journal entries.

        Args:
            file_path: Path to the bank statement file
            default_entity_name: Default entity name if none can be detected

        Returns:
            IngestionResult with summary statistics

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If no parser can handle the file
        """
        result = IngestionResult()

        # Clear caches for fresh ingestion
        self._entity_cache.clear()
        self._account_cache.clear()

        # Parse the file
        parsed_transactions = BankParserFactory.parse(file_path)

        # Ensure system entity exists for standard accounts
        system_entity = self._get_or_create_entity(SYSTEM_ENTITY_NAME)

        # Track created entities/accounts for result
        initial_entities = set(e.name for e in self._entity_repo.list_all())
        initial_accounts_count = self._count_all_accounts()

        # Process each transaction
        for parsed_txn in parsed_transactions:
            try:
                self._process_transaction(
                    parsed_txn,
                    default_entity_name,
                    result,
                )
                result.transaction_count += 1
            except Exception as e:
                result.errors.append(
                    f"Error processing transaction {parsed_txn.import_id}: {e}"
                )

        # Calculate created counts
        final_entities = set(e.name for e in self._entity_repo.list_all())
        result.entity_count = len(final_entities - initial_entities)
        result.account_count = self._count_all_accounts() - initial_accounts_count

        return result

    def _count_all_accounts(self) -> int:
        """Count total accounts across all entities."""
        count = 0
        for entity in self._entity_repo.list_all():
            count += sum(1 for _ in self._account_repo.list_by_entity(entity.id))
        return count

    def _process_transaction(
        self,
        parsed_txn: ParsedTransaction,
        default_entity_name: str | None,
        result: IngestionResult,
    ) -> None:
        """Process a single parsed transaction.

        Args:
            parsed_txn: The parsed transaction to process
            default_entity_name: Default entity name if none detected
            result: IngestionResult to update
        """
        # Parse entity and account from account_name
        entity_name, account_suffix = self._parse_account_name(
            parsed_txn.account_name,
            parsed_txn.account_number,
        )
        if not entity_name:
            entity_name = default_entity_name or "Unknown Entity"

        # Get or create entity
        entity = self._get_or_create_entity(entity_name)

        # Get or create cash account for this entity
        cash_account_name = f"Cash - {account_suffix}"
        cash_account = self._get_or_create_account(
            entity,
            cash_account_name,
            AccountType.ASSET,
            AccountSubType.CHECKING,
        )

        # Classify the transaction
        txn_type = self._classifier.classify(parsed_txn)

        # Update type breakdown
        result.type_breakdown[txn_type] = result.type_breakdown.get(txn_type, 0) + 1

        # Book the journal entry based on transaction type
        tax_lots_created = self._book_transaction(
            parsed_txn,
            txn_type,
            entity,
            cash_account,
        )
        result.tax_lot_count += tax_lots_created

    def _parse_account_name(
        self,
        account_name: str,
        account_number: str,
    ) -> tuple[str, str]:
        """Parse account name to extract entity name and account suffix.

        Handles formats:
        - "ENTROPY MANAGEMENT GROUP - 7111" → ("ENTROPY MANAGEMENT GROUP", "7111")
        - "Kaneda - 8231 - 8231" → ("Kaneda", "8231")
        - "Atlantic Blue" → ("Atlantic Blue", "Main")

        Args:
            account_name: Full account name from bank
            account_number: Account number from bank

        Returns:
            Tuple of (entity_name, account_suffix)
        """
        if not account_name:
            return "", account_number or "Main"

        # Split on " - " to separate entity from account
        parts = account_name.split(" - ")

        if len(parts) >= 2:
            entity_name = parts[0].strip()
            # Use the last part as account suffix, or account_number if available
            account_suffix = parts[-1].strip() or account_number or "Main"
            return entity_name, account_suffix

        # No separator - use whole name as entity, account_number as suffix
        return account_name.strip(), account_number or "Main"

    def _detect_entity_type(self, name: str) -> EntityType:
        """Detect entity type from name using keyword patterns.

        Args:
            name: Entity name to analyze

        Returns:
            Detected EntityType, defaults to INDIVIDUAL
        """
        name_upper = name.upper()
        for pattern, entity_type in ENTITY_PATTERNS.items():
            if pattern.upper() in name_upper:
                return entity_type
        return EntityType.INDIVIDUAL

    def _get_or_create_entity(self, name: str) -> Entity:
        """Get existing entity by name or create new one.

        Uses cache to avoid repeated repository lookups.

        Args:
            name: Entity name

        Returns:
            Entity instance
        """
        # Check cache first
        if name in self._entity_cache:
            return self._entity_cache[name]

        # Try to find existing
        existing = self._entity_repo.get_by_name(name)
        if existing:
            self._entity_cache[name] = existing
            return existing

        # Create new entity
        entity_type = self._detect_entity_type(name)
        entity = Entity(name=name, entity_type=entity_type)
        self._entity_repo.add(entity)
        self._entity_cache[name] = entity
        return entity

    def _get_or_create_account(
        self,
        entity: Entity,
        name: str,
        account_type: AccountType,
        sub_type: AccountSubType,
    ) -> Account:
        """Get existing account or create new one.

        Uses cache to avoid repeated repository lookups.

        Args:
            entity: Owning entity
            name: Account name
            account_type: Type of account
            sub_type: Sub-type of account

        Returns:
            Account instance
        """
        cache_key = (entity.id, name)

        # Check cache first
        if cache_key in self._account_cache:
            return self._account_cache[cache_key]

        # Try to find existing
        existing = self._account_repo.get_by_name(name, entity.id)
        if existing:
            self._account_cache[cache_key] = existing
            return existing

        # Create new account
        account = Account(
            name=name,
            entity_id=entity.id,
            account_type=account_type,
            sub_type=sub_type,
        )
        self._account_repo.add(account)
        self._account_cache[cache_key] = account
        return account

    def _get_standard_account(self, name: str, entity: Entity | None = None) -> Account:
        """Get a standard account, creating if necessary.

        Standard accounts are created under the System entity by default,
        or under the specified entity.

        Args:
            name: Standard account name (must be in STANDARD_ACCOUNTS)
            entity: Optional entity to create under (defaults to System)

        Returns:
            Account instance

        Raises:
            ValueError: If account name is not a recognized standard account
        """
        if name not in STANDARD_ACCOUNTS:
            raise ValueError(f"Unknown standard account: {name}")

        if entity is None:
            entity = self._get_or_create_entity(SYSTEM_ENTITY_NAME)

        account_type, sub_type = STANDARD_ACCOUNTS[name]
        return self._get_or_create_account(entity, name, account_type, sub_type)

    def _get_or_create_security(
        self,
        symbol: str | None,
        cusip: str | None,
        name: str | None = None,
        is_qsbs: bool = False,
    ) -> Security:
        """Get existing security or create new one.

        Args:
            symbol: Security symbol
            cusip: CUSIP identifier
            name: Security name (defaults to symbol)
            is_qsbs: Whether security is QSBS eligible

        Returns:
            Security instance
        """
        # Try to find by symbol first
        if symbol:
            existing = self._security_repo.get_by_symbol(symbol)
            if existing:
                return existing

        # Try to find by CUSIP
        if cusip:
            existing = self._security_repo.get_by_cusip(cusip)
            if existing:
                return existing

        # Create new security
        security = Security(
            symbol=symbol or cusip or "UNKNOWN",
            name=name or symbol or cusip or "Unknown Security",
            cusip=cusip,
            is_qsbs_eligible=is_qsbs,
        )
        self._security_repo.add(security)
        return security

    def _get_or_create_position(
        self,
        account: Account,
        security: Security,
    ) -> Position:
        """Get existing position or create new one.

        Args:
            account: Account holding the position
            security: Security being held

        Returns:
            Position instance
        """
        existing = self._position_repo.get_by_account_and_security(
            account.id, security.id
        )
        if existing:
            return existing

        position = Position(
            account_id=account.id,
            security_id=security.id,
        )
        self._position_repo.add(position)
        return position

    def _book_transaction(
        self,
        parsed_txn: ParsedTransaction,
        txn_type: TransactionType,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book a journal entry based on transaction type.

        Args:
            parsed_txn: The parsed transaction
            txn_type: Classified transaction type
            entity: Owning entity
            cash_account: Cash account for the entity

        Returns:
            Number of tax lots created
        """
        # Route to appropriate booking method
        booking_methods = {
            TransactionType.INTEREST: self._book_interest,
            TransactionType.EXPENSE: self._book_expense,
            TransactionType.TRANSFER: self._book_transfer,
            TransactionType.TRUST_TRANSFER: self._book_trust_transfer,
            TransactionType.CONTRIBUTION_DISTRIBUTION: self._book_contribution_distribution,
            TransactionType.CONTRIBUTION_TO_ENTITY: self._book_contribution_to_entity,
            TransactionType.LOAN: self._book_loan,
            TransactionType.LOAN_REPAYMENT: self._book_loan_repayment,
            TransactionType.PURCHASE_QSBS: self._book_purchase_qsbs,
            TransactionType.PURCHASE_NON_QSBS: self._book_purchase_non_qsbs,
            TransactionType.PURCHASE_OZ_FUND: self._book_purchase_oz_fund,
            TransactionType.SALE_QSBS: self._book_sale_qsbs,
            TransactionType.SALE_NON_QSBS: self._book_sale_non_qsbs,
            TransactionType.LIQUIDATION: self._book_liquidation,
            TransactionType.BROKER_FEES: self._book_broker_fees,
            TransactionType.RETURN_OF_FUNDS: self._book_return_of_funds,
            TransactionType.PUBLIC_MARKET: self._book_public_market,
            TransactionType.UNCLASSIFIED: self._book_unclassified,
        }

        method = booking_methods.get(txn_type, self._book_unclassified)
        return method(parsed_txn, entity, cash_account)

    def _create_and_post_transaction(
        self,
        parsed_txn: ParsedTransaction,
        entries: list[Entry],
        memo_prefix: str,
    ) -> None:
        """Create and post a transaction with the given entries.

        Args:
            parsed_txn: Source parsed transaction
            entries: List of journal entries
            memo_prefix: Prefix for transaction memo
        """
        memo = f"{memo_prefix}: {parsed_txn.description}"
        if parsed_txn.other_party:
            memo += f" ({parsed_txn.other_party})"

        txn = Transaction(
            transaction_date=parsed_txn.date,
            entries=entries,
            memo=memo,
            reference=parsed_txn.import_id,
        )

        self._ledger_service.post_transaction(txn)

    def _book_interest(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book INTEREST transaction: Dr Cash, Cr Interest Income."""
        amount = Money(abs(parsed_txn.amount))
        income_account = self._get_standard_account("Interest Income", entity)

        entries = [
            Entry(account_id=cash_account.id, debit_amount=amount),
            Entry(account_id=income_account.id, credit_amount=amount),
        ]

        self._create_and_post_transaction(parsed_txn, entries, "Interest income")
        return 0

    def _book_expense(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book EXPENSE transaction: Dr Expense, Cr Cash."""
        amount = Money(abs(parsed_txn.amount))
        expense_account = self._get_standard_account(
            "Legal & Professional Fees", entity
        )

        entries = [
            Entry(account_id=expense_account.id, debit_amount=amount),
            Entry(account_id=cash_account.id, credit_amount=amount),
        ]

        self._create_and_post_transaction(parsed_txn, entries, "Expense")
        return 0

    def _book_transfer(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book TRANSFER transaction: Dr/Cr between cash accounts."""
        amount = Money(abs(parsed_txn.amount))

        # For transfers, we may have a destination entity
        # Use Due From/To Affiliates as the offset
        affiliate_account = self._get_standard_account("Due From/To Affiliates", entity)

        if parsed_txn.amount > 0:
            # Cash inflow - Dr Cash, Cr Due From/To Affiliates
            entries = [
                Entry(account_id=cash_account.id, debit_amount=amount),
                Entry(account_id=affiliate_account.id, credit_amount=amount),
            ]
        else:
            # Cash outflow - Dr Due From/To Affiliates, Cr Cash
            entries = [
                Entry(account_id=affiliate_account.id, debit_amount=amount),
                Entry(account_id=cash_account.id, credit_amount=amount),
            ]

        self._create_and_post_transaction(parsed_txn, entries, "Transfer")
        return 0

    def _book_trust_transfer(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book TRUST_TRANSFER: Dr Due From Trust, Cr Cash (or reverse)."""
        amount = Money(abs(parsed_txn.amount))
        trust_account = self._get_standard_account("Due From Trust", entity)

        if parsed_txn.amount > 0:
            # Cash inflow from trust - Dr Cash, Cr Due From Trust
            entries = [
                Entry(account_id=cash_account.id, debit_amount=amount),
                Entry(account_id=trust_account.id, credit_amount=amount),
            ]
        else:
            # Cash outflow to trust - Dr Due From Trust, Cr Cash
            entries = [
                Entry(account_id=trust_account.id, debit_amount=amount),
                Entry(account_id=cash_account.id, credit_amount=amount),
            ]

        self._create_and_post_transaction(parsed_txn, entries, "Trust transfer")
        return 0

    def _book_contribution_distribution(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book CONTRIBUTION_DISTRIBUTION: Fund capital call or distribution."""
        amount = Money(abs(parsed_txn.amount))
        fund_account = self._get_standard_account("Investment - Fund", entity)

        if parsed_txn.amount < 0:
            # Capital call - Dr Investment - Fund, Cr Cash
            entries = [
                Entry(account_id=fund_account.id, debit_amount=amount),
                Entry(account_id=cash_account.id, credit_amount=amount),
            ]
        else:
            # Distribution - Dr Cash, Cr Investment - Fund
            entries = [
                Entry(account_id=cash_account.id, debit_amount=amount),
                Entry(account_id=fund_account.id, credit_amount=amount),
            ]

        self._create_and_post_transaction(
            parsed_txn, entries, "Contribution/Distribution"
        )
        return 0

    def _book_contribution_to_entity(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book CONTRIBUTION_TO_ENTITY: Dr Cash, Cr Member's Capital."""
        amount = Money(abs(parsed_txn.amount))
        capital_account = self._get_standard_account("Member's Capital", entity)

        entries = [
            Entry(account_id=cash_account.id, debit_amount=amount),
            Entry(account_id=capital_account.id, credit_amount=amount),
        ]

        self._create_and_post_transaction(parsed_txn, entries, "Capital contribution")
        return 0

    def _book_loan(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book LOAN: Dr Notes Receivable, Cr Cash."""
        amount = Money(abs(parsed_txn.amount))
        notes_account = self._get_standard_account("Notes Receivable", entity)

        entries = [
            Entry(account_id=notes_account.id, debit_amount=amount),
            Entry(account_id=cash_account.id, credit_amount=amount),
        ]

        self._create_and_post_transaction(parsed_txn, entries, "Loan")
        return 0

    def _book_loan_repayment(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book LOAN_REPAYMENT: Dr Cash, Cr Notes Receivable + Interest Income.

        Since we don't have the principal/interest split, we assume 90% principal.
        """
        total_amount = Money(abs(parsed_txn.amount))
        # Assume 90% principal, 10% interest (simplified - real implementation
        # would track the loan balance and calculate properly)
        principal = Money(
            (total_amount.amount * Decimal("0.90")).quantize(Decimal("0.01"))
        )
        interest = total_amount - principal

        notes_account = self._get_standard_account("Notes Receivable", entity)
        income_account = self._get_standard_account("Interest Income", entity)

        entries = [
            Entry(account_id=cash_account.id, debit_amount=total_amount),
            Entry(account_id=notes_account.id, credit_amount=principal),
            Entry(account_id=income_account.id, credit_amount=interest),
        ]

        self._create_and_post_transaction(parsed_txn, entries, "Loan repayment")
        return 0

    def _book_purchase_qsbs(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book PURCHASE_QSBS: Dr Investment - QSBS Stock, Cr Cash + CREATE TAX LOT."""
        return self._book_investment_purchase(
            parsed_txn,
            entity,
            cash_account,
            "Investment - QSBS Stock",
            is_qsbs=True,
        )

    def _book_purchase_non_qsbs(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book PURCHASE_NON_QSBS: Dr Investment - Non-QSBS, Cr Cash + CREATE TAX LOT."""
        return self._book_investment_purchase(
            parsed_txn,
            entity,
            cash_account,
            "Investment - Non-QSBS",
            is_qsbs=False,
        )

    def _book_purchase_oz_fund(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book PURCHASE_OZ_FUND: Dr Investment - OZ Fund, Cr Cash + CREATE TAX LOT."""
        return self._book_investment_purchase(
            parsed_txn,
            entity,
            cash_account,
            "Investment - OZ Fund",
            is_qsbs=False,
        )

    def _book_investment_purchase(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
        investment_account_name: str,
        is_qsbs: bool,
    ) -> int:
        """Common logic for booking investment purchases and creating tax lots.

        Args:
            parsed_txn: The parsed transaction
            entity: Owning entity
            cash_account: Cash account
            investment_account_name: Name of investment account to debit
            is_qsbs: Whether this is a QSBS-eligible security

        Returns:
            Number of tax lots created (1)
        """
        amount = Money(abs(parsed_txn.amount))
        investment_account = self._get_standard_account(investment_account_name, entity)

        entries = [
            Entry(account_id=investment_account.id, debit_amount=amount),
            Entry(account_id=cash_account.id, credit_amount=amount),
        ]

        self._create_and_post_transaction(parsed_txn, entries, "Investment purchase")

        # Create tax lot
        security = self._get_or_create_security(
            parsed_txn.symbol,
            parsed_txn.cusip,
            parsed_txn.other_party,
            is_qsbs=is_qsbs,
        )
        position = self._get_or_create_position(investment_account, security)

        # Calculate quantity and cost per share
        quantity = parsed_txn.quantity or Decimal("1")
        if parsed_txn.price:
            cost_per_share = Money(parsed_txn.price)
        else:
            cost_per_share = Money(amount.amount / quantity)

        lot = TaxLot(
            position_id=position.id,
            acquisition_date=parsed_txn.date,
            cost_per_share=cost_per_share,
            original_quantity=Quantity(quantity),
            acquisition_type=AcquisitionType.PURCHASE,
            reference=parsed_txn.import_id,
        )
        self._tax_lot_repo.add(lot)

        return 1

    def _book_sale_qsbs(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book SALE_QSBS: Dr Cash, Cr Investment + Gain/Loss + DISPOSE TAX LOTS."""
        return self._book_investment_sale(
            parsed_txn,
            entity,
            cash_account,
            "Investment - QSBS Stock",
            "Gain on Sale - QSBS",
            is_qsbs=True,
        )

    def _book_sale_non_qsbs(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book SALE_NON_QSBS: Dr Cash, Cr Investment + Gain/Loss + DISPOSE TAX LOTS."""
        return self._book_investment_sale(
            parsed_txn,
            entity,
            cash_account,
            "Investment - Non-QSBS",
            "Gain/Loss on Sale",
            is_qsbs=False,
        )

    def _book_investment_sale(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
        investment_account_name: str,
        gain_account_name: str,
        is_qsbs: bool,
    ) -> int:
        """Common logic for booking investment sales and disposing tax lots.

        Args:
            parsed_txn: The parsed transaction
            entity: Owning entity
            cash_account: Cash account
            investment_account_name: Name of investment account to credit
            gain_account_name: Name of gain/loss account
            is_qsbs: Whether this is a QSBS security

        Returns:
            Number of tax lots created (always 0 for sales)
        """
        proceeds = Money(abs(parsed_txn.amount))
        investment_account = self._get_standard_account(investment_account_name, entity)
        gain_account = self._get_standard_account(gain_account_name, entity)

        # Try to find security and position to get cost basis
        security = self._get_or_create_security(
            parsed_txn.symbol,
            parsed_txn.cusip,
            parsed_txn.other_party,
            is_qsbs=is_qsbs,
        )
        position = self._position_repo.get_by_account_and_security(
            investment_account.id, security.id
        )

        quantity = Quantity(parsed_txn.quantity or Decimal("1"))
        cost_basis = Money.zero()
        realized_gain = proceeds

        # Try to dispose tax lots if position exists
        if position:
            try:
                dispositions = self._lot_matching_service.execute_sale(
                    position_id=position.id,
                    quantity=quantity,
                    proceeds=proceeds,
                    sale_date=parsed_txn.date,
                    method=LotSelection.FIFO,
                )
                # Calculate total cost basis
                total_cost = sum(
                    (d.cost_basis.amount for d in dispositions), Decimal("0")
                )
                cost_basis = Money(total_cost, proceeds.currency)
                realized_gain = proceeds - cost_basis
            except Exception:
                # If lot disposal fails, use full proceeds as gain
                pass

        # Build entries
        entries = [
            Entry(account_id=cash_account.id, debit_amount=proceeds),
        ]

        if cost_basis.is_positive:
            entries.append(
                Entry(account_id=investment_account.id, credit_amount=cost_basis)
            )

        if realized_gain.is_positive:
            entries.append(
                Entry(account_id=gain_account.id, credit_amount=realized_gain)
            )
        elif realized_gain.is_negative:
            entries.append(
                Entry(
                    account_id=gain_account.id,
                    debit_amount=Money(-realized_gain.amount),
                )
            )

        # Ensure we have at least one credit if no cost basis
        if not cost_basis.is_positive and realized_gain.is_zero:
            entries.append(
                Entry(account_id=investment_account.id, credit_amount=proceeds)
            )

        self._create_and_post_transaction(parsed_txn, entries, "Investment sale")
        return 0

    def _book_liquidation(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book LIQUIDATION: Dr Cash, Cr Investment + Gain/Loss."""
        proceeds = Money(abs(parsed_txn.amount))
        investment_account = self._get_standard_account(
            "Investment - Portfolio Co", entity
        )
        gain_account = self._get_standard_account("Gain/Loss on Liquidation", entity)

        # For liquidation, we may not have security info
        # Try to find position if we have identifiers
        cost_basis = Money.zero()
        if parsed_txn.symbol or parsed_txn.cusip:
            security = self._get_or_create_security(
                parsed_txn.symbol,
                parsed_txn.cusip,
                parsed_txn.other_party,
            )
            position = self._position_repo.get_by_account_and_security(
                investment_account.id, security.id
            )
            if position:
                cost_basis = self._lot_matching_service.get_position_cost_basis(
                    position.id
                )
                # Dispose all lots
                open_lots = self._lot_matching_service.get_open_lots(position.id)
                total_qty = sum(
                    (lot.remaining_quantity.value for lot in open_lots), Decimal("0")
                )
                if total_qty > Decimal("0"):
                    try:
                        self._lot_matching_service.execute_sale(
                            position_id=position.id,
                            quantity=Quantity(total_qty),
                            proceeds=proceeds,
                            sale_date=parsed_txn.date,
                            method=LotSelection.FIFO,
                        )
                    except Exception:
                        pass

        realized_gain = proceeds - cost_basis

        entries = [
            Entry(account_id=cash_account.id, debit_amount=proceeds),
        ]

        if cost_basis.is_positive:
            entries.append(
                Entry(account_id=investment_account.id, credit_amount=cost_basis)
            )

        if realized_gain.is_positive:
            entries.append(
                Entry(account_id=gain_account.id, credit_amount=realized_gain)
            )
        elif realized_gain.is_negative:
            entries.append(
                Entry(
                    account_id=gain_account.id,
                    debit_amount=Money(-realized_gain.amount),
                )
            )

        # Ensure we have at least one credit
        if not cost_basis.is_positive and realized_gain.is_zero:
            entries.append(
                Entry(account_id=investment_account.id, credit_amount=proceeds)
            )

        self._create_and_post_transaction(parsed_txn, entries, "Liquidation")
        return 0

    def _book_broker_fees(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book BROKER_FEES: Dr Investment (capitalize), Cr Cash."""
        amount = Money(abs(parsed_txn.amount))

        # If we have security identifiers, capitalize to that specific investment
        # Otherwise use generic Portfolio Co
        if parsed_txn.symbol or parsed_txn.cusip:
            security = self._get_or_create_security(
                parsed_txn.symbol,
                parsed_txn.cusip,
                parsed_txn.other_party,
            )
            # Create a specific investment account for this security
            investment_account = self._get_or_create_account(
                entity,
                f"Investment - {security.symbol}",
                AccountType.ASSET,
                AccountSubType.VENTURE_CAPITAL,
            )

            # Try to add to tax lot cost basis
            position = self._position_repo.get_by_account_and_security(
                investment_account.id, security.id
            )
            if position:
                open_lots = self._lot_matching_service.get_open_lots(position.id)
                if open_lots:
                    # Add fee to most recent lot
                    lot = max(open_lots, key=lambda x: x.acquisition_date)
                    # Adjust cost per share
                    new_cost = lot.cost_per_share.amount + (
                        amount.amount / lot.remaining_quantity.value
                    )
                    lot.cost_per_share = Money(new_cost)
                    self._tax_lot_repo.update(lot)
        else:
            investment_account = self._get_standard_account(
                "Investment - Portfolio Co", entity
            )

        entries = [
            Entry(account_id=investment_account.id, debit_amount=amount),
            Entry(account_id=cash_account.id, credit_amount=amount),
        ]

        self._create_and_post_transaction(parsed_txn, entries, "Broker fees")
        return 0

    def _book_return_of_funds(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book RETURN_OF_FUNDS: Dr Cash, Cr Investment (reduce basis)."""
        amount = Money(abs(parsed_txn.amount))
        investment_account = self._get_standard_account(
            "Investment - Portfolio Co", entity
        )

        entries = [
            Entry(account_id=cash_account.id, debit_amount=amount),
            Entry(account_id=investment_account.id, credit_amount=amount),
        ]

        self._create_and_post_transaction(parsed_txn, entries, "Return of funds")
        return 0

    def _book_public_market(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book PUBLIC_MARKET transactions (T-Bills, Crypto, etc.)."""
        amount = Money(abs(parsed_txn.amount))
        search_text = f"{parsed_txn.description} {parsed_txn.other_party or ''}".upper()

        # Determine sub-type based on keywords
        if "TREASURY" in search_text or "T-BILL" in search_text:
            return self._book_public_market_tbill(parsed_txn, entity, cash_account)
        elif (
            "CRYPTO" in search_text
            or "HYPERLIQUID" in search_text
            or "BITCOIN" in search_text
        ):
            return self._book_public_market_crypto(parsed_txn, entity, cash_account)
        else:
            # Default to T-Bill treatment
            return self._book_public_market_tbill(parsed_txn, entity, cash_account)

    def _book_public_market_tbill(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book T-Bill purchase or sale/maturity."""
        amount = Money(abs(parsed_txn.amount))
        tbill_account = self._get_standard_account(
            "Marketable Securities - T-Bills", entity
        )

        if parsed_txn.amount < 0:
            # Purchase - Dr T-Bills, Cr Cash
            entries = [
                Entry(account_id=tbill_account.id, debit_amount=amount),
                Entry(account_id=cash_account.id, credit_amount=amount),
            ]
            memo = "T-Bill purchase"
        else:
            # Sale/maturity - Dr Cash, Cr T-Bills + Interest Income
            # Assume some interest earned (simplified)
            income_account = self._get_standard_account("Interest Income", entity)
            # For simplicity, credit full amount to T-Bills
            # In reality, would need to track cost basis
            entries = [
                Entry(account_id=cash_account.id, debit_amount=amount),
                Entry(account_id=tbill_account.id, credit_amount=amount),
            ]
            memo = "T-Bill maturity/sale"

        self._create_and_post_transaction(parsed_txn, entries, memo)
        return 0

    def _book_public_market_crypto(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book cryptocurrency sale."""
        proceeds = Money(abs(parsed_txn.amount))
        crypto_account = self._get_standard_account("Digital Assets - Crypto", entity)
        gain_account = self._get_standard_account("Gain/Loss - Digital Assets", entity)

        if parsed_txn.amount > 0:
            # Sale - Dr Cash, Cr Digital Assets + Gain/Loss
            # Simplified: assume full proceeds is gain (would need cost basis tracking)
            entries = [
                Entry(account_id=cash_account.id, debit_amount=proceeds),
                Entry(account_id=crypto_account.id, credit_amount=proceeds),
            ]
            memo = "Crypto sale"
        else:
            # Purchase - Dr Digital Assets, Cr Cash
            entries = [
                Entry(account_id=crypto_account.id, debit_amount=proceeds),
                Entry(account_id=cash_account.id, credit_amount=proceeds),
            ]
            memo = "Crypto purchase"

        self._create_and_post_transaction(parsed_txn, entries, memo)
        return 0

    def _book_unclassified(
        self,
        parsed_txn: ParsedTransaction,
        entity: Entity,
        cash_account: Account,
    ) -> int:
        """Book UNCLASSIFIED: Dr/Cr Cash vs Suspense."""
        amount = Money(abs(parsed_txn.amount))
        suspense_account = self._get_standard_account("Suspense / Unclassified", entity)

        if parsed_txn.amount > 0:
            # Cash inflow - Dr Cash, Cr Suspense
            entries = [
                Entry(account_id=cash_account.id, debit_amount=amount),
                Entry(account_id=suspense_account.id, credit_amount=amount),
            ]
        else:
            # Cash outflow - Dr Suspense, Cr Cash
            entries = [
                Entry(account_id=suspense_account.id, debit_amount=amount),
                Entry(account_id=cash_account.id, credit_amount=amount),
            ]

        self._create_and_post_transaction(parsed_txn, entries, "Unclassified")
        return 0
