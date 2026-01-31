<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-29 | Updated: 2026-01-31 -->

# DOMAIN LAYER

## OVERVIEW
Core accounting domain: entities, transactions, tax lots, reconciliation, exchange rates, budgets, and value objects.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Entities/accounts | entities.py | Entity, Account, Security, Position |
| Transactions | transactions.py | Transaction, Entry, TaxLot + exceptions |
| Value objects | value_objects.py | Money, Quantity (frozen), 10 enums |
| Reconciliation | reconciliation.py | ReconciliationSession, ReconciliationMatch |
| Transfer matching | transfer_matching.py | TransferMatchingSession, TransferMatch |
| Corporate actions | corporate_actions.py | CorporateAction, Price |
| Documents | documents.py | Document, TaxDocLine |
| Audit | audit.py | AuditEntry, AuditAction enum |
| Exchange rates | exchange_rates.py | ExchangeRate (frozen dataclass) |
| Vendors | vendors.py | Vendor dataclass |
| Budgets | budgets.py | Budget, BudgetLineItem, BudgetVariance, BudgetPeriodType |

## CONVENTIONS
- Dataclasses with `id: UUID = field(default_factory=uuid4)`
- UTC timestamps via `_utc_now()` helper
- Enums inherit from `str, Enum` for JSON serialization
- Value objects: `@dataclass(frozen=True, slots=True)`
- Validation in `__post_init__` or dedicated `validate()` methods
- Domain exceptions in transactions.py (UnbalancedTransactionError, etc.)

## ENUMS (11 total)
Currency (19), EntityType (5), AccountType (5), AccountSubType (15), AssetClass (8), AcquisitionType (8), CorporateActionType (8), TransactionType (23), ExpenseCategory (19), LotSelection (7), BudgetPeriodType (4)

## ANTI-PATTERNS (THIS PROJECT)
- None documented.

## NOTES
- Money/Quantity use `object.__setattr__()` in `__post_init__` to bypass frozen for Decimal coercion
- Position uses private fields (`_quantity`, `_cost_basis`) with property accessors
- TaxLot tracks `original_quantity` vs `remaining_quantity` for partial dispositions
- ReconciliationMatch statuses: PENDING, CONFIRMED, REJECTED, SKIPPED
- BudgetVariance is frozen dataclass with computed properties (variance_percent, is_over_budget)
