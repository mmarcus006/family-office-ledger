# Draft: Reconciliation Workflow

## Requirements (confirmed)
- **Full reconciliation suite**: Post-ingestion verification + Interactive matching + Bank statement reconciliation
- **Start with**: Interactive matching (user's priority)
- **Interface**: Both CLI (`fol reconcile`) and API (REST endpoints)
- **Test strategy**: TDD (write failing tests first)
- **Plan quality**: High accuracy (Momus review)

## Technical Decisions
- **Match state persistence**: Database (ReconciliationSession table survives restarts)
- **Match actions**: Confirm / Reject / Skip (NO Edit in v1 - Metis recommendation accepted)
- **Matching algorithm**: Existing fuzzy matching (amount 50pts + date 30pts + memo 20pts)
- **Session lifecycle**: Auto-close when all matches processed + manual close anytime
- **Concurrency**: One pending session per account (409 Conflict if exists)

## Research Findings
- **Existing ReconciliationServiceImpl**: 466 lines with import, match, confirm, create_from_import, get_summary
- **No API endpoints**: ReconciliationService not exposed via REST
- **No CLI commands**: No `fol reconcile` command
- **Ingestion separate**: Ingestion books directly with reference=import_id, no auto-reconciliation
- **Suspense account hardcoded**: create_from_import uses placeholder

## Metis Gap Analysis Incorporated
- Session lifecycle clarified (auto-close + manual)
- Edit action removed from v1
- Concurrent sessions prevented (one per account)
- Acceptance criteria defined as executable curl/CLI commands
- Scale considerations noted (pagination for large datasets)

## Open Questions
- None - all requirements clarified

## Scope Boundaries
- **INCLUDE**:
  - Interactive matching workflow (priority 1)
  - Post-ingestion verification (priority 2)
  - Bank statement reconciliation (priority 3)
  - ReconciliationSession domain model
  - Database persistence for sessions
  - CLI commands
  - API endpoints
  - TDD test coverage
- **EXCLUDE**:
  - Machine learning matching
  - Multi-user approval workflows
  - Tax document reconciliation (separate feature)
  - Bulk operations (confirm all)
  - Edit action (v2)
  - Undo capability (v2)
  - Concurrent sessions for same account

## Test Strategy Decision
- **Infrastructure exists**: YES (pytest, fixtures in conftest.py)
- **User wants tests**: YES (TDD)
- **Framework**: pytest with existing patterns
- **QA approach**: TDD - RED-GREEN-REFACTOR for each TODO
