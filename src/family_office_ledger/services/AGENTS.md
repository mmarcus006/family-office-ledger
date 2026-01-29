# SERVICES LAYER

## OVERVIEW
Business logic orchestration over domain models and repository interfaces.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Ingestion | ingestion.py | 1216 lines, 35 methods, bank imports |
| Reconciliation | reconciliation.py | 795 lines, session-based matching workflow |
| Transaction classification | transaction_classifier.py | rules engine |
| Ledger posting | ledger.py | double-entry validation |
| Reporting | reporting.py | net worth, balance sheet, PnL |
| Tax lot matching | lot_matching.py | FIFO/LIFO/SPECIFIC_ID/etc. |
| Corporate actions | corporate_actions.py | splits, spinoffs, mergers |
| Interfaces | interfaces.py | ABCs + shared DTOs (MatchResult, LotDisposition) |

## CONVENTIONS
- Service implementations use `*Impl` suffix
- Constructor injection of repository interfaces
- Interfaces and shared DTOs in interfaces.py
- Exceptions defined in same module, re-exported via `__init__.py`

## EXCEPTIONS
- `SessionExistsError`, `SessionNotFoundError`, `MatchNotFoundError` (reconciliation.py)
- `AccountNotFoundError`, `TransactionNotFoundError` (ledger.py)
- `InsufficientLotsError`, `InvalidLotSelectionError` (lot_matching.py)

## ANTI-PATTERNS (THIS PROJECT)
- None documented.

## NOTES
- ingestion.py is the largest hotspot (18 booking methods)
- Reconciliation uses fuzzy matching: exact amount (50pts) + date proximity (30pts) + memo similarity (20pts)
- Auto-close triggers when all matches are CONFIRMED or REJECTED (not SKIPPED)
