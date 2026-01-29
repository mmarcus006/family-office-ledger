from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import date
from uuid import UUID

from family_office_ledger.domain.budgets import Budget, BudgetLineItem
from family_office_ledger.domain.entities import Account, Entity, Position, Security
from family_office_ledger.domain.exchange_rates import ExchangeRate
from family_office_ledger.domain.households import Household, HouseholdMember
from family_office_ledger.domain.ownership import EntityOwnership
from family_office_ledger.domain.reconciliation import ReconciliationSession
from family_office_ledger.domain.transactions import TaxLot, Transaction
from family_office_ledger.domain.vendors import Vendor


class EntityRepository(ABC):
    @abstractmethod
    def add(self, entity: Entity) -> None:
        pass

    @abstractmethod
    def get(self, entity_id: UUID) -> Entity | None:
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Entity | None:
        pass

    @abstractmethod
    def list_all(self) -> Iterable[Entity]:
        pass

    @abstractmethod
    def list_active(self) -> Iterable[Entity]:
        pass

    @abstractmethod
    def update(self, entity: Entity) -> None:
        pass

    @abstractmethod
    def delete(self, entity_id: UUID) -> None:
        pass


class HouseholdRepository(ABC):
    @abstractmethod
    def add(self, household: Household) -> None:
        pass

    @abstractmethod
    def get(self, household_id: UUID) -> Household | None:
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Household | None:
        pass

    @abstractmethod
    def list_all(self) -> Iterable[Household]:
        pass

    @abstractmethod
    def list_active(self) -> Iterable[Household]:
        pass

    @abstractmethod
    def update(self, household: Household) -> None:
        pass

    @abstractmethod
    def delete(self, household_id: UUID) -> None:
        pass

    @abstractmethod
    def add_member(self, member: HouseholdMember) -> None:
        pass

    @abstractmethod
    def get_member(self, member_id: UUID) -> HouseholdMember | None:
        pass

    @abstractmethod
    def list_members(
        self, household_id: UUID, as_of_date: date | None = None
    ) -> Iterable[HouseholdMember]:
        pass

    @abstractmethod
    def list_households_for_entity(
        self, entity_id: UUID, as_of_date: date | None = None
    ) -> Iterable[HouseholdMember]:
        pass

    @abstractmethod
    def update_member(self, member: HouseholdMember) -> None:
        pass

    @abstractmethod
    def remove_member(self, member_id: UUID) -> None:
        pass


class AccountRepository(ABC):
    @abstractmethod
    def add(self, account: Account) -> None:
        pass

    @abstractmethod
    def get(self, account_id: UUID) -> Account | None:
        pass

    @abstractmethod
    def get_by_name(self, name: str, entity_id: UUID) -> Account | None:
        pass

    @abstractmethod
    def list_by_entity(self, entity_id: UUID) -> Iterable[Account]:
        pass

    @abstractmethod
    def list_investment_accounts(
        self, entity_id: UUID | None = None
    ) -> Iterable[Account]:
        pass

    @abstractmethod
    def update(self, account: Account) -> None:
        pass

    @abstractmethod
    def delete(self, account_id: UUID) -> None:
        pass


class SecurityRepository(ABC):
    @abstractmethod
    def add(self, security: Security) -> None:
        pass

    @abstractmethod
    def get(self, security_id: UUID) -> Security | None:
        pass

    @abstractmethod
    def get_by_symbol(self, symbol: str) -> Security | None:
        pass

    @abstractmethod
    def get_by_cusip(self, cusip: str) -> Security | None:
        pass

    @abstractmethod
    def list_all(self) -> Iterable[Security]:
        pass

    @abstractmethod
    def list_qsbs_eligible(self) -> Iterable[Security]:
        pass

    @abstractmethod
    def update(self, security: Security) -> None:
        pass


class PositionRepository(ABC):
    @abstractmethod
    def add(self, position: Position) -> None:
        pass

    @abstractmethod
    def get(self, position_id: UUID) -> Position | None:
        pass

    @abstractmethod
    def get_by_account_and_security(
        self, account_id: UUID, security_id: UUID
    ) -> Position | None:
        pass

    @abstractmethod
    def list_by_account(self, account_id: UUID) -> Iterable[Position]:
        pass

    @abstractmethod
    def list_by_security(self, security_id: UUID) -> Iterable[Position]:
        pass

    @abstractmethod
    def list_by_entity(self, entity_id: UUID) -> Iterable[Position]:
        pass

    @abstractmethod
    def update(self, position: Position) -> None:
        pass


class TransactionRepository(ABC):
    @abstractmethod
    def add(self, txn: Transaction) -> None:
        pass

    @abstractmethod
    def get(self, txn_id: UUID) -> Transaction | None:
        pass

    @abstractmethod
    def list_by_account(
        self,
        account_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Iterable[Transaction]:
        pass

    @abstractmethod
    def list_by_entity(
        self,
        entity_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Iterable[Transaction]:
        pass

    @abstractmethod
    def list_by_date_range(
        self, start_date: date, end_date: date
    ) -> Iterable[Transaction]:
        pass

    @abstractmethod
    def get_reversals(self, txn_id: UUID) -> Iterable[Transaction]:
        pass

    @abstractmethod
    def update(self, txn: Transaction) -> None:
        pass


class TaxLotRepository(ABC):
    @abstractmethod
    def add(self, lot: TaxLot) -> None:
        pass

    @abstractmethod
    def get(self, lot_id: UUID) -> TaxLot | None:
        pass

    @abstractmethod
    def list_by_position(self, position_id: UUID) -> Iterable[TaxLot]:
        pass

    @abstractmethod
    def list_open_by_position(self, position_id: UUID) -> Iterable[TaxLot]:
        pass

    @abstractmethod
    def list_by_acquisition_date_range(
        self, position_id: UUID, start_date: date, end_date: date
    ) -> Iterable[TaxLot]:
        pass

    @abstractmethod
    def list_wash_sale_candidates(
        self, position_id: UUID, sale_date: date
    ) -> Iterable[TaxLot]:
        pass

    @abstractmethod
    def update(self, lot: TaxLot) -> None:
        pass


class ReconciliationSessionRepository(ABC):
    """Repository interface for reconciliation sessions.

    Manages persistence of reconciliation sessions and their associated matches.
    Sessions are eagerly loaded with all matches.
    """

    @abstractmethod
    def add(self, session: ReconciliationSession) -> None:
        """Add a new reconciliation session with all its matches."""
        pass

    @abstractmethod
    def get(self, session_id: UUID) -> ReconciliationSession | None:
        """Get a session by ID, including all matches."""
        pass

    @abstractmethod
    def get_pending_for_account(self, account_id: UUID) -> ReconciliationSession | None:
        """Get the pending session for an account, if one exists."""
        pass

    @abstractmethod
    def update(self, session: ReconciliationSession) -> None:
        """Update a session and all its matches (full replace)."""
        pass

    @abstractmethod
    def delete(self, session_id: UUID) -> None:
        """Delete a session and all its matches (cascade)."""
        pass

    @abstractmethod
    def list_by_account(self, account_id: UUID) -> Iterable[ReconciliationSession]:
        """List all sessions for an account."""
        pass


class ExchangeRateRepository(ABC):
    """Repository interface for exchange rates."""

    @abstractmethod
    def add(self, rate: ExchangeRate) -> None:
        """Add a new exchange rate."""
        pass

    @abstractmethod
    def get(self, rate_id: UUID) -> ExchangeRate | None:
        """Get exchange rate by ID."""
        pass

    @abstractmethod
    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        effective_date: date,
    ) -> ExchangeRate | None:
        """Get exchange rate for currency pair on specific date."""
        pass

    @abstractmethod
    def get_latest_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate | None:
        """Get most recent exchange rate for currency pair."""
        pass

    @abstractmethod
    def list_by_currency_pair(
        self,
        from_currency: str,
        to_currency: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Iterable[ExchangeRate]:
        """List exchange rates for currency pair within date range."""
        pass

    @abstractmethod
    def list_by_date(self, effective_date: date) -> Iterable[ExchangeRate]:
        """List all exchange rates for a specific date."""
        pass

    @abstractmethod
    def delete(self, rate_id: UUID) -> None:
        """Delete an exchange rate."""
        pass


class VendorRepository(ABC):
    """Repository interface for vendors/payees."""

    @abstractmethod
    def add(self, vendor: Vendor) -> None:
        """Add a new vendor."""
        pass

    @abstractmethod
    def get(self, vendor_id: UUID) -> Vendor | None:
        """Get vendor by ID."""
        pass

    @abstractmethod
    def update(self, vendor: Vendor) -> None:
        """Update an existing vendor."""
        pass

    @abstractmethod
    def delete(self, vendor_id: UUID) -> None:
        """Delete a vendor."""
        pass

    @abstractmethod
    def list_all(self, include_inactive: bool = False) -> Iterable[Vendor]:
        """List all vendors, optionally including inactive ones."""
        pass

    @abstractmethod
    def list_by_category(self, category: str) -> Iterable[Vendor]:
        """List vendors by category."""
        pass

    @abstractmethod
    def search_by_name(self, name_pattern: str) -> Iterable[Vendor]:
        """Search vendors by name pattern."""
        pass

    @abstractmethod
    def get_by_tax_id(self, tax_id: str) -> Vendor | None:
        """Get vendor by tax ID."""
        pass


class BudgetRepository(ABC):
    @abstractmethod
    def add(self, budget: Budget) -> None:
        pass

    @abstractmethod
    def get(self, budget_id: UUID) -> Budget | None:
        pass

    @abstractmethod
    def update(self, budget: Budget) -> None:
        pass

    @abstractmethod
    def delete(self, budget_id: UUID) -> None:
        pass

    @abstractmethod
    def list_by_entity(
        self, entity_id: UUID, include_inactive: bool = False
    ) -> Iterable[Budget]:
        pass

    @abstractmethod
    def get_active_for_date(self, entity_id: UUID, as_of_date: date) -> Budget | None:
        pass

    @abstractmethod
    def add_line_item(self, line_item: BudgetLineItem) -> None:
        pass

    @abstractmethod
    def get_line_items(self, budget_id: UUID) -> Iterable[BudgetLineItem]:
        pass

    @abstractmethod
    def update_line_item(self, line_item: BudgetLineItem) -> None:
        pass

    @abstractmethod
    def delete_line_item(self, line_item_id: UUID) -> None:
        pass


class EntityOwnershipRepository(ABC):
    @abstractmethod
    def add(self, ownership: EntityOwnership) -> None:
        pass

    @abstractmethod
    def get(self, ownership_id: UUID) -> EntityOwnership | None:
        pass

    @abstractmethod
    def list_by_owner(
        self, owner_entity_id: UUID, as_of_date: date | None = None
    ) -> Iterable[EntityOwnership]:
        pass

    @abstractmethod
    def list_by_owned(
        self, owned_entity_id: UUID, as_of_date: date | None = None
    ) -> Iterable[EntityOwnership]:
        pass

    @abstractmethod
    def list_active_as_of_date(self, as_of_date: date) -> Iterable[EntityOwnership]:
        pass

    @abstractmethod
    def update(self, ownership: EntityOwnership) -> None:
        pass

    @abstractmethod
    def delete(self, ownership_id: UUID) -> None:
        pass
