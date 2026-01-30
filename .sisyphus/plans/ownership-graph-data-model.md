# Addepar-Style Ownership Graph Data Model (Households + Look-Through)

## TL;DR

Evolve the current **flat `Entity -> Account -> Position -> TaxLot`** model into an **Addepar-inspired “financial graph”** by adding:

- `Household` as the top-level grouping
- percent-based **ownership edges between entities** (and optional “joint ownership” nodes)
- look-through traversal for **household / beneficial-owner reporting**, while preserving the existing tax-lot + cost basis system

This plan is designed to fit the existing architecture: `domain/` dataclasses → repository interfaces → SQLite/Postgres schema → services → API/CLI.

---

## Context

### Source Documents (requirements)

- `investment-accounting-ux-design-research.md` (Jan 2026)
  - Recommends allocation-tree navigation: Household → Client → Entity → Account → Holding → Lot
  - Tax-awareness should be visible at every layer; reconciliation is first-class
- `partnership-family-office-data-models-report.md` (Jan 2026)
  - Recommends Addepar-style “Financial Graph”: nodes + percentage-based ownership edges
  - Highlights joint ownership + look-through as must-haves for complex family structures

### Current Codebase Reality (what we must integrate with)

- Domain models:
  - `src/family_office_ledger/domain/entities.py` (`Entity`, `Account`, `Security`, `Position`)
  - `src/family_office_ledger/domain/transactions.py` (`Transaction`, `Entry`, `TaxLot`)
- Persistence is flat and entity-scoped:
  - `src/family_office_ledger/repositories/sqlite.py` creates `entities`, `accounts`, `positions`, `tax_lots` tables
  - `accounts.entity_id` enforces **exactly one legal owner entity per account**
- Tax lot + cost basis support is already strong:
  - `src/family_office_ledger/services/lot_matching.py` implements FIFO/LIFO/HIFO/SpecID/etc
  - `src/family_office_ledger/services/tax_documents.py` produces Form 8949 + Schedule D
  - `src/family_office_ledger/services/qsbs.py` models QSBS status/qualification

---

## Decisions

### Confirmed (from user)

- **Client/Person representation**: reuse existing `Entity` with `EntityType.INDIVIDUAL` (no separate Person/Client table).
- **Ownership over time**: time-bounded edges with `effective_start_date` / `effective_end_date`.
- **Household scope**: multiple households supported (multi-family-office ready).
- **Joint ownership**: represent joint ownership as a dedicated entity node (add `EntityType.JOINT`), not polymorphic edges to accounts.
- **Partnership scope**: include partnership capital accounts; exclude waterfall allocations.

### Additional Confirmed (follow-up)

- **Multi-household naming / identity**: keep `entities.name` globally `UNIQUE`; add a household-scoped display label on membership.

Defaults applied until you decide:
- Ownership edges represent **economic exposure** for look-through reporting (not tax filing attribution).
- Partnership capital accounts default to **partner-level** (best practice), but can be simplified to partnership-level only if desired.

---

## Semantics And Guardrails

These rules are what prevent cycles, double counting, and “mystery totals.”

### Ownership Edge Semantics

- **Meaning**: `ownership_fraction` expresses economic exposure (net worth weighting) from `owner_entity_id` to `owned_entity_id`.
- **Not for filing**: tax documents (`Form 8949`, `Schedule D`) remain entity-scoped unless/until a dedicated tax-attribution layer is added.
- **Effective dating**: treat edges as half-open `[start, end)`.

### Household Membership Semantics

- Household membership defines which entities are “in scope” for a household.
- **Roots for look-through** (recommended): `EntityType.INDIVIDUAL` members with `role = 'client'`.
- **Double-counting rule**: household rollups are computed from roots through ownership edges; direct membership of downstream entities must not implicitly create additional roots.

### Remainder / External Ownership Policy

- Allow sum(owner fractions) < 1.0 and treat the remainder as “external/unknown”.
- Reports show household-owned share; optionally include an “unallocated remainder” line item.

### Validation Rules (creation-time)

- Reject self-edges.
- Reject cycles (deterministic error).
- Reject overlapping effective-date ranges for the same `(owner_entity_id, owned_entity_id, ownership_type)`.
- Reject sum(owner fractions) > 1.0 for a given `(owned_entity_id, as_of_date, ownership_type)`.

---

## Proposed Target Data Model (v2)

> This section describes the recommended “best-practice” shape of the data model after the above decisions are made.

### 1) Household

New domain model: `Household`

**Table: `households`**

| Column | Type | Notes |
|--------|------|------|
| id | UUID (TEXT) | PK |
| name | TEXT | unique within system (or per tenant) |
| primary_contact_entity_id | UUID (TEXT) | optional FK to `entities.id` |
| is_active | INTEGER | default 1 |
| created_at / updated_at | TEXT | ISO timestamp |

**Relationship:**

- Household (1) → (N) Entities (clients + legal entities + joint nodes)

**Table: `household_members`**

| Column | Type | Notes |
|--------|------|------|
| household_id | UUID (TEXT) | FK → `households.id` |
| entity_id | UUID (TEXT) | FK → `entities.id` |
| role | TEXT | optional (`client`, `entity`, etc.) |
| display_name | TEXT | optional household-scoped label (e.g. “John Smith”) |
| effective_start_date | TEXT | date; nullable or required |
| effective_end_date | TEXT | date; nullable |

Rationale: this aligns with the chosen “multiple households” + time-bounded modeling.

### 2) Entity (Client + Legal Entity + Joint Node)

Keep existing `Entity` as the central “node” concept, but extend it.

**Existing:** `src/family_office_ledger/domain/entities.py#L21` (Entity)

**Add (recommended fields):**

- `tax_id: str | None` and `tax_id_type: str | None` (SSN/EIN/ITIN)  
  - If you don’t want to store raw sensitive IDs, store masked + last4 or keep entirely optional.
- `tax_treatment: TaxTreatment` (e.g., pass-through, c-corp, tax-exempt, disregarded)
- `formation_date: date | None`
- `jurisdiction: str | None`

**Expand `EntityType`** (in `src/family_office_ledger/domain/value_objects.py`):

- Keep: LLC, TRUST, PARTNERSHIP, INDIVIDUAL, HOLDING_CO
- Add: FOUNDATION, ESTATE, S_CORP, C_CORP, JOINT

### Uniqueness Note (must reconcile with multi-household)

Today, the SQLite schema enforces `entities.name` as globally unique:

- `src/family_office_ledger/repositories/sqlite.py` (`CREATE TABLE entities ... name TEXT NOT NULL UNIQUE`)

Decision: keep global uniqueness and introduce a household-scoped label (`household_members.display_name`).

### 3) Ownership Edge (Entity ↔ Entity)

New domain model: `EntityOwnership`

This is the core “financial graph” capability.

**Table: `entity_ownership`**

| Column | Type | Notes |
|--------|------|------|
| id | UUID (TEXT) | PK |
| owner_entity_id | UUID (TEXT) | FK → `entities.id` |
| owned_entity_id | UUID (TEXT) | FK → `entities.id` |
| ownership_fraction | TEXT | decimal string; recommended range 0–1 |
| effective_start_date | TEXT | date; required |
| effective_end_date | TEXT | date; nullable |
| ownership_basis | TEXT | `percent` now; reserve `units` for later |
| ownership_type | TEXT | default `beneficial` (future: voting, economic, etc.) |
| created_at / updated_at | TEXT | ISO timestamp |
| notes | TEXT | optional |

**Invariants / validations (service-level, not just DB):**

- No self-edges (owner != owned)
- Prevent cycles (or at least detect and error) to avoid infinite look-through
- For a given owned_entity + as-of date, enforce that **sum(owner fractions) ≈ 1.0** (configurable tolerance) OR explicitly allow “unknown remainder”
- Treat effective dates as half-open intervals: edge is active if `start <= as_of_date` and (`end` is null or `as_of_date < end`)

### 4) Account / Position / TaxLot

Keep existing model; add account defaults to match UX doc.

**Account** (`src/family_office_ledger/domain/entities.py#L42`) — recommended additions:

- `institution: str | None`
- `account_number_last4: str | None`
- `default_lot_selection: LotSelection` (defaults FIFO)
- `connection_type: str` (manual/linked) + optional `connection_id`

**Why**: aligns with the UX requirement “sensible defaults with expert overrides” and supports the “Account default cost basis method” behavior.

### 5) Allocation Tree Views (derived, not stored)

The UI wants “Household → Client → Entity → Account → Holding → Lot”. The storage model can remain graph + attachments, and we produce the tree as a derived view.

Recommended service: `OwnershipGraphService` (new)

- Build an adjacency map from `entity_ownership` for a given as-of date
- Provide queries:
  - `list_household_roots(household_id)`
  - `get_allocation_tree(household_id, as_of_date)`
  - `compute_effective_ownership(owner_entity_id, as_of_date)` → map[entity_id] = fractional ownership

### 6) Partnership Capital Accounts (no waterfall)

Goal: support partnership-style capital account reporting without modeling distribution waterfalls.

Two supported designs:

1. **Partnership-level only (minimal)**
   - One equity account (e.g., `Member's Capital`) inside the partnership entity.
   - This already exists as an ingestion booking pattern.

2. **Partner-level (recommended for real partnership accounting)**
   - Each partner (an `Entity`: INDIVIDUAL/TRUST/etc.) has a dedicated capital equity account inside the partnership entity.

If partner-level is chosen, add:

**Table: `partnership_partners`**

| Column | Type | Notes |
|--------|------|------|
| partnership_entity_id | UUID (TEXT) | FK → `entities.id` |
| partner_entity_id | UUID (TEXT) | FK → `entities.id` |
| capital_account_id | UUID (TEXT) | FK → `accounts.id` (equity account owned by the partnership entity) |
| effective_start_date | TEXT | date |
| effective_end_date | TEXT | date; nullable |

---

## Work Objectives

### Core Objective

Enable Addepar-style ownership structures and look-through reporting without breaking the existing ledger + investment accounting primitives.

### Concrete Deliverables

- Domain models + enums for household + ownership edges
- Database schema additions (SQLite + Postgres)
- Repository interfaces + implementations
- Ownership graph service for look-through traversal
- Reporting enhancements to support household / beneficial-owner scoped views
- API endpoints to manage households and ownership relationships
- Tests covering ownership math, cycle detection, and look-through reporting

### Must NOT Have (guardrails)

- Don’t replace existing `TaxLot` / cost basis machinery; build ownership on top
- Don’t make `accounts` multi-entity owned at the storage level (would cascade through transaction posting + queries)
- Don’t require enterprise complexity (waterfalls, multi-GAAP, full consolidations) unless explicitly requested
- Don’t introduce account-level ownership edges unless joint-entity modeling proves insufficient

---

## Verification Strategy

This repo has a large pytest suite; new work should include tests.

Global gates (agent-executable):

```bash
uv run pytest -q
# Assert: exit code 0

uv run mypy src/
# Assert: exit code 0

uv run ruff check .
# Assert: exit code 0
```

Ownership-graph targeted tests (to add):

```bash
uv run pytest -q tests/test_ownership_graph.py::test_cycle_rejected
uv run pytest -q tests/test_ownership_graph.py::test_effective_dated_overlap_rejected
uv run pytest -q tests/test_ownership_graph.py::test_household_rollup_no_double_counting
# Assert: each command reports "1 passed" and exit code 0
```

---

## Execution Strategy (Waves)

Wave 1: Domain + persistence foundations

- Household + ownership edge domain models
- Repository interfaces
- SQLite/Postgres schema updates + backfill/default household

Wave 2: Ownership traversal + reporting

- OwnershipGraphService
- Look-through net worth / positions / capital gains variants

Wave 3: API + UX wiring points

- CRUD endpoints for households and ownership edges
- Allocation tree endpoint for UI

---

## TODOs

0. Resolve entity naming uniqueness strategy for multi-household

Why this is first:
- Multi-household is enabled via membership; household-scoped labels avoid a risky uniqueness migration.

References:
- `src/family_office_ledger/repositories/sqlite.py#L74` (entities.name UNIQUE in schema)
- `src/family_office_ledger/repositories/postgres.py` (mirrors schema)
- `src/family_office_ledger/repositories/interfaces.py` (EntityRepository.get_by_name semantics)
- `tests/test_repositories_sqlite.py` (tests for get_by_name)
- `tests/test_repositories_postgres.py` (tests for get_by_name)

Acceptance criteria:
- `uv run pytest -q tests/test_repositories_sqlite.py::TestSQLiteEntityRepository::test_get_by_name` passes (unchanged semantics)
- Household membership can store duplicate `display_name` across different households without colliding on `entities.name`

1. Add `Household` domain model and repository

References:
- `src/family_office_ledger/domain/entities.py` (dataclass conventions)
- `src/family_office_ledger/repositories/sqlite.py#L69` (schema creation style)
- `src/family_office_ledger/repositories/interfaces.py` (repository interface patterns)

Acceptance criteria:
- SQLite schema includes `households` table
- `uv run pytest -q tests/test_households_repository.py::test_add_and_get_household`
  - Assert: output contains "1 passed"

2. Add household membership (`household_members`) and related queries

References:
- `src/family_office_ledger/repositories/sqlite.py#L69` (schema creation style)

Acceptance criteria:
- Entities can be attached to households (with optional effective dates)
- `uv run pytest -q tests/test_household_membership_repository.py::test_add_and_list_membership_as_of_date`
  - Assert: output contains "1 passed"

3. Extend `Entity` to support tax metadata + add `EntityType.JOINT`

References:
- `src/family_office_ledger/domain/entities.py` (Entity fields)
- `src/family_office_ledger/domain/value_objects.py` (Enum conventions)
- `src/family_office_ledger/api/schemas.py#L11` (entity_type validation regex needs updating)

Acceptance criteria:
- Existing tests still pass after schema migration/backfill

4. Add `EntityOwnership` (ownership edges) domain model + repository

References:
- `partnership-family-office-data-models-report.md` (Position/edge model; percent-based ownership)

Acceptance criteria:
- Can persist ownership edges and query by owner/owned
- Validation prevents self-edges
- `uv run pytest -q tests/test_ownership_graph.py::test_self_edge_rejected`
  - Assert: output contains "1 passed"

5. Implement ownership traversal + cycle detection

References:
- `investment-accounting-ux-design-research.md` (allocation tree + look-through)
- `src/family_office_ledger/services/reporting.py` (current multi-entity aggregation)

Acceptance criteria:
- Given a small test graph, traversal returns correct effective ownership weights
- Cycles are detected and rejected deterministically
- `uv run pytest -q tests/test_ownership_graph.py::test_cycle_rejected`
  - Assert: output contains "1 passed"

6. Add household- and beneficial-owner-scoped reports

References:
- `src/family_office_ledger/services/reporting.py` (net worth + positions)

Acceptance criteria:
- New report functions accept `household_id` and/or `owner_entity_id` and produce weighted rollups
- `uv run pytest` passes
- `uv run pytest -q tests/test_ownership_graph.py::test_household_rollup_no_double_counting`
  - Assert: output contains "1 passed"

7. Add API endpoints for households + ownership edges + allocation tree

References:
- `src/family_office_ledger/api/schemas.py` (pydantic patterns)
- `src/family_office_ledger/api/routes.py` (routing patterns)

Acceptance criteria:
- Endpoints exist for CRUD and allocation-tree read
- Basic contract tests (pytest) confirm response shapes
- `uv run pytest -q tests/test_api.py::test_create_entity_returns_201`
  - Assert: still passes after updating allowed entity_type values

8. Add partnership capital account support (no waterfall)

What to do:
- If partnership-level only: confirm existing `Member's Capital` pattern is sufficient and expose a report.
- If partner-level: implement `partnership_partners` mapping and add reporting for partner capital balances.

References:
- `src/family_office_ledger/services/ingestion.py#L661` (existing `Member's Capital` booking)

Acceptance criteria:
- A partnership entity can produce a “capital accounts” report (per partner if configured)
- Existing ledger posting and balance sheet remain correct
- `uv run pytest -q tests/test_ingestion_service.py::test_contribution_to_entity_books_members_capital`
- `uv run pytest -q tests/test_ingestion_service.py::TestBookContributionToEntity::test_books_capital_contribution`
  - Assert: continues to pass (or is replaced by a partner-capital version if chosen)

---

## Success Criteria

- You can model: Household → two individuals → joint entity → account(s) → holdings
- You can model: Individual → Trust → LLC → accounts
- You can compute look-through net worth and holdings without double counting
- Existing investment tax lot functionality remains intact
