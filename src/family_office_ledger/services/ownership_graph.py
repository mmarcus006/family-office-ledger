"""Service for ownership graph traversal, cycle detection, and look-through calculations."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from family_office_ledger.domain.ownership import EntityOwnership
from family_office_ledger.domain.value_objects import AccountType
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    EntityOwnershipRepository,
    EntityRepository,
    HouseholdRepository,
    PositionRepository,
    TransactionRepository,
)


class CycleDetectedError(ValueError):
    def __init__(self, cycle_path: list[UUID]) -> None:
        self.cycle_path = cycle_path
        path_str = " -> ".join(str(uid) for uid in cycle_path)
        super().__init__(f"Cycle detected in ownership graph: {path_str}")


@dataclass
class OwnershipEdge:
    owned_entity_id: UUID
    ownership_fraction: Decimal


@dataclass
class EffectiveOwnership:
    entity_id: UUID
    effective_fraction: Decimal
    path: list[UUID] = field(default_factory=list)


@dataclass
class LookThroughPosition:
    entity_id: UUID
    entity_name: str
    account_id: UUID
    account_name: str
    direct_balance: Decimal
    effective_fraction: Decimal
    weighted_balance: Decimal


class OwnershipGraphService:
    def __init__(
        self,
        ownership_repo: EntityOwnershipRepository,
        household_repo: HouseholdRepository,
        entity_repo: EntityRepository | None = None,
        account_repo: AccountRepository | None = None,
        transaction_repo: TransactionRepository | None = None,
        position_repo: PositionRepository | None = None,
    ) -> None:
        self._ownership_repo = ownership_repo
        self._household_repo = household_repo
        self._entity_repo = entity_repo
        self._account_repo = account_repo
        self._transaction_repo = transaction_repo
        self._position_repo = position_repo

    def build_adjacency_map(self, as_of_date: date) -> dict[UUID, list[OwnershipEdge]]:
        edges = self._ownership_repo.list_active_as_of_date(as_of_date)
        adjacency: dict[UUID, list[OwnershipEdge]] = defaultdict(list)
        for edge in edges:
            adjacency[edge.owner_entity_id].append(
                OwnershipEdge(
                    owned_entity_id=edge.owned_entity_id,
                    ownership_fraction=edge.ownership_fraction,
                )
            )
        return dict(adjacency)

    def detect_cycle(self, as_of_date: date) -> list[UUID] | None:
        adjacency = self.build_adjacency_map(as_of_date)
        visited: set[UUID] = set()
        rec_stack: set[UUID] = set()
        path: list[UUID] = []

        def dfs(node: UUID) -> list[UUID] | None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for edge in adjacency.get(node, []):
                if edge.owned_entity_id not in visited:
                    result = dfs(edge.owned_entity_id)
                    if result is not None:
                        return result
                elif edge.owned_entity_id in rec_stack:
                    cycle_start = path.index(edge.owned_entity_id)
                    return path[cycle_start:] + [edge.owned_entity_id]

            path.pop()
            rec_stack.remove(node)
            return None

        for node in adjacency:
            if node not in visited:
                cycle = dfs(node)
                if cycle is not None:
                    return cycle
        return None

    def validate_no_cycles(self, as_of_date: date) -> None:
        cycle = self.detect_cycle(as_of_date)
        if cycle is not None:
            raise CycleDetectedError(cycle)

    def validate_ownership_edge(self, ownership: EntityOwnership) -> None:
        adjacency = self.build_adjacency_map(ownership.effective_start_date)

        adjacency.setdefault(ownership.owner_entity_id, []).append(
            OwnershipEdge(
                owned_entity_id=ownership.owned_entity_id,
                ownership_fraction=ownership.ownership_fraction,
            )
        )

        visited: set[UUID] = set()
        rec_stack: set[UUID] = set()
        path: list[UUID] = []

        def dfs(node: UUID) -> list[UUID] | None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for edge in adjacency.get(node, []):
                if edge.owned_entity_id not in visited:
                    result = dfs(edge.owned_entity_id)
                    if result is not None:
                        return result
                elif edge.owned_entity_id in rec_stack:
                    cycle_start = path.index(edge.owned_entity_id)
                    return path[cycle_start:] + [edge.owned_entity_id]

            path.pop()
            rec_stack.remove(node)
            return None

        for node in adjacency:
            if node not in visited:
                cycle = dfs(node)
                if cycle is not None:
                    raise CycleDetectedError(cycle)

    def compute_effective_ownership(
        self, root_entity_id: UUID, as_of_date: date
    ) -> dict[UUID, EffectiveOwnership]:
        adjacency = self.build_adjacency_map(as_of_date)
        result: dict[UUID, EffectiveOwnership] = {}

        def traverse(
            entity_id: UUID, cumulative_fraction: Decimal, path: list[UUID]
        ) -> None:
            current_path = path + [entity_id]

            if entity_id not in result:
                result[entity_id] = EffectiveOwnership(
                    entity_id=entity_id,
                    effective_fraction=cumulative_fraction,
                    path=current_path,
                )
            else:
                result[entity_id].effective_fraction += cumulative_fraction
                return

            for edge in adjacency.get(entity_id, []):
                new_fraction = cumulative_fraction * edge.ownership_fraction
                traverse(edge.owned_entity_id, new_fraction, current_path)

        traverse(root_entity_id, Decimal("1.0"), [])
        return result

    def list_household_roots(
        self, household_id: UUID, as_of_date: date | None = None
    ) -> list[UUID]:
        members = list(self._household_repo.list_members(household_id, as_of_date))
        return [m.entity_id for m in members if m.role == "client"]

    def get_all_owned_entities(
        self, root_entity_id: UUID, as_of_date: date
    ) -> set[UUID]:
        effective = self.compute_effective_ownership(root_entity_id, as_of_date)
        return set(effective.keys())

    def get_ownership_chain(
        self, from_entity_id: UUID, to_entity_id: UUID, as_of_date: date
    ) -> list[EntityOwnership] | None:
        edges_by_owner: dict[UUID, list[EntityOwnership]] = defaultdict(list)
        for edge in self._ownership_repo.list_active_as_of_date(as_of_date):
            edges_by_owner[edge.owner_entity_id].append(edge)

        visited: set[UUID] = set()
        path: list[EntityOwnership] = []

        def dfs(current: UUID) -> bool:
            if current == to_entity_id:
                return True
            if current in visited:
                return False
            visited.add(current)

            for edge in edges_by_owner.get(current, []):
                path.append(edge)
                if dfs(edge.owned_entity_id):
                    return True
                path.pop()
            return False

        if dfs(from_entity_id):
            return path
        return None

    def compute_household_effective_ownership(
        self, household_id: UUID, as_of_date: date
    ) -> dict[UUID, Decimal]:
        roots = self.list_household_roots(household_id, as_of_date)
        combined: dict[UUID, Decimal] = {}

        for root_id in roots:
            effective = self.compute_effective_ownership(root_id, as_of_date)
            for entity_id, ownership in effective.items():
                if entity_id in combined:
                    combined[entity_id] = min(
                        Decimal("1.0"),
                        combined[entity_id] + ownership.effective_fraction,
                    )
                else:
                    combined[entity_id] = ownership.effective_fraction

        return combined

    def _calculate_account_balance(self, account_id: UUID, as_of_date: date) -> Decimal:
        if self._transaction_repo is None:
            return Decimal("0")

        transactions = self._transaction_repo.list_by_account(
            account_id, end_date=as_of_date
        )
        balance = Decimal("0")
        for txn in transactions:
            for entry in txn.entries:
                if entry.account_id == account_id:
                    balance += entry.debit_amount.amount - entry.credit_amount.amount
        return balance

    def household_look_through_net_worth(
        self, household_id: UUID, as_of_date: date
    ) -> dict[str, Any]:
        if self._entity_repo is None or self._account_repo is None:
            return {
                "total_assets": Decimal("0"),
                "total_liabilities": Decimal("0"),
                "net_worth": Decimal("0"),
                "detail": [],
            }

        effective_ownership = self.compute_household_effective_ownership(
            household_id, as_of_date
        )

        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        detail: list[dict[str, Any]] = []

        for entity_id, fraction in effective_ownership.items():
            entity = self._entity_repo.get(entity_id)
            if entity is None:
                continue

            accounts = list(self._account_repo.list_by_entity(entity_id))

            for account in accounts:
                balance = self._calculate_account_balance(account.id, as_of_date)
                weighted_balance = balance * fraction

                if account.account_type == AccountType.ASSET:
                    total_assets += weighted_balance
                elif account.account_type == AccountType.LIABILITY:
                    total_liabilities += abs(weighted_balance)

                detail.append(
                    {
                        "entity_id": str(entity_id),
                        "entity_name": entity.name,
                        "account_id": str(account.id),
                        "account_name": account.name,
                        "direct_balance": balance,
                        "effective_fraction": fraction,
                        "weighted_balance": weighted_balance,
                    }
                )

        return {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": total_assets - total_liabilities,
            "detail": detail,
        }

    def beneficial_owner_look_through_net_worth(
        self, owner_entity_id: UUID, as_of_date: date
    ) -> dict[str, Any]:
        if self._entity_repo is None or self._account_repo is None:
            return {
                "total_assets": Decimal("0"),
                "total_liabilities": Decimal("0"),
                "net_worth": Decimal("0"),
                "detail": [],
            }

        effective_ownership = self.compute_effective_ownership(
            owner_entity_id, as_of_date
        )

        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        detail: list[dict[str, Any]] = []

        for entity_id, ownership in effective_ownership.items():
            entity = self._entity_repo.get(entity_id)
            if entity is None:
                continue

            accounts = list(self._account_repo.list_by_entity(entity_id))

            for account in accounts:
                balance = self._calculate_account_balance(account.id, as_of_date)
                weighted_balance = balance * ownership.effective_fraction

                if account.account_type == AccountType.ASSET:
                    total_assets += weighted_balance
                elif account.account_type == AccountType.LIABILITY:
                    total_liabilities += abs(weighted_balance)

                detail.append(
                    {
                        "entity_id": str(entity_id),
                        "entity_name": entity.name,
                        "account_id": str(account.id),
                        "account_name": account.name,
                        "direct_balance": balance,
                        "effective_fraction": ownership.effective_fraction,
                        "weighted_balance": weighted_balance,
                    }
                )

        return {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": total_assets - total_liabilities,
            "detail": detail,
        }

    def partnership_capital_accounts_report(
        self, partnership_entity_id: UUID, as_of_date: date
    ) -> dict[str, Any]:
        if self._entity_repo is None or self._account_repo is None:
            return {
                "partnership_id": str(partnership_entity_id),
                "partnership_name": "",
                "as_of_date": as_of_date.isoformat(),
                "capital_accounts": [],
                "total_capital": Decimal("0"),
            }

        entity = self._entity_repo.get(partnership_entity_id)
        if entity is None:
            return {
                "partnership_id": str(partnership_entity_id),
                "partnership_name": "",
                "as_of_date": as_of_date.isoformat(),
                "capital_accounts": [],
                "total_capital": Decimal("0"),
                "error": "Partnership entity not found",
            }

        accounts = list(self._account_repo.list_by_entity(partnership_entity_id))
        capital_accounts: list[dict[str, Any]] = []
        total_capital = Decimal("0")

        for account in accounts:
            if account.account_type != AccountType.EQUITY:
                continue

            balance = self._calculate_account_balance(account.id, as_of_date)

            capital_accounts.append(
                {
                    "account_id": str(account.id),
                    "account_name": account.name,
                    "balance": balance,
                }
            )
            total_capital += balance

        return {
            "partnership_id": str(partnership_entity_id),
            "partnership_name": entity.name,
            "as_of_date": as_of_date.isoformat(),
            "capital_accounts": capital_accounts,
            "total_capital": total_capital,
        }


__all__ = [
    "CycleDetectedError",
    "OwnershipEdge",
    "EffectiveOwnership",
    "LookThroughPosition",
    "OwnershipGraphService",
]
