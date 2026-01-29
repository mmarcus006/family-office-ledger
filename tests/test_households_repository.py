from datetime import date
from uuid import uuid4

import pytest

from family_office_ledger.domain.entities import Entity
from family_office_ledger.domain.households import Household, HouseholdMember
from family_office_ledger.domain.value_objects import EntityType
from family_office_ledger.repositories.sqlite import (
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteHouseholdRepository,
)


@pytest.fixture
def db() -> SQLiteDatabase:
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database


@pytest.fixture
def household_repo(db: SQLiteDatabase) -> SQLiteHouseholdRepository:
    return SQLiteHouseholdRepository(db)


@pytest.fixture
def entity_repo(db: SQLiteDatabase) -> SQLiteEntityRepository:
    return SQLiteEntityRepository(db)


class TestSQLiteHouseholdRepository:
    def test_add_and_get_household(self, household_repo: SQLiteHouseholdRepository):
        household = Household(name="Smith Family")

        household_repo.add(household)
        retrieved = household_repo.get(household.id)

        assert retrieved is not None
        assert retrieved.id == household.id
        assert retrieved.name == "Smith Family"
        assert retrieved.primary_contact_entity_id is None
        assert retrieved.is_active is True

    def test_get_nonexistent_household_returns_none(
        self, household_repo: SQLiteHouseholdRepository
    ):
        result = household_repo.get(uuid4())
        assert result is None

    def test_get_by_name(self, household_repo: SQLiteHouseholdRepository):
        household = Household(name="Johnson Family")
        household_repo.add(household)

        retrieved = household_repo.get_by_name("Johnson Family")

        assert retrieved is not None
        assert retrieved.name == "Johnson Family"

    def test_get_by_name_not_found(self, household_repo: SQLiteHouseholdRepository):
        result = household_repo.get_by_name("Nonexistent")
        assert result is None

    def test_list_all_households(self, household_repo: SQLiteHouseholdRepository):
        household1 = Household(name="Family A")
        household2 = Household(name="Family B")
        household_repo.add(household1)
        household_repo.add(household2)

        households = list(household_repo.list_all())

        assert len(households) == 2
        names = {h.name for h in households}
        assert names == {"Family A", "Family B"}

    def test_list_active_households(self, household_repo: SQLiteHouseholdRepository):
        household1 = Household(name="Active Family")
        household2 = Household(name="Inactive Family", is_active=False)
        household_repo.add(household1)
        household_repo.add(household2)

        active = list(household_repo.list_active())

        assert len(active) == 1
        assert active[0].name == "Active Family"

    def test_update_household(self, household_repo: SQLiteHouseholdRepository):
        household = Household(name="Old Name")
        household_repo.add(household)

        updated = Household(
            name="New Name",
            id=household.id,
            is_active=False,
        )
        household_repo.update(updated)

        retrieved = household_repo.get(household.id)
        assert retrieved is not None
        assert retrieved.name == "New Name"
        assert retrieved.is_active is False

    def test_delete_household(self, household_repo: SQLiteHouseholdRepository):
        household = Household(name="To Delete")
        household_repo.add(household)

        household_repo.delete(household.id)

        assert household_repo.get(household.id) is None

    def test_household_preserves_timestamps(
        self, household_repo: SQLiteHouseholdRepository
    ):
        household = Household(name="Test")
        original_created = household.created_at
        original_updated = household.updated_at

        household_repo.add(household)
        retrieved = household_repo.get(household.id)

        assert retrieved is not None
        assert retrieved.created_at == original_created
        assert retrieved.updated_at == original_updated

    def test_household_with_primary_contact(
        self,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
    ):
        entity = Entity(name="John Smith", entity_type=EntityType.INDIVIDUAL)
        entity_repo.add(entity)

        household = Household(
            name="Smith Family",
            primary_contact_entity_id=entity.id,
        )
        household_repo.add(household)

        retrieved = household_repo.get(household.id)
        assert retrieved is not None
        assert retrieved.primary_contact_entity_id == entity.id

    def test_update_household_primary_contact(
        self,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
    ):
        entity1 = Entity(name="Jane Smith", entity_type=EntityType.INDIVIDUAL)
        entity2 = Entity(name="John Smith", entity_type=EntityType.INDIVIDUAL)
        entity_repo.add(entity1)
        entity_repo.add(entity2)

        household = Household(
            name="Smith Family",
            primary_contact_entity_id=entity1.id,
        )
        household_repo.add(household)

        updated = Household(
            name="Smith Family",
            id=household.id,
            primary_contact_entity_id=entity2.id,
        )
        household_repo.update(updated)

        retrieved = household_repo.get(household.id)
        assert retrieved is not None
        assert retrieved.primary_contact_entity_id == entity2.id

    def test_clear_household_primary_contact(
        self,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
    ):
        entity = Entity(name="Jane Smith", entity_type=EntityType.INDIVIDUAL)
        entity_repo.add(entity)

        household = Household(
            name="Smith Family",
            primary_contact_entity_id=entity.id,
        )
        household_repo.add(household)

        updated = Household(
            name="Smith Family",
            id=household.id,
            primary_contact_entity_id=None,
        )
        household_repo.update(updated)

        retrieved = household_repo.get(household.id)
        assert retrieved is not None
        assert retrieved.primary_contact_entity_id is None


class TestSQLiteHouseholdMemberRepository:
    def test_add_member(
        self,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
    ):
        entity = Entity(name="John Smith", entity_type=EntityType.INDIVIDUAL)
        entity_repo.add(entity)
        household = Household(name="Smith Family")
        household_repo.add(household)

        member = HouseholdMember(
            household_id=household.id,
            entity_id=entity.id,
            role="client",
            display_name="John",
        )
        household_repo.add_member(member)

        retrieved = household_repo.get_member(member.id)
        assert retrieved is not None
        assert retrieved.id == member.id
        assert retrieved.household_id == household.id
        assert retrieved.entity_id == entity.id
        assert retrieved.role == "client"
        assert retrieved.display_name == "John"

    def test_list_members(
        self,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
    ):
        entity1 = Entity(name="Jane Smith", entity_type=EntityType.INDIVIDUAL)
        entity2 = Entity(name="John Smith", entity_type=EntityType.INDIVIDUAL)
        entity_repo.add(entity1)
        entity_repo.add(entity2)
        household = Household(name="Smith Family")
        household_repo.add(household)

        member1 = HouseholdMember(household_id=household.id, entity_id=entity1.id)
        member2 = HouseholdMember(household_id=household.id, entity_id=entity2.id)
        household_repo.add_member(member1)
        household_repo.add_member(member2)

        members = list(household_repo.list_members(household.id))

        assert len(members) == 2
        entity_ids = {m.entity_id for m in members}
        assert entity_ids == {entity1.id, entity2.id}

    def test_list_members_as_of_date(
        self,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
    ):
        entity1 = Entity(name="Current Member", entity_type=EntityType.INDIVIDUAL)
        entity2 = Entity(name="Past Member", entity_type=EntityType.INDIVIDUAL)
        entity3 = Entity(name="Future Member", entity_type=EntityType.INDIVIDUAL)
        entity_repo.add(entity1)
        entity_repo.add(entity2)
        entity_repo.add(entity3)
        household = Household(name="Test Household")
        household_repo.add(household)

        current_member = HouseholdMember(
            household_id=household.id,
            entity_id=entity1.id,
            effective_start_date=date(2020, 1, 1),
        )
        past_member = HouseholdMember(
            household_id=household.id,
            entity_id=entity2.id,
            effective_start_date=date(2018, 1, 1),
            effective_end_date=date(2019, 12, 31),
        )
        future_member = HouseholdMember(
            household_id=household.id,
            entity_id=entity3.id,
            effective_start_date=date(2025, 1, 1),
        )
        household_repo.add_member(current_member)
        household_repo.add_member(past_member)
        household_repo.add_member(future_member)

        members_2024 = list(
            household_repo.list_members(household.id, date(2024, 6, 15))
        )
        assert len(members_2024) == 1
        assert members_2024[0].entity_id == entity1.id

        members_2019 = list(
            household_repo.list_members(household.id, date(2019, 6, 15))
        )
        assert len(members_2019) == 1
        assert members_2019[0].entity_id == entity2.id

    def test_list_households_for_entity(
        self,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
    ):
        entity = Entity(name="Multi-Household Entity", entity_type=EntityType.LLC)
        entity_repo.add(entity)
        household1 = Household(name="Family A")
        household2 = Household(name="Family B")
        household_repo.add(household1)
        household_repo.add(household2)

        member1 = HouseholdMember(household_id=household1.id, entity_id=entity.id)
        member2 = HouseholdMember(household_id=household2.id, entity_id=entity.id)
        household_repo.add_member(member1)
        household_repo.add_member(member2)

        memberships = list(household_repo.list_households_for_entity(entity.id))

        assert len(memberships) == 2
        household_ids = {m.household_id for m in memberships}
        assert household_ids == {household1.id, household2.id}

    def test_remove_member(
        self,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
    ):
        entity = Entity(name="To Remove", entity_type=EntityType.INDIVIDUAL)
        entity_repo.add(entity)
        household = Household(name="Test Household")
        household_repo.add(household)

        member = HouseholdMember(household_id=household.id, entity_id=entity.id)
        household_repo.add_member(member)

        household_repo.remove_member(member.id)

        assert household_repo.get_member(member.id) is None
        assert list(household_repo.list_members(household.id)) == []

    def test_update_member(
        self,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
    ):
        entity = Entity(name="Update Test", entity_type=EntityType.INDIVIDUAL)
        entity_repo.add(entity)
        household = Household(name="Test Household")
        household_repo.add(household)

        member = HouseholdMember(
            household_id=household.id,
            entity_id=entity.id,
            role="client",
        )
        household_repo.add_member(member)

        updated = HouseholdMember(
            household_id=member.household_id,
            entity_id=member.entity_id,
            id=member.id,
            role="trustee",
            display_name="New Display Name",
        )
        household_repo.update_member(updated)

        retrieved = household_repo.get_member(member.id)
        assert retrieved is not None
        assert retrieved.role == "trustee"
        assert retrieved.display_name == "New Display Name"

    def test_member_preserves_timestamps(
        self,
        household_repo: SQLiteHouseholdRepository,
        entity_repo: SQLiteEntityRepository,
    ):
        entity = Entity(name="Timestamp Test", entity_type=EntityType.INDIVIDUAL)
        entity_repo.add(entity)
        household = Household(name="Test Household")
        household_repo.add(household)

        member = HouseholdMember(household_id=household.id, entity_id=entity.id)
        original_created = member.created_at

        household_repo.add_member(member)
        retrieved = household_repo.get_member(member.id)

        assert retrieved is not None
        assert retrieved.created_at == original_created
