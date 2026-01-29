# SERVICES LAYER

## OVERVIEW
Business logic orchestration over domain models and repository interfaces. 16 services total.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Ingestion | ingestion.py | 1216 lines, 35 methods, bank imports |
| Reconciliation | reconciliation.py | 795 lines, session-based matching workflow |
| Transfer matching | transfer_matching.py | inter-account transfer pairing |
| Transaction classification | transaction_classifier.py | rules engine |
| Ledger posting | ledger.py | double-entry validation |
| Reporting | reporting.py | 776 lines, net worth, balance sheet, PnL |
| Tax lot matching | lot_matching.py | FIFO/LIFO/SPECIFIC_ID/etc. |
| Corporate actions | corporate_actions.py | splits, spinoffs, mergers |
| Audit | audit.py | audit trail logging |
| Currency | currency.py | exchange rate management |
| Portfolio analytics | portfolio_analytics.py | allocation, concentration, performance |
| QSBS | qsbs.py | IRC §1202 tracking |
| Tax documents | tax_documents.py | Form 8949, Schedule D |
| Interfaces | interfaces.py | ABCs + shared DTOs (MatchResult, LotDisposition) |

## CONVENTIONS
- Service implementations use `*Impl` suffix (6 services have interfaces)
- Constructor injection of repository interfaces
- Interfaces and shared DTOs in interfaces.py
- Exceptions defined in same module, re-exported via `__init__.py`

## SERVICE INTERFACES (interfaces.py)
| Interface | Implementation | Has ABC |
|-----------|---------------|---------|
| LedgerService | LedgerServiceImpl | Yes |
| ReconciliationService | ReconciliationServiceImpl | Yes |
| ReportingService | ReportingServiceImpl | Yes |
| LotMatchingService | LotMatchingServiceImpl | Yes |
| CorporateActionService | CorporateActionServiceImpl | Yes |
| CurrencyService | CurrencyServiceImpl | Yes |
| TransferMatchingService | - | No |
| QSBSService | - | No |
| TaxDocumentService | - | No |
| PortfolioAnalyticsService | - | No |
| AuditService | - | No |

## EXCEPTIONS
- `SessionExistsError`, `SessionNotFoundError`, `MatchNotFoundError` (reconciliation.py)
- `AccountNotFoundError`, `TransactionNotFoundError` (ledger.py)
- `InsufficientLotsError`, `InvalidLotSelectionError` (lot_matching.py)
- `ExchangeRateNotFoundError` (currency.py)
- `TransferMatchNotFoundError`, `TransferSessionNotFoundError` (transfer_matching.py)

## ANTI-PATTERNS (THIS PROJECT)
- ingestion.py has 23 `_book_*()` methods - strategy pattern candidate

## NOTES
- ingestion.py is the largest hotspot (1216 lines, 23 booking methods)
- Reconciliation uses fuzzy matching: exact amount (50pts) + date proximity (30pts) + memo similarity (20pts)
- Auto-close triggers when all matches are CONFIRMED or REJECTED (not SKIPPED)
