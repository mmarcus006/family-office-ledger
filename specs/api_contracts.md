# API Contracts

## Overview

The Atlas Family Office Ledger exposes a RESTful API via FastAPI with 85 endpoints across 16 routers.

**Base URL:** `http://localhost:8000`  
**Documentation:** `/docs` (Swagger) or `/redoc` (ReDoc)

## Authentication

Currently no authentication is implemented. All endpoints are publicly accessible.

## Common Patterns

- **IDs:** All resource IDs are UUIDs
- **Dates:** ISO 8601 format (`YYYY-MM-DD`)
- **Amounts:** Serialized as strings to preserve decimal precision
- **Errors:** Standard HTTP status codes with JSON error bodies

## Routers and Endpoints

### Health Router (`/health`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check, returns API version |

### Entity Router (`/entities`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/entities` | Create a new entity |
| GET | `/entities` | List all entities |
| GET | `/entities/{entity_id}` | Get entity by ID |

### Account Router (`/accounts`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/accounts` | Create a new account |
| GET | `/accounts` | List accounts (optionally by entity) |

### Transaction Router (`/transactions`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/transactions` | Create a journal entry |
| GET | `/transactions` | List transactions with filters |

### Report Router (`/reports`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reports/net-worth` | Net worth report |
| GET | `/reports/balance-sheet/{entity_id}` | Balance sheet for entity |
| GET | `/reports/summary-by-type` | Summary by account type |
| GET | `/reports/summary-by-entity` | Summary by entity |
| GET | `/reports/dashboard` | Dashboard metrics |
| GET | `/reports/budget/{entity_id}` | Budget report for entity |

### Reconciliation Router (`/reconciliation`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reconciliation/sessions` | Create reconciliation session |
| GET | `/reconciliation/sessions/{session_id}` | Get session details |
| GET | `/reconciliation/sessions/{session_id}/matches` | List matches |
| POST | `/reconciliation/sessions/{session_id}/matches/{match_id}/confirm` | Confirm match |
| POST | `/reconciliation/sessions/{session_id}/matches/{match_id}/reject` | Reject match |
| POST | `/reconciliation/sessions/{session_id}/matches/{match_id}/skip` | Skip match |
| POST | `/reconciliation/sessions/{session_id}/close` | Close session |
| GET | `/reconciliation/sessions/{session_id}/summary` | Session summary |

### Transfer Router (`/transfers`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/transfers/sessions` | Create transfer matching session |
| GET | `/transfers/sessions/{session_id}` | Get session details |
| GET | `/transfers/sessions/{session_id}/matches` | List potential matches |
| POST | `/transfers/sessions/{session_id}/matches/{match_id}/confirm` | Confirm match |
| POST | `/transfers/sessions/{session_id}/matches/{match_id}/reject` | Reject match |
| POST | `/transfers/sessions/{session_id}/close` | Close session |
| GET | `/transfers/sessions/{session_id}/summary` | Session summary |

### QSBS Router (`/qsbs`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/qsbs/securities` | List QSBS-eligible securities |
| POST | `/qsbs/securities/{security_id}/mark-eligible` | Mark security as QSBS-eligible |
| POST | `/qsbs/securities/{security_id}/unmark-eligible` | Remove QSBS eligibility |
| GET | `/qsbs/summary` | QSBS holdings summary |

### Tax Router (`/tax`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tax/generate` | Generate tax documents |
| GET | `/tax/summary` | Tax document summary |
| GET | `/tax/entities/{entity_id}/form-8949` | Form 8949 for entity |
| GET | `/tax/entities/{entity_id}/schedule-d` | Schedule D for entity |

### Portfolio Router (`/portfolio`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/portfolio/asset-allocation` | Asset allocation breakdown |
| GET | `/portfolio/concentration` | Concentration analysis |
| GET | `/portfolio/performance` | Performance metrics |
| GET | `/portfolio/summary` | Portfolio summary |

### Audit Router (`/audit`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/audit` | List audit entries with filters |
| GET | `/audit/{entry_id}` | Get audit entry by ID |
| GET | `/audit/entity/{entity_id}` | Audit trail for entity |
| GET | `/audit/summary` | Audit summary statistics |

### Currency Router (`/currency`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/currency/rates` | Add exchange rate |
| GET | `/currency/rates` | List exchange rates |
| GET | `/currency/rates/latest` | Get latest rate for pair |
| GET | `/currency/rates/{rate_id}` | Get rate by ID |
| DELETE | `/currency/rates/{rate_id}` | Delete rate |
| POST | `/currency/convert` | Convert amount between currencies |

### Vendor Router (`/vendors`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/vendors` | Create vendor |
| GET | `/vendors` | List vendors |
| GET | `/vendors/search` | Search vendors by name |
| GET | `/vendors/{vendor_id}` | Get vendor by ID |
| PUT | `/vendors/{vendor_id}` | Update vendor |
| DELETE | `/vendors/{vendor_id}` | Delete vendor |

### Expense Router (`/expenses`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/expenses/categorize` | Categorize a transaction |
| GET | `/expenses/summary` | Expense summary by period |
| GET | `/expenses/by-category` | Expenses grouped by category |
| GET | `/expenses/by-vendor` | Expenses grouped by vendor |
| GET | `/expenses/recurring` | Detect recurring expenses |

### Budget Router (`/budgets`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/budgets` | Create budget |
| GET | `/budgets` | List budgets (optionally by entity) |
| GET | `/budgets/{budget_id}` | Get budget by ID |
| DELETE | `/budgets/{budget_id}` | Delete budget |
| POST | `/budgets/{budget_id}/line-items` | Add line item |
| GET | `/budgets/{budget_id}/line-items` | List line items |
| GET | `/budgets/{budget_id}/variance` | Get budget variance |
| GET | `/budgets/{budget_id}/alerts` | Get budget alerts |

### Household Router (`/households`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/households` | Create household |
| GET | `/households` | List households |
| GET | `/households/{household_id}` | Get household by ID |
| DELETE | `/households/{household_id}` | Delete household |
| POST | `/households/{household_id}/members` | Add member |
| GET | `/households/{household_id}/members` | List members |
| DELETE | `/households/{household_id}/members/{member_id}` | Remove member |
| GET | `/households/{household_id}/net-worth` | Look-through net worth |

### Ownership Router (`/ownership`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ownership` | Create ownership edge |
| GET | `/ownership` | List ownership edges |
| GET | `/ownership/{ownership_id}` | Get edge by ID |
| DELETE | `/ownership/{ownership_id}` | Delete edge |
| GET | `/ownership/entities/{entity_id}/tree` | Get ownership tree |
| GET | `/ownership/entities/{entity_id}/look-through-net-worth` | Look-through net worth |
| GET | `/ownership/entities/{entity_id}/capital-accounts` | Partnership capital accounts |

## Common Request/Response Examples

### Create Entity

**Request:**
```json
POST /entities
{
  "name": "Smith Family LLC",
  "entity_type": "llc",
  "tax_treatment": "pass_through",
  "jurisdiction": "Delaware"
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Smith Family LLC",
  "entity_type": "llc",
  "is_active": true,
  "created_at": "2026-01-29T14:30:00Z"
}
```

### Create Transaction

**Request:**
```json
POST /transactions
{
  "description": "Office rent payment",
  "transaction_date": "2026-01-29",
  "entries": [
    {"account_id": "...", "debit_amount": "5000.00", "credit_amount": "0.00"},
    {"account_id": "...", "debit_amount": "0.00", "credit_amount": "5000.00"}
  ]
}
```

### Error Response

```json
{
  "detail": "Entity not found"
}
```

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful delete) |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 422 | Unprocessable Entity |
| 500 | Internal Server Error |
