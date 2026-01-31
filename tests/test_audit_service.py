"""Tests for audit trail service."""

from uuid import uuid4

import pytest

from family_office_ledger.domain.audit import (
    AuditAction,
    AuditEntityType,
)
from family_office_ledger.repositories.sqlite import SQLiteDatabase
from family_office_ledger.services.audit import AuditService


@pytest.fixture
def db() -> SQLiteDatabase:
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database


@pytest.fixture
def service(db: SQLiteDatabase) -> AuditService:
    return AuditService(db)


class TestAuditServiceLogCreate:
    def test_logs_create_action(self, service: AuditService):
        entity_id = uuid4()
        new_values = {"name": "Test Entity", "type": "llc"}

        entry = service.log_create(
            entity_type=AuditEntityType.ENTITY,
            entity_id=entity_id,
            new_values=new_values,
        )

        assert entry.action == AuditAction.CREATE
        assert entry.entity_type == AuditEntityType.ENTITY
        assert entry.entity_id == entity_id
        assert entry.new_values == new_values
        assert entry.old_values is None
        assert "Created" in entry.change_summary

    def test_includes_user_and_metadata(self, service: AuditService):
        user_id = uuid4()
        entity_id = uuid4()

        entry = service.log_create(
            entity_type=AuditEntityType.ACCOUNT,
            entity_id=entity_id,
            new_values={"name": "Checking"},
            user_id=user_id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert entry.user_id == user_id
        assert entry.ip_address == "192.168.1.1"
        assert entry.user_agent == "Mozilla/5.0"


class TestAuditServiceLogUpdate:
    def test_logs_update_with_changes(self, service: AuditService):
        entity_id = uuid4()
        old_values = {"name": "Old Name", "status": "active"}
        new_values = {"name": "New Name", "status": "active"}

        entry = service.log_update(
            entity_type=AuditEntityType.ENTITY,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
        )

        assert entry.action == AuditAction.UPDATE
        assert entry.old_values == old_values
        assert entry.new_values == new_values
        assert "name" in entry.change_summary

    def test_detects_changed_fields(self, service: AuditService):
        entity_id = uuid4()
        old_values = {"a": 1, "b": 2, "c": 3}
        new_values = {"a": 1, "b": 5, "c": 3}

        entry = service.log_update(
            entity_type=AuditEntityType.ACCOUNT,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
        )

        assert entry.changed_fields == ["b"]


class TestAuditServiceLogDelete:
    def test_logs_delete_action(self, service: AuditService):
        entity_id = uuid4()
        old_values = {"name": "Deleted Entity"}

        entry = service.log_delete(
            entity_type=AuditEntityType.ENTITY,
            entity_id=entity_id,
            old_values=old_values,
        )

        assert entry.action == AuditAction.DELETE
        assert entry.old_values == old_values
        assert entry.new_values is None
        assert "Deleted" in entry.change_summary


class TestAuditServiceQueries:
    def test_get_entry_by_id(self, service: AuditService):
        entity_id = uuid4()
        entry = service.log_create(
            entity_type=AuditEntityType.SECURITY,
            entity_id=entity_id,
            new_values={"symbol": "AAPL"},
        )

        retrieved = service.get_entry(entry.id)

        assert retrieved is not None
        assert retrieved.id == entry.id
        assert retrieved.entity_id == entity_id

    def test_get_nonexistent_entry(self, service: AuditService):
        entry = service.get_entry(uuid4())
        assert entry is None

    def test_list_by_entity(self, service: AuditService):
        entity_id = uuid4()

        service.log_create(
            entity_type=AuditEntityType.ENTITY,
            entity_id=entity_id,
            new_values={"name": "Test"},
        )
        service.log_update(
            entity_type=AuditEntityType.ENTITY,
            entity_id=entity_id,
            old_values={"name": "Test"},
            new_values={"name": "Updated"},
        )

        entries = service.list_by_entity(AuditEntityType.ENTITY, entity_id)

        assert len(entries) == 2
        assert entries[0].action == AuditAction.UPDATE
        assert entries[1].action == AuditAction.CREATE

    def test_list_by_entity_type(self, service: AuditService):
        service.log_create(
            entity_type=AuditEntityType.ENTITY,
            entity_id=uuid4(),
            new_values={},
        )
        service.log_create(
            entity_type=AuditEntityType.ACCOUNT,
            entity_id=uuid4(),
            new_values={},
        )
        service.log_create(
            entity_type=AuditEntityType.ENTITY,
            entity_id=uuid4(),
            new_values={},
        )

        entries = service.list_by_entity_type(AuditEntityType.ENTITY)

        assert len(entries) == 2

    def test_list_by_action(self, service: AuditService):
        entity_id = uuid4()

        service.log_create(
            entity_type=AuditEntityType.ENTITY,
            entity_id=entity_id,
            new_values={},
        )
        service.log_update(
            entity_type=AuditEntityType.ENTITY,
            entity_id=entity_id,
            old_values={},
            new_values={},
        )
        service.log_delete(
            entity_type=AuditEntityType.ENTITY,
            entity_id=entity_id,
            old_values={},
        )

        create_entries = service.list_by_action(AuditAction.CREATE)
        update_entries = service.list_by_action(AuditAction.UPDATE)
        delete_entries = service.list_by_action(AuditAction.DELETE)

        assert len(create_entries) == 1
        assert len(update_entries) == 1
        assert len(delete_entries) == 1

    def test_list_recent(self, service: AuditService):
        for i in range(5):
            service.log_create(
                entity_type=AuditEntityType.ENTITY,
                entity_id=uuid4(),
                new_values={"index": i},
            )

        entries = service.list_recent(limit=3)

        assert len(entries) == 3


class TestAuditServiceSummary:
    def test_summary_counts(self, service: AuditService):
        for _ in range(3):
            service.log_create(
                entity_type=AuditEntityType.ENTITY,
                entity_id=uuid4(),
                new_values={},
            )
        for _ in range(2):
            service.log_update(
                entity_type=AuditEntityType.ACCOUNT,
                entity_id=uuid4(),
                old_values={},
                new_values={},
            )
        service.log_delete(
            entity_type=AuditEntityType.SECURITY,
            entity_id=uuid4(),
            old_values={},
        )

        summary = service.get_summary()

        assert summary.total_entries == 6
        assert summary.entries_by_action[AuditAction.CREATE] == 3
        assert summary.entries_by_action[AuditAction.UPDATE] == 2
        assert summary.entries_by_action[AuditAction.DELETE] == 1
        assert summary.entries_by_entity_type[AuditEntityType.ENTITY] == 3
        assert summary.entries_by_entity_type[AuditEntityType.ACCOUNT] == 2
        assert summary.entries_by_entity_type[AuditEntityType.SECURITY] == 1

    def test_empty_summary(self, service: AuditService):
        summary = service.get_summary()

        assert summary.total_entries == 0
        assert summary.oldest_entry is None
        assert summary.newest_entry is None
