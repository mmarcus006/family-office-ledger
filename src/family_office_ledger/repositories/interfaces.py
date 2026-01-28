from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import date
from uuid import UUID

from family_office_ledger.domain.entities import Account, Entity, Position, Security
from family_office_ledger.domain.transactions import TaxLot, Transaction


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
