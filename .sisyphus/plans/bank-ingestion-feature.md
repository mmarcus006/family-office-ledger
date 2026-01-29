# Bank Transaction Ingestion Feature

## TL;DR

> **Quick Summary**: Add bank-specific parsers and ingestion service to automatically import transactions from CITI, UBS, and Morgan Stanley files, classify them into 17 transaction types, auto-create entities/accounts, and book proper double-entry journal entries.
> 
> **Deliverables**:
> - Bank-specific parsers (CITI CSV, UBS CSV, Morgan Stanley Excel)
> - Transaction type classification engine (17 types from Sample_JE.csv)
> - Transaction ingestion service with entity/account auto-creation
> - Investment transaction handling (creates tax lots for buys/sells)
> - Transfer matching between accounts
> 
> **Estimated Effort**: Large (6-8 hours)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5

---

## Context

### Original Request
Ingest transaction files from three different banks (CITI, UBS, Morgan Stanley) and:
- Auto-create entities from account names
- Create accounts under appropriate entities
- Classify each transaction into one of 17 types using keyword/pattern matching
- Book all transactions with proper double-entry per Sample_JE.csv patterns
- Handle investment transactions (create/dispose tax lots)
- Recognize and match transfers between accounts

### File Analysis

**CITI CSV (144 transactions, 6 accounts):**
- Columns: Date Range, Account Number, Account Description, Description, Type, Amount, CUSIP, Quantity, Symbol, etc.
- Account types: Checking, Savings, Brokerage
- Amount format: "(217.34)" for negatives
- Account Number format: `=T("XXXXXX9251")`

**UBS CSV (758 transactions, 6 accounts):**
- Filter line on row 1, header on row 2
- Columns: Account Number, Date, Activity, Description, Symbol, Cusip, Type, Quantity, Price, Amount, Friendly Account Name
- Account types: All brokerage
- Activity types: DEBIT CARD, BOUGHT, SOLD, WITHDRAWAL, DEPOSIT

**Morgan Stanley Excel (216 transactions, 18 accounts):**
- Metadata rows 1-6, header on row 7
- Columns: Activity Date, Transaction Date, Account, Activity, Description, Symbol, Cusip, Quantity, Price($), Amount($)
- Account format: "Entity Name - XXXX - XXXX"
- Many LLC and Trust accounts

### Transaction Type Mapping (from Sample_JE.csv)

| # | Type | Direction | Keywords/Patterns | Journal Entry |
|---|------|-----------|-------------------|---------------|
| 1 | INTEREST | + | "INTEREST", "MARGIN INT" | Dr: Cash, Cr: Interest Income |
| 2 | EXPENSE | - | "LEGAL FEE", "PROFESSIONAL" | Dr: Expense, Cr: Cash |
| 3 | TRANSFER | ± | Wire between our accounts | Dr: Cash-Dest, Cr: Cash-Source |
| 4 | TRUST_TRANSFER | ± | Other party contains "TRUST" | Dr/Cr: Due From Trust + Cash |
| 5 | CONTRIBUTION/DISTRIBUTION | ± | "CAPITAL CALL", fund names | Dr/Cr: Investment-Fund + Cash |
| 6 | CONTRIBUTION_TO_ENTROPY | + | Member contribution | Dr: Cash, Cr: Member's Capital |
| 7 | LOAN | - | "LOAN TO", related party | Dr: Notes Receivable, Cr: Cash |
| 8 | LOAN_REPAYMENT | + | "LOAN REPAYMENT" | Dr: Cash, Cr: Notes Rec + Interest |
| 9 | PURCHASE_QSBS | - | Investment + QSBS eligible | Dr: Investment-QSBS, Cr: Cash |
| 10 | PURCHASE_NON_QSBS | - | Investment + NOT QSBS | Dr: Investment-NonQSBS, Cr: Cash |
| 11 | PURCHASE_OZ_FUND | - | "OZ FUND", "OPPORTUNITY ZONE" | Dr: Investment-OZ, Cr: Cash |
| 12 | SALE_QSBS | + | Sale + QSBS position | Dr: Cash, Cr: Investment + Gain |
| 13 | SALE_NON_QSBS | + | Sale + Non-QSBS position | Dr: Cash, Cr: Investment + Gain/Loss |
| 14 | LIQUIDATION | + | "LIQUIDATION", "ESCROW" | Dr: Cash, Cr: Investment + Gain/Loss |
| 15 | BROKER_FEES | - | "BROKER FEE", "SECONDARY" | Dr: Investment (capitalize), Cr: Cash |
| 16 | RETURN_OF_FUNDS | + | "REFUND", "CANCELLED" | Dr: Cash, Cr: Investment |
| 17 | PUBLIC_MARKET | ± | T-Bills, Crypto | Varies by sub-type |
| 18 | UNCLASSIFIED | ± | No match | Dr/Cr: Suspense + Cash |

### Research Findings
- Existing CSV/OFX parsers in `/src/family_office_ledger/parsers/` provide patterns
- `LedgerService.post_transaction()` validates balance and saves
- `LotMatchingService.execute_sale()` handles tax lot disposal
- Repository interfaces support all CRUD operations
- Domain models: Entity (EntityType enum), Account (AccountType enum), Transaction, Entry, TaxLot

---

## Work Objectives

### Core Objective
Enable automatic ingestion of bank transaction files with intelligent transaction classification, entity/account creation, and proper double-entry booking following the patterns defined in Sample_JE.csv.

### Concrete Deliverables
1. `src/family_office_ledger/domain/value_objects.py` - Add TransactionType enum (18 types)
2. `src/family_office_ledger/parsers/bank_parsers.py` - Bank-specific parsers
3. `src/family_office_ledger/services/transaction_classifier.py` - Rules engine for classification
4. `src/family_office_ledger/services/ingestion.py` - Ingestion service
5. `tests/test_bank_parsers.py` - Parser tests
6. `tests/test_transaction_classifier.py` - Classification tests
7. `tests/test_ingestion_service.py` - Ingestion service tests
8. Updated `parsers/__init__.py` and `services/__init__.py`

### Definition of Done
- [x] All three bank files parse successfully
- [x] Transactions classified into correct types (manual spot-check 20 samples)
- [x] Entities auto-created from account names (LLCs, Trusts)
- [x] Accounts created under correct entities
- [x] All transactions booked with balanced double-entry
- [x] Investment buys/sells create/dispose tax lots
- [x] `uv run pytest` passes
- [x] `uv run mypy src/` passes

### Must Have
- Parse CITI, UBS, Morgan Stanley formats
- Classify transactions into 17+ types
- Auto-create entities from account names
- Book transactions as balanced double-entry per Sample_JE.csv
- Create tax lots for investment purchases
- Dispose tax lots for investment sales

### Must NOT Have (Guardrails)
- Do NOT create duplicate entities/accounts on re-import
- Do NOT book unbalanced transactions
- Do NOT modify existing domain models (except adding TransactionType enum)
- Do NOT use pandas or heavy external libraries (except openpyxl for Excel)
- Do NOT hardcode account IDs - use get_or_create pattern

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **User wants tests**: YES (TDD)
- **Framework**: pytest

### Test Coverage Requirements
- Parser tests: Each bank format, edge cases, invalid data
- Classification tests: Each of 18 transaction types
- Ingestion tests: Entity creation, account creation, transaction booking
- Integration test: Full file ingestion end-to-end

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Add TransactionType enum to value_objects.py
└── Task 2: Create bank-specific parsers

Wave 2 (After Wave 1):
├── Task 3: Create transaction classifier with rules engine
└── (Task 2 must complete first)

Wave 3 (After Wave 2):
├── Task 4: Create ingestion service
└── (Task 3 must complete first)

Wave 4 (After Wave 3):
├── Task 5: Integration testing with real files
└── Task 6: Update exports and CLI
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 3 | 2 |
| 2 | None | 3, 4 | 1 |
| 3 | 1, 2 | 4 | None |
| 4 | 2, 3 | 5, 6 | None |
| 5 | 4 | None | 6 |
| 6 | 4 | None | 5 |

---

## TODOs

- [x] 1. Add TransactionType Enum

  **What to do**:
  - Add `TransactionType` enum to `src/family_office_ledger/domain/value_objects.py`
  - Include all 18 transaction types from Sample_JE.csv mapping
  - Add to `__all__` export in domain module

  **TransactionType Enum Values**:
  ```python
  class TransactionType(str, Enum):
      INTEREST = "interest"
      EXPENSE = "expense"
      TRANSFER = "transfer"
      TRUST_TRANSFER = "trust_transfer"
      CONTRIBUTION_DISTRIBUTION = "contribution_distribution"
      CONTRIBUTION_TO_ENTITY = "contribution_to_entity"
      LOAN = "loan"
      LOAN_REPAYMENT = "loan_repayment"
      PURCHASE_QSBS = "purchase_qsbs"
      PURCHASE_NON_QSBS = "purchase_non_qsbs"
      PURCHASE_OZ_FUND = "purchase_oz_fund"
      SALE_QSBS = "sale_qsbs"
      SALE_NON_QSBS = "sale_non_qsbs"
      LIQUIDATION = "liquidation"
      BROKER_FEES = "broker_fees"
      RETURN_OF_FUNDS = "return_of_funds"
      PUBLIC_MARKET = "public_market"
      UNCLASSIFIED = "unclassified"
  ```

  **Must NOT do**:
  - Do not modify any other enums
  - Do not change existing code structure

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:
  - `src/family_office_ledger/domain/value_objects.py:16-30` - Existing enum patterns (EntityType, AccountType)
  - `/mnt/c/Users/Miller/OneDrive/Documents/Sample_JE.csv` - Transaction type definitions

  **Acceptance Criteria**:
  - [x] TransactionType enum added with all 18 values
  - [x] Enum follows existing pattern (str, Enum)
  - [x] `uv run pytest tests/test_value_objects.py -v` → PASS
  - [x] `uv run mypy src/family_office_ledger/domain/value_objects.py` → no errors

  **Commit**: YES
  - Message: `feat(domain): add TransactionType enum for bank ingestion classification`
  - Files: `src/family_office_ledger/domain/value_objects.py`

---

- [x] 2. Create Bank-Specific Parsers

  **What to do**:
  - Create `src/family_office_ledger/parsers/bank_parsers.py` with:
    - `ParsedTransaction` dataclass with standardized fields
    - `BankParser` abstract base class
    - `CitiParser` - handles CITI CSV format
    - `UBSParser` - handles UBS CSV format (skip filter line)
    - `MorganStanleyParser` - handles Excel format (skip metadata rows)
    - `BankParserFactory` - auto-detect and return correct parser
  - Create `tests/test_bank_parsers.py` with TDD tests

  **ParsedTransaction Dataclass**:
  ```python
  @dataclass
  class ParsedTransaction:
      import_id: str              # Unique ID for dedup
      date: date                  # Transaction date
      description: str            # Bank description
      amount: Decimal             # Positive=credit, Negative=debit
      account_number: str         # Bank account number
      account_name: str           # Friendly account name
      other_party: str | None     # Counterparty name (if available)
      symbol: str | None          # Security symbol (if investment)
      cusip: str | None           # CUSIP (if investment)
      quantity: Decimal | None    # Shares (if investment)
      price: Decimal | None       # Price per share (if investment)
      activity_type: str | None   # Bank's activity type (BOUGHT, SOLD, etc.)
      raw_data: dict              # Original row for debugging
  ```

  **Must NOT do**:
  - Do not use pandas or heavy external libraries
  - Do not modify existing parser files
  - Do not add transaction type classification here (that's Task 3)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3, Task 4
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `src/family_office_ledger/parsers/csv_parser.py` - Existing CSV parser pattern with column detection
  - `src/family_office_ledger/parsers/ofx_parser.py` - OFX parser pattern

  **Data References**:
  - `/mnt/c/Users/Miller/Downloads/Transactions_CITI_01_28_2026_YTD.csv`
  - `/mnt/c/Users/Miller/Downloads/Transactions_UBS_01_28_2026_YTD.csv`
  - `/mnt/c/Users/Miller/Downloads/Transactions_MS_01_28_2026_YTD.xlsx`

  **CITI CSV Format**:
  ```
  Date Range,Account Number,Account Description,Description,Type,Amount (Reporting CCY),CUSIP,Quantity,Symbol...
  2026-01-28,=T("XXXXXX9251"),"Citigold Interest Checking","ACH ELECTRONIC DEBIT...","Cash Withdrawal","(217.34)"...
  ```
  - Account Number needs regex to extract from `=T("XXXXXX9251")`
  - Amount uses parentheses for negatives: `(217.34)` → `-217.34`

  **UBS CSV Format**:
  ```
  "Filtered by - Date: 01/01/2025-01/28/2026, Money Market: Exclude"
  Account Number,Date,Activity,Description,Symbol,Cusip,Type,Quantity,Price,Amount,Friendly Account Name
  V8 03825,01/28/2026,DEBIT CARD,VENMO *Eva Apor,,,Cash,,,-400.00,Atlantic Blue
  ```
  - Skip row 1 (filter metadata)
  - Header on row 2

  **Morgan Stanley Excel Format** (header on row 7):
  ```
  Activity Date,Transaction Date,Account,Activity,Description,Symbol,Cusip,Quantity,Price($),Amount($)
  01/28/2026,01/28/2026,Kaneda - 8231 - 8231,CASH TRANSFER,CASH ADJUSTMENT...,,,0,0,-110113.71
  ```
  - Skip rows 1-6 (metadata)
  - Header on row 7
  - Use openpyxl to read Excel

  **Acceptance Criteria**:
  - [x] `CitiParser.parse()` returns list of ParsedTransaction
  - [x] `UBSParser.parse()` skips filter line, parses correctly
  - [x] `MorganStanleyParser.parse()` handles Excel format
  - [x] `BankParserFactory.get_parser()` auto-detects file type by extension
  - [x] All parsers extract: date, description, amount, account_number, account_name
  - [x] Investment fields populated when available: symbol, cusip, quantity, price
  - [x] Import IDs are deterministic (same file → same IDs)
  - [x] `uv run pytest tests/test_bank_parsers.py -v` → PASS
  - [x] `uv run mypy src/family_office_ledger/parsers/bank_parsers.py` → no errors

  **Commit**: YES
  - Message: `feat(parsers): add bank-specific parsers for CITI, UBS, Morgan Stanley`
  - Files: `src/family_office_ledger/parsers/bank_parsers.py`, `tests/test_bank_parsers.py`

---

- [x] 3. Create Transaction Classifier

  **What to do**:
  - Create `src/family_office_ledger/services/transaction_classifier.py` with:
    - `TransactionClassifier` class
    - `classify(parsed_txn: ParsedTransaction) -> TransactionType` method
    - Ordered list of classification rules
    - Each rule: (condition_func, transaction_type)
  - Create `tests/test_transaction_classifier.py` with test for each type

  **Classification Rules (Priority Order)**:
  
  1. **INTEREST**: Keywords ["INTEREST", "MARGIN INT", "INT PAYMENT"], amount > 0, no CUSIP
  2. **EXPENSE**: Keywords ["LEGAL FEE", "PROFESSIONAL", "ACCOUNTING", "ADVISORY"], amount < 0
  3. **TRUST_TRANSFER**: other_party contains "TRUST"
  4. **LOAN**: Keywords ["LOAN TO", "NOTE RECEIVABLE", "ADVANCE TO"], amount < 0
  5. **LOAN_REPAYMENT**: Keywords ["LOAN REPAYMENT", "NOTE REPAYMENT"], amount > 0
  6. **BROKER_FEES**: Keywords ["BROKER FEE", "TRANSACTION FEE", "SECONDARY MARKET"], amount < 0
  7. **RETURN_OF_FUNDS**: Keywords ["REFUND", "RETURN OF FUNDS", "CANCELLED"], amount > 0
  8. **PURCHASE_OZ_FUND**: Keywords ["OZ FUND", "OPPORTUNITY ZONE"], amount < 0
  9. **CONTRIBUTION_DISTRIBUTION**: other_party contains ["LP", "FUND", "CAPITAL", "PARTNERS"]
  10. **CONTRIBUTION_TO_ENTITY**: Keywords ["CAPITAL CONTRIBUTION", "MEMBER CONTRIBUTION"], amount > 0
  11. **PUBLIC_MARKET**: Keywords ["TREASURY", "T-BILL", "CRYPTO", "HYPERLIQUID", "BITCOIN"]
  12. **LIQUIDATION**: Keywords ["LIQUIDATION", "ESCROW RELEASE", "WIND DOWN"]
  13. **SALE_***: activity_type in ["SOLD", "SALE", "REDEMPTION"] AND has CUSIP/symbol
      - SALE_QSBS if security.is_qsbs_eligible (requires security lookup)
      - SALE_NON_QSBS otherwise
  14. **PURCHASE_***: activity_type in ["BOUGHT", "PURCHASE"] OR (amount < 0 AND has CUSIP/symbol)
      - PURCHASE_QSBS if security.is_qsbs_eligible
      - PURCHASE_NON_QSBS otherwise
  15. **TRANSFER**: Keywords ["WIRE TRANSFER", "ACH TRANSFER", "INTERNAL TRANSFER"]
      - Post-processing step will match pairs
  16. **UNCLASSIFIED**: Default fallback

  **Security Lookup Interface**:
  ```python
  class SecurityLookup(Protocol):
      def is_qsbs_eligible(self, symbol: str | None, cusip: str | None) -> bool | None:
          """Returns True/False if security found, None if not found"""
          ...
  ```

  **Must NOT do**:
  - Do not hardcode account IDs
  - Do not book transactions (that's ingestion service)
  - Do not access repositories directly (use SecurityLookup interface)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 4
  - **Blocked By**: Task 1, Task 2

  **References**:
  - `src/family_office_ledger/domain/value_objects.py` - TransactionType enum (from Task 1)
  - `src/family_office_ledger/parsers/bank_parsers.py` - ParsedTransaction (from Task 2)
  - `/mnt/c/Users/Miller/OneDrive/Documents/Sample_JE.csv` - Transaction type patterns
  - `.sisyphus/drafts/bank-ingestion-rules.md` - Detailed classification rules

  **Acceptance Criteria**:
  - [x] `TransactionClassifier.classify()` returns correct TransactionType for each scenario
  - [x] Test case for each of 18 transaction types
  - [x] INTEREST: "INTEREST PAYMENT" with positive amount → INTEREST
  - [x] EXPENSE: "LEGAL FEE" with negative amount → EXPENSE
  - [x] PURCHASE_QSBS: BOUGHT + CUSIP + QSBS eligible → PURCHASE_QSBS
  - [x] UNCLASSIFIED: Unknown pattern → UNCLASSIFIED
  - [x] `uv run pytest tests/test_transaction_classifier.py -v` → PASS
  - [x] `uv run mypy src/family_office_ledger/services/transaction_classifier.py` → no errors

  **Commit**: YES
  - Message: `feat(services): add transaction classifier with 18 type rules engine`
  - Files: `src/family_office_ledger/services/transaction_classifier.py`, `tests/test_transaction_classifier.py`

---

- [x] 4. Create Ingestion Service

  **What to do**:
  - Create `src/family_office_ledger/services/ingestion.py` with:
    - `IngestionService` class with dependencies:
      - `entity_repo: EntityRepository`
      - `account_repo: AccountRepository`
      - `security_repo: SecurityRepository`
      - `ledger_service: LedgerService`
      - `lot_matching_service: LotMatchingService`
      - `transaction_classifier: TransactionClassifier`
    - `ingest_file(file_path, default_entity_name)` - main entry point
    - `_get_or_create_entity(account_name)` - auto-create entities
    - `_get_or_create_account(entity_id, name, account_type, sub_type)` - auto-create accounts
    - `_book_transaction(parsed_txn, txn_type, source_account)` - create journal entry
    - `_handle_investment_purchase(parsed_txn, txn_type, account)` - create tax lots
    - `_handle_investment_sale(parsed_txn, txn_type, account)` - dispose tax lots
  - Create `tests/test_ingestion_service.py`

  **Entity Detection Logic**:
  ```python
  ENTITY_PATTERNS = {
      "LLC": EntityType.LLC,
      "L.L.C.": EntityType.LLC,
      "HOLDINGS": EntityType.HOLDING_CO,
      "INVESTMENTS": EntityType.HOLDING_CO,
      "TRUST": EntityType.TRUST,
      "PARTNERSHIP": EntityType.PARTNERSHIP,
      "LP": EntityType.PARTNERSHIP,
  }
  
  def detect_entity_type(name: str) -> EntityType:
      for pattern, entity_type in ENTITY_PATTERNS.items():
          if pattern in name.upper():
              return entity_type
      return EntityType.INDIVIDUAL  # Default
  ```

  **Account Name Parsing**:
  - "ENTROPY MANAGEMENT GROUP - 7111" → Entity: "ENTROPY MANAGEMENT GROUP", Account: "7111"
  - "Kaneda - 8231 - 8231" → Entity: "Kaneda Investments LLC" (lookup), Account: "8231"
  - "Atlantic Blue" → Entity: "Atlantic Blue", Account: "Main"

  **Double-Entry Booking by TransactionType**:
  
  | Type | Debit Account | Credit Account | Tax Lot Action |
  |------|---------------|----------------|----------------|
  | INTEREST | Cash (source) | Interest Income | None |
  | EXPENSE | Expense (by keyword) | Cash (source) | None |
  | TRANSFER | Cash (dest) | Cash (source) | None |
  | TRUST_TRANSFER | Due From/To Trust | Cash (source) | None |
  | CONTRIBUTION_DISTRIBUTION | Investment-Fund / Cash | Cash / Investment | None |
  | CONTRIBUTION_TO_ENTITY | Cash (source) | Member's Capital | None |
  | LOAN | Notes Receivable | Cash (source) | None |
  | LOAN_REPAYMENT | Cash (source) | Notes Rec + Interest | None |
  | PURCHASE_QSBS | Investment-QSBS | Cash (source) | CREATE |
  | PURCHASE_NON_QSBS | Investment-NonQSBS | Cash (source) | CREATE |
  | PURCHASE_OZ_FUND | Investment-OZ | Cash (source) | CREATE |
  | SALE_QSBS | Cash (source) | Investment + Gain-QSBS | DISPOSE |
  | SALE_NON_QSBS | Cash (source) | Investment + Gain/Loss | DISPOSE |
  | LIQUIDATION | Cash (source) | Investment + Gain/Loss | DISPOSE ALL |
  | BROKER_FEES | Investment (capitalize) | Cash (source) | UPDATE BASIS |
  | RETURN_OF_FUNDS | Cash (source) | Investment | UPDATE BASIS |
  | PUBLIC_MARKET | Varies | Varies | Varies |
  | UNCLASSIFIED | Cash / Suspense | Suspense / Cash | None |

  **Must NOT do**:
  - Do not create duplicate entities/accounts (use get_or_create pattern)
  - Do not book unbalanced transactions
  - Do not modify existing services
  - Do not hardcode account names - parameterize via config

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 5, Task 6
  - **Blocked By**: Task 2, Task 3

  **References**:

  **Pattern References**:
  - `src/family_office_ledger/services/ledger.py:post_transaction()` - Transaction posting pattern
  - `src/family_office_ledger/services/lot_matching.py:execute_sale()` - Tax lot disposal
  - `src/family_office_ledger/repositories/interfaces.py` - Repository interfaces

  **Domain References**:
  - `src/family_office_ledger/domain/entities.py:Entity,Account,Position,Security`
  - `src/family_office_ledger/domain/transactions.py:Transaction,Entry,TaxLot`
  - `src/family_office_ledger/domain/value_objects.py:EntityType,AccountType,Money,TransactionType`

  **JE Mapping Reference**:
  - `/mnt/c/Users/Miller/OneDrive/Documents/Sample_JE.csv` - Complete JE patterns

  **Acceptance Criteria**:
  - [x] `IngestionService.ingest_file()` parses and books all transactions
  - [x] Entities auto-created for LLCs, Trusts, Holdings
  - [x] Accounts created under correct entities with correct AccountType
  - [x] No duplicate entities/accounts on re-import (idempotent)
  - [x] All transactions balanced (debits == credits)
  - [x] Investment purchases create TaxLot records
  - [x] Investment sales dispose TaxLot records via LotMatchingService
  - [x] UNCLASSIFIED transactions flagged for review
  - [x] `uv run pytest tests/test_ingestion_service.py -v` → PASS
  - [x] `uv run mypy src/family_office_ledger/services/ingestion.py` → no errors

  **Commit**: YES
  - Message: `feat(services): add transaction ingestion service with auto-entity creation and JE booking`
  - Files: `src/family_office_ledger/services/ingestion.py`, `tests/test_ingestion_service.py`

---

- [x] 5. Integration Test with Real Files

  **What to do**:
  - Create integration test that ingests all three bank files
  - Verify correct entity count
  - Verify correct account count
  - Verify transaction totals match file totals
  - Spot-check 20 transactions for correct classification
  - Test idempotency (re-import doesn't duplicate)

  **Must NOT do**:
  - Do not commit test data files to repo

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 6)
  - **Blocks**: None
  - **Blocked By**: Task 4

  **References**:
  - Task 2, Task 3, Task 4 outputs
  - Test files at `/mnt/c/Users/Miller/Downloads/Transactions_*.csv|xlsx`

  **Acceptance Criteria**:
  ```bash
  # Agent runs:
  cd /home/miller/projects/quicken
  uv run python -c "
  from family_office_ledger.services.ingestion import IngestionService
  from family_office_ledger.repositories.sqlite import SQLiteDatabase
  
  # Use SQLite for integration test
  db = SQLiteDatabase(':memory:')
  db.initialize()
  
  # Create service with all dependencies
  svc = IngestionService(...)
  
  # Ingest all files
  results_citi = svc.ingest_file('/mnt/c/Users/Miller/Downloads/Transactions_CITI_01_28_2026_YTD.csv')
  results_ubs = svc.ingest_file('/mnt/c/Users/Miller/Downloads/Transactions_UBS_01_28_2026_YTD.csv')
  results_ms = svc.ingest_file('/mnt/c/Users/Miller/Downloads/Transactions_MS_01_28_2026_YTD.xlsx')
  
  # Verify counts
  print(f'CITI: {results_citi.transaction_count} transactions, {results_citi.entity_count} entities')
  print(f'UBS: {results_ubs.transaction_count} transactions')
  print(f'MS: {results_ms.transaction_count} transactions')
  
  # Print classification breakdown
  for txn_type, count in results_citi.type_breakdown.items():
      print(f'  {txn_type}: {count}')
  "
  ```
  - [x] All files ingest without errors
  - [x] Entity count matches unique entity names (~20+)
  - [x] Account count matches unique accounts (30)
  - [x] Transaction count matches file rows (~1100)
  - [x] Spot-check shows correct classification

  **Commit**: YES
  - Message: `test(integration): verify bank file ingestion end-to-end`

---

- [x] 6. Update Exports and CLI

  **What to do**:
  - Update `src/family_office_ledger/parsers/__init__.py` to export:
    - `BankParserFactory`, `ParsedTransaction`
    - `CitiParser`, `UBSParser`, `MorganStanleyParser`
  - Update `src/family_office_ledger/services/__init__.py` to export:
    - `IngestionService`, `TransactionClassifier`
  - Update `src/family_office_ledger/domain/value_objects.py` exports for `TransactionType`
  - Add CLI command: `fol ingest <file_path> [--default-entity NAME]`

  **CLI Command**:
  ```python
  @app.command()
  def ingest(
      file_path: Path,
      default_entity: str = typer.Option("Unknown", help="Default entity for unrecognized accounts"),
  ):
      """Ingest bank transaction file."""
      svc = IngestionService(...)
      result = svc.ingest_file(str(file_path), default_entity)
      typer.echo(f"Ingested {result.transaction_count} transactions")
      typer.echo(f"Created {result.entity_count} entities, {result.account_count} accounts")
  ```

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 5)
  - **Blocks**: None
  - **Blocked By**: Task 4

  **Acceptance Criteria**:
  - [x] `from family_office_ledger.parsers import BankParserFactory` works
  - [x] `from family_office_ledger.services import IngestionService` works
  - [x] `from family_office_ledger.domain.value_objects import TransactionType` works
  - [x] `uv run fol ingest --help` shows command
  - [x] All tests pass: `uv run pytest`
  - [x] Type check passes: `uv run mypy src/`

  **Commit**: YES
  - Message: `chore: update exports and add ingest CLI command`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(domain): add TransactionType enum` | value_objects.py | pytest, mypy |
| 2 | `feat(parsers): add bank-specific parsers` | bank_parsers.py, test_bank_parsers.py | pytest, mypy |
| 3 | `feat(services): add transaction classifier` | transaction_classifier.py, test_*.py | pytest, mypy |
| 4 | `feat(services): add ingestion service` | ingestion.py, test_ingestion_service.py | pytest, mypy |
| 5 | `test(integration): bank file ingestion` | test updates | manual verification |
| 6 | `chore: update exports and CLI` | __init__.py, cli.py | pytest, mypy |

---

## Success Criteria

### Verification Commands
```bash
# Parse and verify file counts
cd /home/miller/projects/quicken
uv run python -c "
from family_office_ledger.parsers.bank_parsers import BankParserFactory
citi = BankParserFactory.parse_file('/mnt/c/Users/Miller/Downloads/Transactions_CITI_01_28_2026_YTD.csv')
ubs = BankParserFactory.parse_file('/mnt/c/Users/Miller/Downloads/Transactions_UBS_01_28_2026_YTD.csv')
ms = BankParserFactory.parse_file('/mnt/c/Users/Miller/Downloads/Transactions_MS_01_28_2026_YTD.xlsx')
print(f'CITI: {len(citi)} transactions')
print(f'UBS: {len(ubs)} transactions')
print(f'MS: {len(ms)} transactions')
print(f'Total: {len(citi) + len(ubs) + len(ms)}')
"
# Expected: CITI ~144, UBS ~758, MS ~216, Total ~1118

# Full test suite
uv run pytest --tb=short
# Expected: All tests pass

# Type check
uv run mypy src/
# Expected: No errors

# CLI test
uv run fol ingest /mnt/c/Users/Miller/Downloads/Transactions_CITI_01_28_2026_YTD.csv
# Expected: Success message with counts
```

### Final Checklist
- [x] All three bank files parse correctly
- [x] Transactions classified into 18 types correctly
- [x] Entities auto-created from account names
- [x] Accounts mapped to correct entities
- [x] Transactions booked with balanced entries per Sample_JE.csv
- [x] Investment transactions create/dispose tax lots
- [x] No duplicates on re-import
- [x] All tests pass
- [x] mypy clean
