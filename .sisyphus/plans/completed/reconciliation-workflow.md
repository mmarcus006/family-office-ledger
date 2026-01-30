# Reconciliation Workflow

## TL;DR

> **Quick Summary**: Add interactive reconciliation workflow with session-based matching, database persistence, CLI commands, and REST API endpoints. Users can create sessions, review proposed matches, and confirm/reject/skip each match.
> 
> **Deliverables**:
> - ReconciliationSession domain model with match state tracking
> - ReconciliationSessionRepository (SQLite + Postgres)
> - Enhanced ReconciliationService with session support
> - REST API endpoints for session management
> - CLI commands: `fol reconcile create/list/confirm/reject/skip/close/summary`
> 
> **Estimated Effort**: Large (3-5 days)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Domain Model → Repository → Service → API/CLI

---

## Context

### Original Request
Build a full reconciliation workflow suite for the family office ledger:
1. Interactive matching (priority 1)
2. Post-ingestion verification (priority 2)
3. Bank statement reconciliation (priority 3)

### Interview Summary
**Key Discussions**:
- Interface: Both CLI and REST API
- Test strategy: TDD (write failing tests first)
- Match actions: Confirm / Reject / Skip (Edit removed from v1)
- Session lifecycle: Auto-close when done + manual close
- Concurrency: One pending session per account (409 Conflict)

**Research Findings**:
- Existing ReconciliationServiceImpl (466 lines) has import, match, confirm methods
- No API endpoints or CLI commands exist
- Session state not persisted (stateless operations)

### Metis Review
**Identified Gaps** (addressed):
- Session lifecycle undefined → Auto-close + manual close
- Edit action ambiguous → Removed from v1
- Concurrent sessions unclear → One per account
- Acceptance criteria missing → Executable curl/CLI commands added
- Scale concerns → Pagination for large datasets

---

## Work Objectives

### Core Objective
Enable users to interactively reconcile imported bank transactions against ledger entries with full state persistence, reviewable match proposals, and confirmation workflow.

### Concrete Deliverables
- `src/family_office_ledger/domain/reconciliation.py` - New domain models
- `src/family_office_ledger/repositories/interfaces.py` - Repository interface additions
- `src/family_office_ledger/repositories/sqlite.py` - SQLite implementation
- `src/family_office_ledger/repositories/postgres.py` - Postgres implementation
- `src/family_office_ledger/services/reconciliation.py` - Enhanced service
- `src/family_office_ledger/api/routes.py` - New API endpoints
- `src/family_office_ledger/api/schemas.py` - New Pydantic schemas
- `src/family_office_ledger/cli.py` - New reconcile commands
- `tests/test_reconciliation_session.py` - Domain model tests
- `tests/test_reconciliation_session_repository.py` - Repository tests
- `tests/test_reconciliation_workflow.py` - Service workflow tests
- `tests/test_reconciliation_api.py` - API endpoint tests
- `tests/test_reconciliation_cli.py` - CLI command tests

### Definition of Done
- [x] `uv run pytest tests/test_reconciliation_*.py -v` → All tests pass (139 tests)
- [x] `uv run mypy src/` → No NEW type errors (15 pre-existing UI errors unrelated to reconciliation)
- [x] `uv run ruff check .` → No NEW lint errors (pre-existing errors unrelated to reconciliation)
- [x] Manual verification: Create session, list matches, confirm/reject/skip, close session

### Must Have
- ReconciliationSession persists to database
- ReconciliationMatch tracks: imported_data, suggested_ledger_txn_id, confidence_score, status
- Match statuses: pending, confirmed, rejected, skipped
- Session statuses: pending, completed, abandoned
- One pending session per account (409 Conflict)
- **Session completion semantics**:
  - Auto-close triggers when: `pending_count == 0` AND `skipped_count == 0` (all matches are CONFIRMED or REJECTED)
  - SKIPPED matches do NOT trigger auto-close (user can revisit them)
  - On manual close: status = COMPLETED if `pending_count == 0 && skipped_count == 0`, else ABANDONED
- Manual close anytime
- Pagination for match listing

### Must NOT Have (Guardrails)
- NO Edit action (v2)
- NO bulk operations (confirm all)
- NO undo capability (v2)
- NO concurrent sessions for same account
- NO interactive CLI prompts (no `input()` calls)
- NO file contents stored in session (only parsed data)
- NO modification to existing `confirm_match(imported_id, ledger_transaction_id)` signature
- New session-based confirm uses different name: `confirm_session_match(session_id, match_id)`
- NO WebSocket/real-time features

### Implementation Specifications (Required Details)

**Enum Values and Serialization**:
- Enums inherit from `str, Enum` following existing project convention
- `ReconciliationSessionStatus` values: `"pending"`, `"completed"`, `"abandoned"` (lowercase)
- `ReconciliationMatchStatus` values: `"pending"`, `"confirmed"`, `"rejected"`, `"skipped"` (lowercase)
- API responses and database store lowercase string values
- JSON example: `{"status": "pending", "match_status": "confirmed"}`

**Confirm Path Behavior**:
- `confirm_session_match(session_id, match_id)` requires `match.suggested_ledger_txn_id is not None`
- If `suggested_ledger_txn_id is None`: raise `MatchNotFoundError("Cannot confirm unmatched import")`
- User cannot change which ledger transaction to match (Edit removed from v1)
- For unmatched imports: user must reject or skip, then use existing `create_from_import()` via separate flow
- Changing SKIPPED → CONFIRMED is allowed (re-visiting a skipped match)
- Changing SKIPPED → CONFIRMED triggers auto-close check

**Repository Semantics**:
- `ReconciliationSessionRepository.add(session)`: Insert session row + all match rows
- `ReconciliationSessionRepository.get(session_id)`: Load session row + all match rows (eager load)
- `ReconciliationSessionRepository.update(session)`: Update session row + upsert all match rows (full replace)
- Pagination is **in-memory**: `list_matches()` loads full session, then slices matches array
  - For v1 this is acceptable (typical session has <100 matches)
  - Future optimization: add `list_matches_paginated()` repo method with LIMIT/OFFSET
- Total count for pagination comes from `len(session.matches)` filtered by status
- Direct repo instantiation pattern: `SQLiteReconciliationSessionRepository(db)` (NOT `db.reconciliation_session_repo`)

**Amount Serialization in API**:
- `imported_amount` stored as `Decimal` in domain, serialized as string in JSON (e.g., `"100.50"`)
- Matches existing pattern in `routes.py:142-143` where amounts use `str(entry.debit_amount.amount)`

**Imported Transaction Schema and Mapping**:
- Parsers (CSV/OFX) output dicts with keys: `import_id`, `date`, `amount`, `description` (or `memo`)
- See `src/family_office_ledger/services/reconciliation.py:117-123` for expected dict shape
- Mapping to `ReconciliationMatch`:
  - `imported_id` ← `dict["import_id"]` (str, required)
  - `imported_date` ← `dict["date"]` (date, required)
  - `imported_amount` ← `dict["amount"]` (Decimal, required)
  - `imported_description` ← `dict.get("description") or dict.get("memo") or ""` (str, optional)
- **Missing required fields**: If `date` or `amount` is missing/None, SKIP that transaction (do not create match). Add to session summary as exception: `"Skipped import {id}: missing date or amount"`

**Service Method Error/Return Semantics**:
| Method | Not Found Behavior |
|--------|-------------------|
| `get_session(session_id)` | Return `None` |
| `list_matches(session_id, ...)` | Raise `SessionNotFoundError` |
| `confirm_session_match(session_id, match_id)` | Raise `SessionNotFoundError` or `MatchNotFoundError` |
| `reject_session_match(session_id, match_id)` | Raise `SessionNotFoundError` or `MatchNotFoundError` |
| `skip_session_match(session_id, match_id)` | Raise `SessionNotFoundError` or `MatchNotFoundError` |
| `close_session(session_id)` | Raise `SessionNotFoundError` |
| `get_session_summary(session_id)` | Raise `SessionNotFoundError` |
- `MatchNotFoundError` means: match_id not found in session's matches list
- "Cannot confirm unmatched import" uses `MatchNotFoundError("Cannot confirm: no suggested ledger transaction")`

**Session State Transition Side Effects**:
- On `confirm_session_match`:
  - Set `match.status = CONFIRMED`
  - Set `match.actioned_at = datetime.now(UTC)`
  - If auto-close triggers: set `session.status = COMPLETED`, `session.closed_at = datetime.now(UTC)`
- On `reject_session_match`:
  - Set `match.status = REJECTED`
  - Set `match.actioned_at = datetime.now(UTC)`
  - If auto-close triggers: set `session.status = COMPLETED`, `session.closed_at = datetime.now(UTC)`
- On `skip_session_match`:
  - Set `match.status = SKIPPED`
  - Set `match.actioned_at = datetime.now(UTC)`
  - NO auto-close check
- On manual `close_session`:
  - Set `session.closed_at = datetime.now(UTC)`
  - Set `session.status = COMPLETED` if `pending_count == 0 && skipped_count == 0`, else `ABANDONED`
- Re-actioning a SKIPPED match (e.g., SKIPPED → CONFIRMED): `actioned_at` is overwritten with new timestamp

**Match Pagination Ordering**:
- Matches are ordered by `created_at ASC` (oldest first, preserving import file order)
- When persisting: insert matches in import file order; `created_at` is set sequentially
- `list_matches()` returns matches sorted by `created_at ASC`, then applies offset/limit

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (pytest, fixtures in conftest.py)
- **User wants tests**: YES (TDD)
- **Framework**: pytest with existing patterns
- **QA approach**: TDD - RED-GREEN-REFACTOR for each TODO

### TDD Workflow Per Task

Each TODO follows RED-GREEN-REFACTOR:
1. **RED**: Write failing test first
   - Test file created with specific assertions
   - `uv run pytest tests/test_X.py::TestY::test_z -v` → FAIL
2. **GREEN**: Implement minimum code to pass
   - `uv run pytest tests/test_X.py::TestY::test_z -v` → PASS
3. **REFACTOR**: Clean up while keeping green
   - `uv run pytest tests/test_X.py -v` → All PASS

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Domain models (ReconciliationSession, ReconciliationMatch)
└── Task 2: Repository interface (ReconciliationSessionRepository)

Wave 2 (After Wave 1):
├── Task 3: SQLite repository implementation
├── Task 4: Postgres repository implementation
└── Task 5: Service enhancement (ReconciliationServiceImpl)

Wave 3 (After Wave 2):
├── Task 6: API endpoints
├── Task 7: API schemas
└── Task 8: CLI commands

Wave 4 (After Wave 3):
├── Task 9: Integration tests
└── Task 10: Exports and documentation
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3, 4, 5 | 2 |
| 2 | None | 3, 4, 5 | 1 |
| 3 | 1, 2 | 5, 6, 8 | 4 |
| 4 | 1, 2 | 5 | 3 |
| 5 | 1, 2, 3 | 6, 7, 8 | None |
| 6 | 5 | 9 | 7, 8 |
| 7 | 5 | 6 | 8 |
| 8 | 5 | 9 | 6, 7 |
| 9 | 6, 8 | 10 | None |
| 10 | 9 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2 | `delegate_task(category="quick", load_skills=[], run_in_background=true)` |
| 2 | 3, 4, 5 | 3,4 parallel; 5 after 3 completes |
| 3 | 6, 7, 8 | All parallel after 5 completes |
| 4 | 9, 10 | Sequential (9 then 10) |

---

## TODOs

### Task 1: Domain Models (ReconciliationSession, ReconciliationMatch)

- [x] 1. Create ReconciliationSession and ReconciliationMatch domain models

  **What to do**:
  - Create `src/family_office_ledger/domain/reconciliation.py`
  - Define `ReconciliationSessionStatus` enum: `PENDING`, `COMPLETED`, `ABANDONED`
  - Define `ReconciliationMatchStatus` enum: `PENDING`, `CONFIRMED`, `REJECTED`, `SKIPPED`
  - Define `ReconciliationMatch` dataclass with fields:
    - `id: UUID` (default_factory=uuid4)
    - `session_id: UUID`
    - `imported_id: str`
    - `imported_date: date`
    - `imported_amount: Decimal`
    - `imported_description: str` (default="")
    - `suggested_ledger_txn_id: UUID | None` (default=None)
    - `confidence_score: int` (default=0)
    - `status: ReconciliationMatchStatus` (default=PENDING)
    - `actioned_at: datetime | None` (default=None)
    - `created_at: datetime` (default_factory=lambda: datetime.now(UTC))
  - Define `ReconciliationSession` dataclass with fields:
    - `id: UUID` (default_factory=uuid4)
    - `account_id: UUID`
    - `file_name: str`
    - `file_format: str`
    - `status: ReconciliationSessionStatus` (default=PENDING)
    - `matches: list[ReconciliationMatch]` (default_factory=list)
    - `created_at: datetime` (default_factory=lambda: datetime.now(UTC))
    - `closed_at: datetime | None` (default=None)
  - Add property methods:
    - `pending_count`: count of matches with status PENDING
    - `confirmed_count`: count of matches with status CONFIRMED
    - `rejected_count`: count of matches with status REJECTED
    - `skipped_count`: count of matches with status SKIPPED
    - `match_rate`: `confirmed_count / len(matches)` if matches else 0.0 (float, 0.0-1.0)
  - Write TDD tests first in `tests/test_reconciliation_session.py`

  **Must NOT do**:
  - NO mutable default arguments
  - NO storing raw file contents
  - NO methods that modify other domain objects

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file creation with clear patterns to follow
  - **Skills**: `[]`
    - No special skills needed - straightforward Python dataclass work
  - **Skills Evaluated but Omitted**:
    - `git-master`: Not needed until commit time

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Tasks 3, 4, 5
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `src/family_office_ledger/domain/transactions.py:1-50` - Transaction dataclass pattern with UUID id, datetime fields
  - `src/family_office_ledger/domain/value_objects.py:1-100` - Enum definitions (inherit from `str, Enum`)
  - `src/family_office_ledger/domain/entities.py:15-60` - Entity dataclass with property methods

  **API/Type References**:
  - `src/family_office_ledger/services/interfaces.py:31-51` - MatchResult and ReconciliationSummary dataclasses

  **Test References**:
  - `tests/test_entities.py:1-50` - Domain model test patterns
  - `tests/test_transactions.py:1-80` - Transaction dataclass tests

  **Acceptance Criteria**:

  **TDD (tests first):**
  - [x] Test file created: `tests/test_reconciliation_session.py`
  - [x] Tests cover: enum values, dataclass creation, property calculations
  - [x] `uv run pytest tests/test_reconciliation_session.py -v` → PASS after implementation

  **Automated Verification:**
  ```bash
  # Agent runs:
  uv run python -c "
  from family_office_ledger.domain.reconciliation import (
      ReconciliationSession, ReconciliationMatch,
      ReconciliationSessionStatus, ReconciliationMatchStatus
  )
  from uuid import uuid4
  from datetime import date
  from decimal import Decimal

  # Create match
  match = ReconciliationMatch(
      session_id=uuid4(),
      imported_id='txn_001',
      imported_date=date(2026, 1, 15),
      imported_amount=Decimal('100.00'),
      imported_description='Test payment'
  )
  assert match.status == ReconciliationMatchStatus.PENDING
  assert match.confidence_score == 0

  # Create session
  session = ReconciliationSession(
      account_id=uuid4(),
      file_name='test.csv',
      file_format='csv'
  )
  assert session.status == ReconciliationSessionStatus.PENDING
  assert session.pending_count == 0
  print('Domain models OK')
  "
  # Assert: Output contains "Domain models OK"
  # Assert: Exit code 0
  ```

  **Commit**: YES
  - Message: `feat(domain): add ReconciliationSession and ReconciliationMatch models`
  - Files: `src/family_office_ledger/domain/reconciliation.py`, `tests/test_reconciliation_session.py`
  - Pre-commit: `uv run pytest tests/test_reconciliation_session.py -v`

---

### Task 2: Repository Interface

- [x] 2. Add ReconciliationSessionRepository interface

  **What to do**:
  - Edit `src/family_office_ledger/repositories/interfaces.py`
  - Add `ReconciliationSessionRepository` abstract class (ABC) with methods:
    - `add(session: ReconciliationSession) -> None`
    - `get(session_id: UUID) -> ReconciliationSession | None`
    - `get_pending_for_account(account_id: UUID) -> ReconciliationSession | None`
    - `update(session: ReconciliationSession) -> None`
    - `delete(session_id: UUID) -> None`
    - `list_by_account(account_id: UUID) -> Iterable[ReconciliationSession]`
  - Add imports for new domain types

  **Must NOT do**:
  - NO implementation code in interface
  - NO changing existing interface signatures

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Interface additions following existing patterns
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `git-master`: Not needed until commit

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Tasks 3, 4, 5
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `src/family_office_ledger/repositories/interfaces.py:10-70` - EntityRepository and AccountRepository ABC patterns
  - `src/family_office_ledger/repositories/interfaces.py:134-175` - TransactionRepository with date range queries
  - `src/family_office_ledger/repositories/interfaces.py:176-220` - TaxLotRepository with complex queries (wash sale, position-based)

  **Acceptance Criteria**:

  **TDD (tests first):**
  - [x] No separate test needed - interface only
  - [x] Verify with mypy: `uv run mypy src/family_office_ledger/repositories/interfaces.py`

  **Automated Verification:**
  ```bash
  # Agent runs:
  uv run python -c "
  from family_office_ledger.repositories.interfaces import ReconciliationSessionRepository
  from abc import ABC
  import inspect

  # Verify it's abstract
  assert issubclass(ReconciliationSessionRepository, ABC)

  # Verify required methods exist
  methods = ['add', 'get', 'get_pending_for_account', 'update', 'delete', 'list_by_account']
  for method in methods:
      assert hasattr(ReconciliationSessionRepository, method), f'Missing method: {method}'
  print('Interface OK')
  "
  # Assert: Output contains "Interface OK"
  ```

  **Commit**: YES (group with Task 1)
  - Message: `feat(repositories): add ReconciliationSessionRepository interface`
  - Files: `src/family_office_ledger/repositories/interfaces.py`
  - Pre-commit: `uv run mypy src/family_office_ledger/repositories/interfaces.py`

---

### Task 3: SQLite Repository Implementation

- [x] 3. Implement SQLiteReconciliationSessionRepository

  **What to do**:
  - Edit `src/family_office_ledger/repositories/sqlite.py`
  - Add `reconciliation_sessions` table creation in `initialize()`:
    - `id TEXT PRIMARY KEY`
    - `account_id TEXT NOT NULL`
    - `file_name TEXT NOT NULL`
    - `file_format TEXT NOT NULL`
    - `status TEXT NOT NULL`
    - `created_at TEXT NOT NULL`
    - `closed_at TEXT`
    - Index on `account_id`
  - Add `reconciliation_matches` table:
    - `id TEXT PRIMARY KEY`
    - `session_id TEXT NOT NULL REFERENCES reconciliation_sessions(id)`
    - `imported_id TEXT NOT NULL`
    - `imported_date TEXT NOT NULL`
    - `imported_amount TEXT NOT NULL`
    - `imported_description TEXT`
    - `suggested_ledger_txn_id TEXT`
    - `confidence_score INTEGER NOT NULL`
    - `status TEXT NOT NULL`
    - `actioned_at TEXT`
    - `created_at TEXT NOT NULL`
    - Index on `session_id`
  - Implement `SQLiteReconciliationSessionRepository` class with all interface methods
  - Handle cascade: loading session loads all matches; deleting session deletes matches
  - Write TDD tests first in `tests/test_reconciliation_session_repository.py`

  **Must NOT do**:
  - NO changing existing table schemas
  
  **FK Cascade Strategy**: SQLite has `PRAGMA foreign_keys = ON` (see `sqlite.py:50-51`). Use `ON DELETE CASCADE` for `reconciliation_matches.session_id` FK. Deleting a session auto-deletes its matches.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Significant code addition, database schema work, comprehensive testing
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `git-master`: Not needed until commit

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 4)
  - **Blocks**: Task 5
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `src/family_office_ledger/repositories/sqlite.py:33-52` - SQLiteDatabase class and get_connection with FK pragma
  - `src/family_office_ledger/repositories/sqlite.py:54-180` - initialize() method with table creation DDL
  - `src/family_office_ledger/repositories/sqlite.py:643-840` - SQLiteTransactionRepository CRUD pattern
  - `src/family_office_ledger/repositories/sqlite.py:843-1007` - SQLiteTaxLotRepository with complex queries

  **Test References**:
  - `tests/test_repositories_sqlite.py:1-100` - Repository test setup and fixtures
  - `tests/test_repositories_sqlite.py:200-350` - Transaction repository tests

  **Acceptance Criteria**:

  **TDD (tests first):**
  - [x] Test file created: `tests/test_reconciliation_session_repository.py`
  - [x] Tests cover: add, get, get_pending_for_account, update, delete, list_by_account
  - [x] Tests cover: cascade delete of matches, session status transitions
  - [x] `uv run pytest tests/test_reconciliation_session_repository.py -v` → PASS (15 tests)

  **Automated Verification:**
  ```bash
  # Agent runs:
  uv run python -c "
  from family_office_ledger.repositories.sqlite import (
      SQLiteDatabase, SQLiteReconciliationSessionRepository
  )
  from family_office_ledger.domain.reconciliation import (
      ReconciliationSession, ReconciliationMatch, ReconciliationSessionStatus
  )
  from uuid import uuid4
  from datetime import date
  from decimal import Decimal
  import tempfile
  import os

  # Create temp database
  with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
      db_path = f.name

  try:
      db = SQLiteDatabase(db_path)
      db.initialize()
      # Direct instantiation pattern (NOT db.property)
      repo = SQLiteReconciliationSessionRepository(db)

      # Create session
      account_id = uuid4()
      session = ReconciliationSession(
          account_id=account_id,
          file_name='test.csv',
          file_format='csv'
      )
      repo.add(session)

      # Retrieve
      retrieved = repo.get(session.id)
      assert retrieved is not None
      assert retrieved.account_id == account_id

      # Get pending for account
      pending = repo.get_pending_for_account(account_id)
      assert pending is not None
      assert pending.id == session.id

      print('SQLite repository OK')
  finally:
      os.unlink(db_path)
  "
  # Assert: Output contains "SQLite repository OK"
  ```

  **Commit**: YES
  - Message: `feat(repositories): add SQLite reconciliation session repository`
  - Files: `src/family_office_ledger/repositories/sqlite.py`, `tests/test_reconciliation_session_repository.py`
  - Pre-commit: `uv run pytest tests/test_reconciliation_session_repository.py -v`

---

### Task 4: Postgres Repository Implementation

- [x] 4. Implement PostgresReconciliationSessionRepository

  **What to do**:
  - Edit `src/family_office_ledger/repositories/postgres.py`
  - Add same table schemas as SQLite in `initialize()`
  - Implement `PostgresReconciliationSessionRepository` class
  - Mirror SQLite implementation with Postgres SQL syntax
  - Tests can reuse patterns from `tests/test_repositories_postgres.py`

  **Must NOT do**:
  - NO changing existing table schemas
  - NO breaking Postgres CI (if present)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Database work mirroring SQLite implementation
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 3)
  - **Blocks**: None directly (SQLite is primary for dev)
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `src/family_office_ledger/repositories/postgres.py:1-180` - PostgresDatabase class and initialization
  - `src/family_office_ledger/repositories/postgres.py:671-880` - PostgresTransactionRepository CRUD pattern
  - `src/family_office_ledger/repositories/postgres.py:881-1053` - PostgresTaxLotRepository with complex queries

  **Test References**:
  - `tests/test_repositories_postgres.py:1-100` - Postgres test fixtures (may skip if no Postgres available)

  **Acceptance Criteria**:

  **TDD (tests first):**
  - [x] Tests added to `tests/test_repositories_postgres.py` with same coverage as SQLite:
    - `test_add_session`, `test_get_session`, `test_get_pending_for_account`
    - `test_update_session`, `test_delete_session_cascades_matches`, `test_list_by_account`
  - [x] Tests marked with `@pytest.mark.skipif(not POSTGRES_URL, reason="No Postgres")` pattern
  - [x] `uv run mypy src/family_office_ledger/repositories/postgres.py` → No errors

  **Automated Verification (when POSTGRES_URL is available):**
  ```bash
  # Agent runs:
  uv run python -c "
  from family_office_ledger.repositories.postgres import PostgresReconciliationSessionRepository
  print('Postgres repository class exists')
  "
  # Assert: No import error

  # When POSTGRES_URL is set, run full test suite:
  # uv run pytest tests/test_repositories_postgres.py -v -k reconciliation
  # Assert: All reconciliation session tests pass
  ```

  **Commit**: YES
  - Message: `feat(repositories): add Postgres reconciliation session repository`
  - Files: `src/family_office_ledger/repositories/postgres.py`, `tests/test_repositories_postgres.py`
  - Pre-commit: `uv run mypy src/family_office_ledger/repositories/postgres.py`

---

### Task 5: Service Enhancement

- [x] 5. Enhance ReconciliationServiceImpl with session support

  **What to do**:
  - Edit `src/family_office_ledger/services/reconciliation.py`
  - Add `ReconciliationSessionRepository` to constructor
  - Add new methods:
    - `create_session(account_id: UUID, file_path: str, file_format: str) -> ReconciliationSession`
      - Check for existing pending session → raise `SessionExistsError` (409)
      - Import transactions from file
      - Run matching against ledger
      - Create ReconciliationMatch for each imported transaction
      - Persist session with matches
      - Return session
    - `get_session(session_id: UUID) -> ReconciliationSession | None`
    - `list_matches(session_id: UUID, status: ReconciliationMatchStatus | None = None, limit: int = 50, offset: int = 0) -> tuple[list[ReconciliationMatch], int]`
      - Returns (matches, total_count) for pagination
    - `confirm_session_match(session_id: UUID, match_id: UUID) -> ReconciliationMatch`
      - Note: Named `confirm_session_match` to avoid collision with existing `confirm_match(imported_id, ledger_txn_id)`
      - Update match status to CONFIRMED
      - Call existing `confirm_match(imported_id, ledger_txn_id)` internally to update ledger reference
      - Check if session should auto-close (triggers when pending==0 AND skipped==0)
    - `reject_session_match(session_id: UUID, match_id: UUID) -> ReconciliationMatch`
      - Update match status to REJECTED
      - Check if session should auto-close
    - `skip_session_match(session_id: UUID, match_id: UUID) -> ReconciliationMatch`
      - Update match status to SKIPPED
      - NO auto-close check (skipped can be revisited)
    - `close_session(session_id: UUID) -> ReconciliationSession`
      - Set status to COMPLETED or ABANDONED based on match states
      - Set closed_at timestamp
    - `get_session_summary(session_id: UUID) -> ReconciliationSummary`
  - Add `SessionExistsError`, `SessionNotFoundError`, `MatchNotFoundError` exceptions
  - Write TDD tests first in `tests/test_reconciliation_workflow.py`

  **Must NOT do**:
  - NO modifying existing `confirm_match(imported_id, ledger_transaction_id)` signature
  - NO storing file contents in session
  - NO bulk operations

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Core business logic, many methods, complex state management
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (after Task 3)
  - **Blocks**: Tasks 6, 7, 8
  - **Blocked By**: Tasks 1, 2, 3

  **References**:

  **Pattern References**:
  - `src/family_office_ledger/services/reconciliation.py:1-50` - Existing ReconciliationServiceImpl constructor
  - `src/family_office_ledger/services/reconciliation.py:89-170` - `match_imported` method (matching algorithm)
  - `src/family_office_ledger/services/reconciliation.py:271-295` - `confirm_match` method
  - `src/family_office_ledger/services/ingestion.py:100-200` - Service with repository injection pattern

  **Test References**:
  - `tests/test_reconciliation_service.py:1-100` - Existing reconciliation tests
  - `tests/test_reconciliation_service.py:400-500` - Full workflow integration tests

  **Acceptance Criteria**:

  **TDD (tests first):**
  - [x] Test file created: `tests/test_reconciliation_workflow.py`
  - [x] Tests cover: create_session, list_matches (with pagination), confirm_session_match, reject_session_match, skip_session_match, close_session
  - [x] Tests cover: auto-close triggers when pending==0 AND skipped==0
  - [x] Tests cover: SessionExistsError when pending session exists
  - [x] Tests cover: session status COMPLETED vs ABANDONED on close
  - [x] `uv run pytest tests/test_reconciliation_workflow.py -v` → PASS (27 tests)

  **Automated Verification:**
  ```bash
  # Agent runs:
  uv run python -c "
  from family_office_ledger.services.reconciliation import (
      ReconciliationServiceImpl,
      SessionExistsError,
      SessionNotFoundError,
      MatchNotFoundError
  )
  import inspect

  # Verify new methods exist
  methods = [
      'create_session', 'get_session', 'list_matches',
      'confirm_session_match', 'reject_session_match', 'skip_session_match',
      'close_session', 'get_session_summary'
  ]
  for method in methods:
      assert hasattr(ReconciliationServiceImpl, method), f'Missing: {method}'

  # Verify exceptions
  assert issubclass(SessionExistsError, Exception)
  assert issubclass(SessionNotFoundError, Exception)
  assert issubclass(MatchNotFoundError, Exception)

  print('Service enhancements OK')
  "
  # Assert: Output contains "Service enhancements OK"
  ```

  **Commit**: YES
  - Message: `feat(services): add session-based reconciliation workflow`
  - Files: `src/family_office_ledger/services/reconciliation.py`, `tests/test_reconciliation_workflow.py`
  - Pre-commit: `uv run pytest tests/test_reconciliation_workflow.py -v`

---

### Task 6: API Endpoints

- [x] 6. Add reconciliation REST API endpoints

  **What to do**:
  - Edit `src/family_office_ledger/api/routes.py`
  - Create `reconciliation_router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])`
  - Edit `src/family_office_ledger/api/app.py` to:
    - Add import: `from family_office_ledger.api.routes import reconciliation_router`
    - Add: `app.include_router(reconciliation_router)` in `create_app()` (after line 52)
  - Add endpoints:
    - `POST /reconciliation/sessions` → Create session (request: account_id, file_path, file_format)
    - `GET /reconciliation/sessions/{session_id}` → Get session
    - `GET /reconciliation/sessions/{session_id}/matches` → List matches (query params: status, limit, offset)
    - `POST /reconciliation/sessions/{session_id}/matches/{match_id}/confirm` → Confirm match
    - `POST /reconciliation/sessions/{session_id}/matches/{match_id}/reject` → Reject match
    - `POST /reconciliation/sessions/{session_id}/matches/{match_id}/skip` → Skip match
    - `POST /reconciliation/sessions/{session_id}/close` → Close session
    - `GET /reconciliation/sessions/{session_id}/summary` → Get summary
  - Handle exceptions:
    - `SessionExistsError` → 409 Conflict
    - `SessionNotFoundError` → 404 Not Found
    - `MatchNotFoundError` → 404 Not Found
  - Include router in `create_app()`
  - Write TDD tests first in `tests/test_reconciliation_api.py`

  **Must NOT do**:
  - NO interactive/streaming responses
  - NO WebSocket endpoints
  - NO file upload (file_path is server-side path)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple endpoints, error handling, schema integration
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 7, 8)
  - **Blocks**: Task 9
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - `src/family_office_ledger/api/routes.py:51-56` - Router creation pattern (APIRouter with prefix/tags)
  - `src/family_office_ledger/api/routes.py:59-105` - Dependency injection functions (get_*_repository, get_*_service)
  - `src/family_office_ledger/api/routes.py:108-159` - Helper functions to convert domain to response
  - `src/family_office_ledger/api/routes.py:170-194` - POST endpoint with Depends() for DB injection
  - `src/family_office_ledger/api/routes.py:197-200` - GET list endpoint pattern
  - `src/family_office_ledger/api/app.py:5-11` - Router imports in app.py
  - `src/family_office_ledger/api/app.py:47-52` - app.include_router() pattern in create_app()

  **Test References**:
  - `tests/test_api.py:1-100` - API test setup with TestClient
  - `tests/test_api.py:245-350` - POST endpoint tests with assertions

  **Acceptance Criteria**:

  **TDD (tests first):**
  - [ ] Test file created: `tests/test_reconciliation_api.py`
  - [ ] Tests cover all endpoints with success and error cases
  - [ ] `uv run pytest tests/test_reconciliation_api.py -v` → PASS

  **Automated Verification:**
  ```bash
  # Agent runs (after starting test server):
  # Note: These are acceptance criteria patterns - actual test uses TestClient

  # AC: Create session returns 201
  # POST /reconciliation/sessions {"account_id": "uuid", "file_path": "/path", "file_format": "csv"}
  # Assert: status_code == 201
  # Assert: response.json() has "session_id"

  # AC: Create session with existing pending returns 409
  # POST /reconciliation/sessions (same account_id)
  # Assert: status_code == 409

  # AC: List matches with pagination
  # GET /reconciliation/sessions/{id}/matches?limit=10&offset=0
  # Assert: response.json() is list
  # Assert: len <= 10

  # AC: Confirm match updates status
  # POST /reconciliation/sessions/{id}/matches/{match_id}/confirm
  # Assert: status_code == 200
  # Assert: response.json()["status"] == "confirmed"

  uv run pytest tests/test_reconciliation_api.py -v
  # Assert: All tests pass
  ```

  **Commit**: YES
  - Message: `feat(api): add reconciliation REST endpoints`
  - Files: `src/family_office_ledger/api/routes.py`, `src/family_office_ledger/api/app.py`, `tests/test_reconciliation_api.py`
  - Pre-commit: `uv run pytest tests/test_reconciliation_api.py -v`

---

### Task 7: API Schemas

- [x] 7. Add Pydantic schemas for reconciliation API

  **What to do**:
  - Edit `src/family_office_ledger/api/schemas.py`
  - Add request/response schemas:
    - `CreateSessionRequest(account_id: UUID, file_path: str, file_format: str)`
    - `SessionResponse(session_id: UUID, account_id: UUID, status: str, created_at: datetime, ...)`
    - `MatchResponse(match_id: UUID, imported_id: str, imported_date: date, imported_amount: Decimal, ...)`
    - `MatchListResponse(matches: list[MatchResponse], total: int, limit: int, offset: int)`
    - `SessionSummaryResponse(total: int, confirmed: int, rejected: int, skipped: int, pending: int, match_rate: float)`

  **Must NOT do**:
  - NO nested complex types that can't serialize

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward Pydantic schema definitions
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 6, 8)
  - **Blocks**: Task 6 (needs schemas)
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - `src/family_office_ledger/api/schemas.py:1-100` - Existing Pydantic schema patterns

  **Acceptance Criteria**:

  **Automated Verification:**
  ```bash
  uv run python -c "
  from family_office_ledger.api.schemas import (
      CreateSessionRequest, SessionResponse, MatchResponse,
      MatchListResponse, SessionSummaryResponse
  )
  print('Schemas OK')
  "
  # Assert: No import errors
  ```

  **Commit**: YES (group with Task 6)
  - Message: `feat(api): add reconciliation Pydantic schemas`
  - Files: `src/family_office_ledger/api/schemas.py`
  - Pre-commit: `uv run mypy src/family_office_ledger/api/schemas.py`

---

### Task 8: CLI Commands

- [x] 8. Add reconciliation CLI commands

  **What to do**:
  - Edit `src/family_office_ledger/cli.py`
  - Add commands:
    - `fol reconcile create --account-id UUID --file PATH [--format csv|ofx]`
    - `fol reconcile list --session-id UUID [--status pending|confirmed|rejected|skipped]`
    - `fol reconcile confirm --session-id UUID --match-id UUID`
    - `fol reconcile reject --session-id UUID --match-id UUID`
    - `fol reconcile skip --session-id UUID --match-id UUID`
    - `fol reconcile close --session-id UUID`
    - `fol reconcile summary --session-id UUID`
  - Use `cmd_reconcile_*` function pattern
  - Print formatted output (tables for lists)
  - Return exit code 0 on success, non-zero on error
  - Write TDD tests first in `tests/test_reconciliation_cli.py`

  **Must NOT do**:
  - NO interactive prompts (no `input()`)
  - NO streaming output
  - NO ANSI colors (keep it simple)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple commands, argument parsing, output formatting
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 6, 7)
  - **Blocks**: Task 9
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - `src/family_office_ledger/cli.py:103-140` - `cmd_ingest` command pattern
  - `src/family_office_ledger/cli.py:1-50` - CLI setup and argument parsing

  **Test References**:
  - `tests/test_cli.py:1-100` - CLI test patterns

  **Acceptance Criteria**:

  **TDD (tests first):**
  - [ ] Test file created: `tests/test_reconciliation_cli.py`
  - [ ] Tests cover all commands with success and error cases
  - [ ] `uv run pytest tests/test_reconciliation_cli.py -v` → PASS

  **Automated Verification:**
  ```bash
  # Agent runs:
  uv run fol reconcile --help
  # Assert: Shows subcommands: create, list, confirm, reject, skip, close, summary

  uv run fol reconcile create --help
  # Assert: Shows options: --account-id, --file, --format
  ```

  **Commit**: YES
  - Message: `feat(cli): add reconciliation commands`
  - Files: `src/family_office_ledger/cli.py`, `tests/test_reconciliation_cli.py`
  - Pre-commit: `uv run pytest tests/test_reconciliation_cli.py -v`

---

### Task 9: Integration Tests

- [x] 9. Add end-to-end integration tests

  **What to do**:
  - Create comprehensive integration tests that exercise full workflow:
    1. Create session from CSV file
    2. List matches
    3. Confirm high-confidence match
    4. Reject low-confidence match
    5. Skip ambiguous match
    6. Close session
    7. Verify summary
  - Test via both API and CLI
  - Use real (temp) database

  **Must NOT do**:
  - NO mocking in integration tests
  - NO skipping cleanup

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Comprehensive integration testing
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (after Tasks 6, 8)
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 6, 8

  **References**:

  **Test References**:
  - `tests/test_reconciliation_service.py:700-830` - Existing integration test patterns

  **Acceptance Criteria**:

  **Automated Verification:**
  ```bash
  uv run pytest tests/test_reconciliation_workflow.py tests/test_reconciliation_api.py tests/test_reconciliation_cli.py -v
  # Assert: All tests pass
  ```

  **Commit**: YES
  - Message: `test: add reconciliation integration tests`
  - Files: Test files from Tasks 3, 5, 6, 8
  - Pre-commit: `uv run pytest tests/test_reconciliation_*.py -v`

---

### Task 10: Exports and Documentation

- [x] 10. Update exports and AGENTS.md

  **What to do**:
  - Edit `src/family_office_ledger/domain/__init__.py` - Add reconciliation exports
  - Edit `src/family_office_ledger/repositories/__init__.py` - Add repository exports
  - Edit `src/family_office_ledger/services/__init__.py` - Add exception exports
  - Edit `src/family_office_ledger/api/__init__.py` - Add schema exports if needed
  - Update `AGENTS.md` with reconciliation workflow documentation

  **Must NOT do**:
  - NO breaking existing exports

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple export updates
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (after Task 9)
  - **Blocks**: None
  - **Blocked By**: Task 9

  **References**:

  **Pattern References**:
  - `src/family_office_ledger/services/__init__.py:1-50` - Export pattern

  **Acceptance Criteria**:

  **Automated Verification:**
  ```bash
  uv run python -c "
  from family_office_ledger.domain import ReconciliationSession, ReconciliationMatch
  from family_office_ledger.services import SessionExistsError
  print('Exports OK')
  "
  # Assert: No import errors

  uv run pytest -v
  # Assert: All tests pass (full suite)

  uv run mypy src/
  # Assert: No type errors

  uv run ruff check .
  # Assert: No lint errors
  ```

  **Commit**: YES
  - Message: `chore: update exports and documentation for reconciliation workflow`
  - Files: `__init__.py` files, `AGENTS.md`
  - Pre-commit: `uv run pytest -v && uv run mypy src/`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1+2 | `feat(domain): add reconciliation domain models and repository interface` | domain/reconciliation.py, repositories/interfaces.py | pytest + mypy |
| 3 | `feat(repositories): add SQLite reconciliation session repository` | repositories/sqlite.py | pytest |
| 4 | `feat(repositories): add Postgres reconciliation session repository` | repositories/postgres.py | mypy |
| 5 | `feat(services): add session-based reconciliation workflow` | services/reconciliation.py | pytest |
| 6+7 | `feat(api): add reconciliation REST endpoints and schemas` | api/routes.py, api/schemas.py | pytest |
| 8 | `feat(cli): add reconciliation commands` | cli.py | pytest |
| 9 | `test: add reconciliation integration tests` | tests/ | pytest |
| 10 | `chore: update exports for reconciliation workflow` | __init__.py files | full suite |

---

## Success Criteria

### Verification Commands
```bash
# All tests pass
uv run pytest tests/test_reconciliation_*.py -v

# Type checking
uv run mypy src/

# Linting
uv run ruff check .

# Full test suite
uv run pytest -v
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] mypy clean
- [ ] ruff clean
- [ ] CLI commands work
- [ ] API endpoints work
