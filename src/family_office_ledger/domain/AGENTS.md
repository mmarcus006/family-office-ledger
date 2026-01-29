# DOMAIN LAYER

## OVERVIEW
Core accounting domain: entities, transactions, tax lots, reconciliation, and value objects.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Entities/accounts | entities.py | Entity, Account, Security, Position |
| Transactions | transactions.py | Transaction, Entry, TaxLot + exceptions |
| Value objects | value_objects.py | Money, Quantity (frozen), 8 enums |
| Reconciliation | reconciliation.py | ReconciliationSession, ReconciliationMatch |
| Corporate actions | corporate_actions.py | CorporateAction, Price |
| Documents | documents.py | Document, TaxDocLine |

## CONVENTIONS
- Dataclasses with `id: UUID = field(default_factory=uuid4)`
- UTC timestamps via `_utc_now()` helper
- Enums inherit from `str, Enum` for JSON serialization
- Value objects: `@dataclass(frozen=True, slots=True)`
- Validation in `__post_init__` or dedicated `validate()` methods
- Domain exceptions in transactions.py (UnbalancedTransactionError, etc.)

## ANTI-PATTERNS (THIS PROJECT)
- None documented.

## NOTES
- Money/Quantity use `object.__setattr__()` in `__post_init__` to bypass frozen for Decimal coercion
- Position uses private fields (`_quantity`, `_cost_basis`) with property accessors
- TaxLot tracks `original_quantity` vs `remaining_quantity` for partial dispositions
- ReconciliationMatch statuses: PENDING, CONFIRMED, REJECTED, SKIPPED
