"""Tests for EntityOwnership domain model and repository."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.entities import Entity
from family_office_ledger.domain.ownership import EntityOwnership, SelfOwnershipError
from family_office_ledger.domain.value_objects import EntityType
from family_office_ledger.domain.entities import Account
from family_office_ledger.domain.households import Household, HouseholdMember
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.value_objects import AccountType, Money
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityOwnershipRepository,
    SQLiteEntityRepository,
    SQLiteHouseholdRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.ownership_graph import (
    CycleDetectedError,
    OwnershipGraphService,
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
def ownership_repo(db: SQLiteDatabase) -> SQLiteEntityOwnershipRepository:
    return SQLiteEntityOwnershipRepository(db)


@pytest.fixture
def household_repo(db: SQLiteDatabase) -> SQLiteHouseholdRepository:
    return SQLiteHouseholdRepository(db)


@pytest.fixture
def account_repo(db: SQLiteDatabase) -> SQLiteAccountRepository:
    return SQLiteAccountRepository(db)


@pytest.fixture
def transaction_repo(db: SQLiteDatabase) -> SQLiteTransactionRepository:
    return SQLiteTransactionRepository(db)


@pytest.fixture
def ownership_service(
    ownership_repo: SQLiteEntityOwnershipRepository,
    household_repo: SQLiteHouseholdRepository,
) -> OwnershipGraphService:
    return OwnershipGraphService(ownership_repo, household_repo)


@pytest.fixture
def full_ownership_service(
    ownership_repo: SQLiteEntityOwnershipRepository,
    household_repo: SQLiteHouseholdRepository,
    entity_repo: SQLiteEntityRepository,
    account_repo: SQLiteAccountRepository,
    transaction_repo: SQLiteTransactionRepository,
) -> OwnershipGraphService:
    return OwnershipGraphService(
        ownership_repo,
        household_repo,
        entity_repo,
        account_repo,
        transaction_repo,
    )


@pytest.fixture
def alice(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(name="Alice Smith", entity_type=EntityType.INDIVIDUAL)
    entity_repo.add(entity)
    return entity


@pytest.fixture
def bob(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(name="Bob Smith", entity_type=EntityType.INDIVIDUAL)
    entity_repo.add(entity)
    return entity


@pytest.fixture
def family_trust(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(name="Smith Family Trust", entity_type=EntityType.TRUST)
    entity_repo.add(entity)
    return entity


@pytest.fixture
def holding_llc(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(name="Smith Holdings LLC", entity_type=EntityType.LLC)
    entity_repo.add(entity)
    return entity


class TestEntityOwnershipDomain:
    def test_self_edge_rejected(self) -> None:
        entity_id = uuid4()
        with pytest.raises(SelfOwnershipError) as exc_info:
            EntityOwnership(
                owner_entity_id=entity_id,
                owned_entity_id=entity_id,
                ownership_fraction=Decimal("0.5"),
                effective_start_date=date(2024, 1, 1),
            )
        assert exc_info.value.entity_id == entity_id
        assert "cannot own itself" in str(exc_info.value)

    def test_ownership_fraction_coerced_to_decimal(self) -> None:
        owner_id = uuid4()
        owned_id = uuid4()
        ownership = EntityOwnership(
            owner_entity_id=owner_id,
            owned_entity_id=owned_id,
            ownership_fraction=0.5,  # type: ignore[arg-type]
            effective_start_date=date(2024, 1, 1),
        )
        assert isinstance(ownership.ownership_fraction, Decimal)
        assert ownership.ownership_fraction == Decimal("0.5")

    def test_is_active_on_within_range(self) -> None:
        owner_id = uuid4()
        owned_id = uuid4()
        ownership = EntityOwnership(
            owner_entity_id=owner_id,
            owned_entity_id=owned_id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
            effective_end_date=date(2024, 12, 31),
        )
        assert ownership.is_active_on(date(2024, 6, 15)) is True
        assert ownership.is_active_on(date(2024, 1, 1)) is True
        assert ownership.is_active_on(date(2024, 12, 30)) is True

    def test_is_active_on_before_start(self) -> None:
        owner_id = uuid4()
        owned_id = uuid4()
        ownership = EntityOwnership(
            owner_entity_id=owner_id,
            owned_entity_id=owned_id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        assert ownership.is_active_on(date(2023, 12, 31)) is False

    def test_is_active_on_after_end(self) -> None:
        owner_id = uuid4()
        owned_id = uuid4()
        ownership = EntityOwnership(
            owner_entity_id=owner_id,
            owned_entity_id=owned_id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
            effective_end_date=date(2024, 12, 31),
        )
        assert ownership.is_active_on(date(2024, 12, 31)) is False
        assert ownership.is_active_on(date(2025, 1, 1)) is False

    def test_is_active_on_no_end_date(self) -> None:
        owner_id = uuid4()
        owned_id = uuid4()
        ownership = EntityOwnership(
            owner_entity_id=owner_id,
            owned_entity_id=owned_id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
            effective_end_date=None,
        )
        assert ownership.is_active_on(date(2099, 12, 31)) is True


class TestSQLiteEntityOwnershipRepository:
    def test_add_and_get(
        self,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        family_trust: Entity,
    ) -> None:
        ownership = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership)

        retrieved = ownership_repo.get(ownership.id)
        assert retrieved is not None
        assert retrieved.owner_entity_id == alice.id
        assert retrieved.owned_entity_id == family_trust.id
        assert retrieved.ownership_fraction == Decimal("0.5")
        assert retrieved.effective_start_date == date(2024, 1, 1)

    def test_self_edge_rejected_on_add(
        self,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
    ) -> None:
        with pytest.raises(SelfOwnershipError):
            ownership = EntityOwnership(
                owner_entity_id=alice.id,
                owned_entity_id=alice.id,
                ownership_fraction=Decimal("0.5"),
                effective_start_date=date(2024, 1, 1),
            )
            ownership_repo.add(ownership)

    def test_list_by_owner(
        self,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        bob: Entity,
        family_trust: Entity,
        holding_llc: Entity,
    ) -> None:
        ownership1 = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership2 = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=holding_llc.id,
            ownership_fraction=Decimal("0.25"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership3 = EntityOwnership(
            owner_entity_id=bob.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership1)
        ownership_repo.add(ownership2)
        ownership_repo.add(ownership3)

        alice_ownerships = list(ownership_repo.list_by_owner(alice.id))
        assert len(alice_ownerships) == 2

        bob_ownerships = list(ownership_repo.list_by_owner(bob.id))
        assert len(bob_ownerships) == 1

    def test_list_by_owned(
        self,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        bob: Entity,
        family_trust: Entity,
    ) -> None:
        ownership1 = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership2 = EntityOwnership(
            owner_entity_id=bob.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership1)
        ownership_repo.add(ownership2)

        trust_owners = list(ownership_repo.list_by_owned(family_trust.id))
        assert len(trust_owners) == 2

    def test_list_by_owner_as_of_date(
        self,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        family_trust: Entity,
        holding_llc: Entity,
    ) -> None:
        ownership_current = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_ended = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=holding_llc.id,
            ownership_fraction=Decimal("0.25"),
            effective_start_date=date(2023, 1, 1),
            effective_end_date=date(2024, 6, 1),
        )
        ownership_repo.add(ownership_current)
        ownership_repo.add(ownership_ended)

        alice_current = list(
            ownership_repo.list_by_owner(alice.id, as_of_date=date(2024, 7, 1))
        )
        assert len(alice_current) == 1
        assert alice_current[0].owned_entity_id == family_trust.id

        alice_all = list(ownership_repo.list_by_owner(alice.id))
        assert len(alice_all) == 2

        alice_past = list(
            ownership_repo.list_by_owner(alice.id, as_of_date=date(2024, 3, 1))
        )
        assert len(alice_past) == 2

    def test_list_active_as_of_date(
        self,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        bob: Entity,
        family_trust: Entity,
    ) -> None:
        ownership_active = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_ended = EntityOwnership(
            owner_entity_id=bob.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2023, 1, 1),
            effective_end_date=date(2024, 6, 1),
        )
        ownership_repo.add(ownership_active)
        ownership_repo.add(ownership_ended)

        active_july = list(ownership_repo.list_active_as_of_date(date(2024, 7, 1)))
        assert len(active_july) == 1
        assert active_july[0].owner_entity_id == alice.id

        active_march = list(ownership_repo.list_active_as_of_date(date(2024, 3, 1)))
        assert len(active_march) == 2

    def test_update(
        self,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        family_trust: Entity,
    ) -> None:
        ownership = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership)

        ownership.update_fraction(Decimal("0.75"))
        ownership_repo.update(ownership)

        retrieved = ownership_repo.get(ownership.id)
        assert retrieved is not None
        assert retrieved.ownership_fraction == Decimal("0.75")

    def test_delete(
        self,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        family_trust: Entity,
    ) -> None:
        ownership = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership)
        assert ownership_repo.get(ownership.id) is not None

        ownership_repo.delete(ownership.id)
        assert ownership_repo.get(ownership.id) is None

    def test_end_ownership(
        self,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        family_trust: Entity,
    ) -> None:
        ownership = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership)

        ownership.end_ownership(date(2024, 12, 31))
        ownership_repo.update(ownership)

        retrieved = ownership_repo.get(ownership.id)
        assert retrieved is not None
        assert retrieved.effective_end_date == date(2024, 12, 31)
        assert retrieved.is_active_on(date(2024, 12, 31)) is False
        assert retrieved.is_active_on(date(2024, 12, 30)) is True


class TestOwnershipGraphService:
    def test_build_adjacency_map(
        self,
        ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        bob: Entity,
        family_trust: Entity,
    ) -> None:
        ownership1 = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership2 = EntityOwnership(
            owner_entity_id=bob.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership1)
        ownership_repo.add(ownership2)

        adjacency = ownership_service.build_adjacency_map(date(2024, 6, 1))

        assert alice.id in adjacency
        assert bob.id in adjacency
        assert len(adjacency[alice.id]) == 1
        assert adjacency[alice.id][0].owned_entity_id == family_trust.id

    def test_cycle_rejected(
        self,
        ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        family_trust: Entity,
        holding_llc: Entity,
    ) -> None:
        ownership1 = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership2 = EntityOwnership(
            owner_entity_id=family_trust.id,
            owned_entity_id=holding_llc.id,
            ownership_fraction=Decimal("1.0"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership3 = EntityOwnership(
            owner_entity_id=holding_llc.id,
            owned_entity_id=alice.id,
            ownership_fraction=Decimal("0.25"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership1)
        ownership_repo.add(ownership2)
        ownership_repo.add(ownership3)

        cycle = ownership_service.detect_cycle(date(2024, 6, 1))
        assert cycle is not None
        assert len(cycle) >= 3

        with pytest.raises(CycleDetectedError) as exc_info:
            ownership_service.validate_no_cycles(date(2024, 6, 1))
        assert len(exc_info.value.cycle_path) >= 3

    def test_no_cycle_in_valid_graph(
        self,
        ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        bob: Entity,
        family_trust: Entity,
        holding_llc: Entity,
    ) -> None:
        ownership1 = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership2 = EntityOwnership(
            owner_entity_id=bob.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership3 = EntityOwnership(
            owner_entity_id=family_trust.id,
            owned_entity_id=holding_llc.id,
            ownership_fraction=Decimal("1.0"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership1)
        ownership_repo.add(ownership2)
        ownership_repo.add(ownership3)

        cycle = ownership_service.detect_cycle(date(2024, 6, 1))
        assert cycle is None

        ownership_service.validate_no_cycles(date(2024, 6, 1))

    def test_validate_ownership_edge_rejects_cycle(
        self,
        ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        family_trust: Entity,
    ) -> None:
        ownership1 = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership1)

        cycle_edge = EntityOwnership(
            owner_entity_id=family_trust.id,
            owned_entity_id=alice.id,
            ownership_fraction=Decimal("0.25"),
            effective_start_date=date(2024, 1, 1),
        )

        with pytest.raises(CycleDetectedError):
            ownership_service.validate_ownership_edge(cycle_edge)

    def test_compute_effective_ownership_simple(
        self,
        ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        family_trust: Entity,
    ) -> None:
        ownership = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership)

        effective = ownership_service.compute_effective_ownership(
            alice.id, date(2024, 6, 1)
        )

        assert alice.id in effective
        assert effective[alice.id].effective_fraction == Decimal("1.0")
        assert family_trust.id in effective
        assert effective[family_trust.id].effective_fraction == Decimal("0.5")

    def test_compute_effective_ownership_chain(
        self,
        ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        family_trust: Entity,
        holding_llc: Entity,
    ) -> None:
        ownership1 = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership2 = EntityOwnership(
            owner_entity_id=family_trust.id,
            owned_entity_id=holding_llc.id,
            ownership_fraction=Decimal("0.8"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership1)
        ownership_repo.add(ownership2)

        effective = ownership_service.compute_effective_ownership(
            alice.id, date(2024, 6, 1)
        )

        assert alice.id in effective
        assert effective[alice.id].effective_fraction == Decimal("1.0")
        assert family_trust.id in effective
        assert effective[family_trust.id].effective_fraction == Decimal("0.5")
        assert holding_llc.id in effective
        assert effective[holding_llc.id].effective_fraction == Decimal("0.4")

    def test_compute_effective_ownership_diamond(
        self,
        ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        entity_repo: SQLiteEntityRepository,
    ) -> None:
        root = Entity(name="Diamond Root", entity_type=EntityType.INDIVIDUAL)
        left = Entity(name="Diamond Left", entity_type=EntityType.TRUST)
        right = Entity(name="Diamond Right", entity_type=EntityType.TRUST)
        bottom = Entity(name="Diamond Bottom", entity_type=EntityType.LLC)
        entity_repo.add(root)
        entity_repo.add(left)
        entity_repo.add(right)
        entity_repo.add(bottom)

        ownership_repo.add(
            EntityOwnership(
                owner_entity_id=root.id,
                owned_entity_id=left.id,
                ownership_fraction=Decimal("0.5"),
                effective_start_date=date(2024, 1, 1),
            )
        )
        ownership_repo.add(
            EntityOwnership(
                owner_entity_id=root.id,
                owned_entity_id=right.id,
                ownership_fraction=Decimal("0.5"),
                effective_start_date=date(2024, 1, 1),
            )
        )
        ownership_repo.add(
            EntityOwnership(
                owner_entity_id=left.id,
                owned_entity_id=bottom.id,
                ownership_fraction=Decimal("0.5"),
                effective_start_date=date(2024, 1, 1),
            )
        )
        ownership_repo.add(
            EntityOwnership(
                owner_entity_id=right.id,
                owned_entity_id=bottom.id,
                ownership_fraction=Decimal("0.5"),
                effective_start_date=date(2024, 1, 1),
            )
        )

        effective = ownership_service.compute_effective_ownership(
            root.id, date(2024, 6, 1)
        )

        assert root.id in effective
        assert effective[root.id].effective_fraction == Decimal("1.0")
        assert left.id in effective
        assert effective[left.id].effective_fraction == Decimal("0.5")
        assert right.id in effective
        assert effective[right.id].effective_fraction == Decimal("0.5")
        assert bottom.id in effective
        assert effective[bottom.id].effective_fraction == Decimal("0.5")

    def test_list_household_roots(
        self,
        ownership_service: OwnershipGraphService,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
    ) -> None:
        household = Household(name="Smith Family")
        household_repo.add(household)

        alice = Entity(name="Alice Smith Root", entity_type=EntityType.INDIVIDUAL)
        bob = Entity(name="Bob Smith Root", entity_type=EntityType.INDIVIDUAL)
        trust = Entity(name="Smith Trust Root", entity_type=EntityType.TRUST)
        entity_repo.add(alice)
        entity_repo.add(bob)
        entity_repo.add(trust)

        member_alice = HouseholdMember(
            household_id=household.id,
            entity_id=alice.id,
            role="client",
            effective_start_date=date(2024, 1, 1),
        )
        member_bob = HouseholdMember(
            household_id=household.id,
            entity_id=bob.id,
            role="client",
            effective_start_date=date(2024, 1, 1),
        )
        member_trust = HouseholdMember(
            household_id=household.id,
            entity_id=trust.id,
            role="entity",
            effective_start_date=date(2024, 1, 1),
        )
        household_repo.add_member(member_alice)
        household_repo.add_member(member_bob)
        household_repo.add_member(member_trust)

        roots = ownership_service.list_household_roots(household.id, date(2024, 6, 1))

        assert len(roots) == 2
        assert alice.id in roots
        assert bob.id in roots
        assert trust.id not in roots

    def test_get_all_owned_entities(
        self,
        ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        family_trust: Entity,
        holding_llc: Entity,
    ) -> None:
        ownership1 = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership2 = EntityOwnership(
            owner_entity_id=family_trust.id,
            owned_entity_id=holding_llc.id,
            ownership_fraction=Decimal("1.0"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership1)
        ownership_repo.add(ownership2)

        owned = ownership_service.get_all_owned_entities(alice.id, date(2024, 6, 1))

        assert alice.id in owned
        assert family_trust.id in owned
        assert holding_llc.id in owned

    def test_get_ownership_chain(
        self,
        ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        family_trust: Entity,
        holding_llc: Entity,
    ) -> None:
        ownership1 = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership2 = EntityOwnership(
            owner_entity_id=family_trust.id,
            owned_entity_id=holding_llc.id,
            ownership_fraction=Decimal("1.0"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership1)
        ownership_repo.add(ownership2)

        chain = ownership_service.get_ownership_chain(
            alice.id, holding_llc.id, date(2024, 6, 1)
        )

        assert chain is not None
        assert len(chain) == 2
        assert chain[0].owner_entity_id == alice.id
        assert chain[0].owned_entity_id == family_trust.id
        assert chain[1].owner_entity_id == family_trust.id
        assert chain[1].owned_entity_id == holding_llc.id

    def test_get_ownership_chain_not_found(
        self,
        ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        alice: Entity,
        bob: Entity,
        family_trust: Entity,
    ) -> None:
        ownership = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=family_trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership)

        chain = ownership_service.get_ownership_chain(
            alice.id, bob.id, date(2024, 6, 1)
        )
        assert chain is None


class TestLookThroughReports:
    def test_household_rollup_no_double_counting(
        self,
        full_ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
        account_repo: SQLiteAccountRepository,
        transaction_repo: SQLiteTransactionRepository,
    ) -> None:
        household = Household(name="Smith Family Rollup")
        household_repo.add(household)

        alice = Entity(name="Alice Rollup", entity_type=EntityType.INDIVIDUAL)
        bob = Entity(name="Bob Rollup", entity_type=EntityType.INDIVIDUAL)
        trust = Entity(name="Smith Trust Rollup", entity_type=EntityType.TRUST)
        entity_repo.add(alice)
        entity_repo.add(bob)
        entity_repo.add(trust)

        member_alice = HouseholdMember(
            household_id=household.id,
            entity_id=alice.id,
            role="client",
            effective_start_date=date(2024, 1, 1),
        )
        member_bob = HouseholdMember(
            household_id=household.id,
            entity_id=bob.id,
            role="client",
            effective_start_date=date(2024, 1, 1),
        )
        member_trust = HouseholdMember(
            household_id=household.id,
            entity_id=trust.id,
            role="entity",
            effective_start_date=date(2024, 1, 1),
        )
        household_repo.add_member(member_alice)
        household_repo.add_member(member_bob)
        household_repo.add_member(member_trust)

        ownership_alice = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_bob = EntityOwnership(
            owner_entity_id=bob.id,
            owned_entity_id=trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership_alice)
        ownership_repo.add(ownership_bob)

        alice_checking = Account(
            name="Alice Checking Rollup",
            entity_id=alice.id,
            account_type=AccountType.ASSET,
        )
        bob_checking = Account(
            name="Bob Checking Rollup",
            entity_id=bob.id,
            account_type=AccountType.ASSET,
        )
        trust_brokerage = Account(
            name="Trust Brokerage Rollup",
            entity_id=trust.id,
            account_type=AccountType.ASSET,
        )
        account_repo.add(alice_checking)
        account_repo.add(bob_checking)
        account_repo.add(trust_brokerage)

        txn_alice = Transaction(
            transaction_date=date(2024, 1, 15),
            entries=[
                Entry(
                    account_id=alice_checking.id,
                    debit_amount=Money(Decimal("10000"), "USD"),
                )
            ],
        )
        txn_bob = Transaction(
            transaction_date=date(2024, 1, 15),
            entries=[
                Entry(
                    account_id=bob_checking.id,
                    debit_amount=Money(Decimal("20000"), "USD"),
                )
            ],
        )
        txn_trust = Transaction(
            transaction_date=date(2024, 1, 15),
            entries=[
                Entry(
                    account_id=trust_brokerage.id,
                    debit_amount=Money(Decimal("100000"), "USD"),
                )
            ],
        )
        transaction_repo.add(txn_alice)
        transaction_repo.add(txn_bob)
        transaction_repo.add(txn_trust)

        result = full_ownership_service.household_look_through_net_worth(
            household.id, date(2024, 6, 1)
        )

        assert result["net_worth"] == Decimal("130000")

    def test_beneficial_owner_look_through(
        self,
        full_ownership_service: OwnershipGraphService,
        ownership_repo: SQLiteEntityOwnershipRepository,
        entity_repo: SQLiteEntityRepository,
        account_repo: SQLiteAccountRepository,
        transaction_repo: SQLiteTransactionRepository,
    ) -> None:
        alice = Entity(name="Alice LookThrough", entity_type=EntityType.INDIVIDUAL)
        trust = Entity(name="Smith Trust LookThrough", entity_type=EntityType.TRUST)
        llc = Entity(name="Smith LLC LookThrough", entity_type=EntityType.LLC)
        entity_repo.add(alice)
        entity_repo.add(trust)
        entity_repo.add(llc)

        ownership1 = EntityOwnership(
            owner_entity_id=alice.id,
            owned_entity_id=trust.id,
            ownership_fraction=Decimal("0.5"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership2 = EntityOwnership(
            owner_entity_id=trust.id,
            owned_entity_id=llc.id,
            ownership_fraction=Decimal("1.0"),
            effective_start_date=date(2024, 1, 1),
        )
        ownership_repo.add(ownership1)
        ownership_repo.add(ownership2)

        alice_checking = Account(
            name="Alice Checking LookThrough",
            entity_id=alice.id,
            account_type=AccountType.ASSET,
        )
        trust_brokerage = Account(
            name="Trust Brokerage LookThrough",
            entity_id=trust.id,
            account_type=AccountType.ASSET,
        )
        llc_account = Account(
            name="LLC Account LookThrough",
            entity_id=llc.id,
            account_type=AccountType.ASSET,
        )
        account_repo.add(alice_checking)
        account_repo.add(trust_brokerage)
        account_repo.add(llc_account)

        txn_alice = Transaction(
            transaction_date=date(2024, 1, 15),
            entries=[
                Entry(
                    account_id=alice_checking.id,
                    debit_amount=Money(Decimal("10000"), "USD"),
                )
            ],
        )
        txn_trust = Transaction(
            transaction_date=date(2024, 1, 15),
            entries=[
                Entry(
                    account_id=trust_brokerage.id,
                    debit_amount=Money(Decimal("20000"), "USD"),
                )
            ],
        )
        txn_llc = Transaction(
            transaction_date=date(2024, 1, 15),
            entries=[
                Entry(
                    account_id=llc_account.id,
                    debit_amount=Money(Decimal("40000"), "USD"),
                )
            ],
        )
        transaction_repo.add(txn_alice)
        transaction_repo.add(txn_trust)
        transaction_repo.add(txn_llc)

        result = full_ownership_service.beneficial_owner_look_through_net_worth(
            alice.id, date(2024, 6, 1)
        )

        expected = (
            Decimal("10000")
            + Decimal("20000") * Decimal("0.5")
            + Decimal("40000") * Decimal("0.5")
        )
        assert result["net_worth"] == expected
