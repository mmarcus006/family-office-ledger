"""Audit trail service for tracking changes to entities."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from typing import Any
from uuid import UUID

from family_office_ledger.domain.audit import (
    AuditAction,
    AuditEntityType,
    AuditEntry,
    AuditLogSummary,
)
from family_office_ledger.repositories.sqlite import SQLiteDatabase


class AuditService:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._db = database
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                action TEXT NOT NULL,
                user_id TEXT,
                timestamp TEXT NOT NULL,
                old_values TEXT,
                new_values TEXT,
                change_summary TEXT NOT NULL DEFAULT '',
                ip_address TEXT,
                user_agent TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_log_entity_type ON audit_log(entity_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_log_entity_id ON audit_log(entity_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action)"
        )
        conn.commit()

    def log_create(
        self,
        entity_type: AuditEntityType,
        entity_id: UUID,
        new_values: dict[str, Any],
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            entity_type=entity_type,
            entity_id=entity_id,
            action=AuditAction.CREATE,
            user_id=user_id,
            old_values=None,
            new_values=new_values,
            change_summary=f"Created {entity_type.value}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._save_entry(entry)
        return entry

    def log_update(
        self,
        entity_type: AuditEntityType,
        entity_id: UUID,
        old_values: dict[str, Any],
        new_values: dict[str, Any],
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditEntry:
        changed_fields = self._get_changed_fields(old_values, new_values)
        change_summary = (
            f"Updated {entity_type.value}: {', '.join(changed_fields)}"
            if changed_fields
            else f"Updated {entity_type.value}"
        )

        entry = AuditEntry(
            entity_type=entity_type,
            entity_id=entity_id,
            action=AuditAction.UPDATE,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
            change_summary=change_summary,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._save_entry(entry)
        return entry

    def log_delete(
        self,
        entity_type: AuditEntityType,
        entity_id: UUID,
        old_values: dict[str, Any],
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            entity_type=entity_type,
            entity_id=entity_id,
            action=AuditAction.DELETE,
            user_id=user_id,
            old_values=old_values,
            new_values=None,
            change_summary=f"Deleted {entity_type.value}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._save_entry(entry)
        return entry

    def _save_entry(self, entry: AuditEntry) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO audit_log (
                id, entity_type, entity_id, action, user_id, timestamp,
                old_values, new_values, change_summary, ip_address, user_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(entry.id),
                entry.entity_type.value,
                str(entry.entity_id),
                entry.action.value,
                str(entry.user_id) if entry.user_id else None,
                entry.timestamp.isoformat(),
                json.dumps(entry.old_values) if entry.old_values else None,
                json.dumps(entry.new_values) if entry.new_values else None,
                entry.change_summary,
                entry.ip_address,
                entry.user_agent,
            ),
        )
        conn.commit()

    def _get_changed_fields(
        self, old_values: dict[str, Any], new_values: dict[str, Any]
    ) -> list[str]:
        changed = []
        all_keys = set(old_values.keys()) | set(new_values.keys())
        for key in all_keys:
            if old_values.get(key) != new_values.get(key):
                changed.append(key)
        return sorted(changed)

    def get_entry(self, entry_id: UUID) -> AuditEntry | None:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM audit_log WHERE id = ?", (str(entry_id),)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_entry(row)

    def list_by_entity(
        self,
        entity_type: AuditEntityType,
        entity_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        conn = self._db.get_connection()
        rows = conn.execute(
            """
            SELECT * FROM audit_log
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (entity_type.value, str(entity_id), limit, offset),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def list_by_entity_type(
        self,
        entity_type: AuditEntityType,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        conn = self._db.get_connection()

        query = "SELECT * FROM audit_log WHERE entity_type = ?"
        params: list[Any] = [entity_type.value]

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND timestamp < ?"
            params.append(
                (
                    datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
                ).isoformat()
            )

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def list_by_action(
        self,
        action: AuditAction,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        conn = self._db.get_connection()

        query = "SELECT * FROM audit_log WHERE action = ?"
        params: list[Any] = [action.value]

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND timestamp < ?"
            params.append(
                (
                    datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
                ).isoformat()
            )

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def list_recent(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        conn = self._db.get_connection()
        rows = conn.execute(
            """
            SELECT * FROM audit_log
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_summary(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> AuditLogSummary:
        conn = self._db.get_connection()

        query_base = "SELECT * FROM audit_log WHERE 1=1"
        params: list[Any] = []

        if start_date:
            query_base += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query_base += " AND timestamp < ?"
            params.append(
                (
                    datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
                ).isoformat()
            )

        count_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM ({query_base})", params
        ).fetchone()
        total_entries = count_row["cnt"]

        action_rows = conn.execute(
            f"""
            SELECT action, COUNT(*) as cnt
            FROM ({query_base})
            GROUP BY action
            """,
            params,
        ).fetchall()
        entries_by_action = {
            AuditAction(row["action"]): row["cnt"] for row in action_rows
        }

        type_rows = conn.execute(
            f"""
            SELECT entity_type, COUNT(*) as cnt
            FROM ({query_base})
            GROUP BY entity_type
            """,
            params,
        ).fetchall()
        entries_by_entity_type = {
            AuditEntityType(row["entity_type"]): row["cnt"] for row in type_rows
        }

        date_row = conn.execute(
            f"""
            SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest
            FROM ({query_base})
            """,
            params,
        ).fetchone()

        oldest = None
        newest = None
        if date_row["oldest"]:
            oldest = datetime.fromisoformat(date_row["oldest"])
        if date_row["newest"]:
            newest = datetime.fromisoformat(date_row["newest"])

        return AuditLogSummary(
            total_entries=total_entries,
            entries_by_action=entries_by_action,
            entries_by_entity_type=entries_by_entity_type,
            oldest_entry=oldest,
            newest_entry=newest,
        )

    def _row_to_entry(self, row: sqlite3.Row) -> AuditEntry:
        old_values = None
        if row["old_values"]:
            old_values = json.loads(row["old_values"])

        new_values = None
        if row["new_values"]:
            new_values = json.loads(row["new_values"])

        user_id = None
        if row["user_id"]:
            user_id = UUID(row["user_id"])

        return AuditEntry(
            id=UUID(row["id"]),
            entity_type=AuditEntityType(row["entity_type"]),
            entity_id=UUID(row["entity_id"]),
            action=AuditAction(row["action"]),
            user_id=user_id,
            timestamp=datetime.fromisoformat(row["timestamp"]),
            old_values=old_values,
            new_values=new_values,
            change_summary=row["change_summary"],
            ip_address=row["ip_address"],
            user_agent=row["user_agent"],
        )
