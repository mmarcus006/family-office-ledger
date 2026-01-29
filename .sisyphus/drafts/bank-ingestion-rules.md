# Draft: Bank Transaction Ingestion - Transaction Type Detection Rules

## Requirements (confirmed)

1. **Parse three bank formats**: CITI CSV, UBS CSV, Morgan Stanley Excel
2. **Auto-create entities**: Extract from account names (LLC, Trust, Holdings patterns)
3. **Auto-create accounts**: Map bank account numbers to ledger accounts
4. **Classify transactions**: Use 17 transaction types from Sample_JE.csv
5. **Book double-entry**: Create balanced journal entries per type
6. **Create tax lots**: For investment purchases (QSBS, Non-QSBS, OZ Fund)
7. **Handle unclassified**: Mark as UNCLASSIFIED for manual review

## Transaction Type Detection Rules

### Source Data
- **Training data**: Kaneda Bank Transactions workbook with Custom_Transaction_Type column
- **Reference mappings**: Sample_JE.csv with complete journal entry patterns
- **Entity mappings**: Entropy workbook Acct_Map and CITI_WIRE_MAPPING sheets

### Detection Logic (Priority Order)

#### 1. INTEREST
**Keywords**: "INTEREST", "MARGIN INT", "INTEREST SHARING", "INT PAYMENT"
**Direction**: Positive (credit to bank account)
**No CUSIP/Symbol required**

```
Debit:  Cash - Bank
Credit: Interest Income
```

#### 2. EXPENSE
**Keywords**: "LEGAL FEE", "PROFESSIONAL FEE", "ACCOUNTING", "ADVISORY", "MANAGEMENT FEE"
**Direction**: Negative (debit from bank account)
**No CUSIP/Symbol required**
**Other Party**: Law firms, accounting firms (GCA LAW, PARTRIDGE SNOW, etc.)

```
Debit:  Legal & Professional Fees (Expense)
Credit: Cash - Bank
```

#### 3. TRANSFER (Internal between our accounts)
**Keywords**: "WIRE TRANSFER", "ACH TRANSFER", "INTERNAL TRANSFER"
**Indicators**:
- Equal and opposite amounts on same date across two accounts
- Sender AND receiver are both in our entity list
- Description contains "WIRE FROM [our entity]" or "WIRE TO [our entity]"

```
Debit:  Cash - Destination Account
Credit: Cash - Source Account
```

**Post-processing**: Match pairs by date + amount + wire direction

#### 4. TRUST_TRANSFER
**Keywords**: "WIRE TO TRUST", "WIRE FROM TRUST", "TRUST DISTRIBUTION"
**Indicators**:
- Other party contains "TRUST" (e.g., "THE KANEDA TRUST", "THE KETOV TRUST", "THE IKIGAI TRUST")
- One party is Trust, other is LLC/Holdings

```
If sending TO trust (negative amount):
  Debit:  Due From Trust (Asset)
  Credit: Cash - Bank

If receiving FROM trust (positive amount):
  Debit:  Cash - Bank
  Credit: Due From Trust (Asset)
```

#### 5. CONTRIBUTION/DISTRIBUTION (Fund capital calls/distributions)
**Keywords**: "CAPITAL CALL", "CAPITAL CONTRIBUTION", "DISTRIBUTION", "FUND DISTRIBUTION"
**Indicators**:
- Other party is a fund (contains "LP", "FUND", "CAPITAL", "PARTNERS")
- Examples: "ZIGG CAPITAL I LP", "BV SOUTH SLC OZ FUND"

```
If capital call (negative amount):
  Debit:  Investment - Fund (Asset)
  Credit: Cash - Bank

If distribution (positive amount):
  Debit:  Cash - Bank
  Credit: Investment - Fund (reduces basis)
```

#### 6. CONTRIBUTION_TO_ENTROPY (Member contributions)
**Keywords**: "CAPITAL CONTRIBUTION", "MEMBER CONTRIBUTION"
**Indicators**:
- Other party is member/partner name
- Receiving entity is the main holding company

```
Debit:  Cash - Bank
Credit: Member's Capital (Equity)
```

#### 7. LOAN (Extending loans)
**Keywords**: "LOAN TO", "NOTE RECEIVABLE", "ADVANCE TO"
**Direction**: Negative (cash outflow)
**Indicators**:
- Other party is related party or trust
- Not a fund or investment company

```
Debit:  Notes Receivable (Asset)
Credit: Cash - Bank
```

#### 8. LOAN (Repayment)
**Keywords**: "LOAN REPAYMENT", "NOTE REPAYMENT", "REPAYMENT FROM"
**Direction**: Positive (cash inflow)
**Note**: May need to split principal vs interest

```
Debit:  Cash - Bank
Credit: Notes Receivable (principal portion)
Credit: Interest Income (interest portion)
```

#### 9. PURCHASE-QSBS
**Keywords**: "INVESTMENT", "PURCHASE", "STOCK PURCHASE", "SUBSCRIPTION"
**Direction**: Negative
**Indicators**:
- Has CUSIP/Symbol
- Security is flagged as QSBS eligible in our security master
- Or other party is a known QSBS company (startup names)

```
Debit:  Investment - QSBS Stock (Asset)
Credit: Cash - Bank
** CREATE TAX LOT with acquisition_date, cost_per_share **
```

#### 10. PURCHASE-NON-QSBS
**Keywords**: Same as PURCHASE-QSBS
**Direction**: Negative
**Indicators**:
- Has CUSIP/Symbol
- Security is NOT QSBS eligible
- Or other party is LLC (pass-through entity)

```
Debit:  Investment - Non-QSBS (Asset)
Credit: Cash - Bank
** CREATE TAX LOT **
```

#### 11. PURCHASE-OZ-FUND (Opportunity Zone)
**Keywords**: "OZ FUND", "OPPORTUNITY ZONE", "QUALIFIED OPPORTUNITY"
**Direction**: Negative
**Indicators**:
- Other party contains "OZ" or "OPPORTUNITY ZONE"

```
Debit:  Investment - OZ Fund (Asset)
Credit: Cash - Bank
** CREATE TAX LOT with special OZ tracking **
```

#### 12. SALE-QSBS
**Keywords**: "SALE", "REDEMPTION", "EXIT", "LIQUIDATION PROCEEDS"
**Direction**: Positive
**Indicators**:
- Has CUSIP/Symbol matching existing QSBS position
- Other party is company being sold

```
Debit:  Cash - Bank (proceeds)
Credit: Investment - QSBS Stock (at cost basis)
Credit: Gain on Sale - QSBS (gain portion)
** DISPOSE TAX LOTS using LotMatchingService **
```

#### 13. SALE-NON-QSBS
**Keywords**: Same as SALE-QSBS
**Direction**: Positive
**Indicators**:
- Has CUSIP/Symbol matching existing Non-QSBS position

```
Debit:  Cash - Bank (proceeds)
Credit: Investment - Non-QSBS (at cost basis)
Credit: Gain/Loss on Sale (gain/loss)
** DISPOSE TAX LOTS **
```

#### 14. LIQUIDATION
**Keywords**: "LIQUIDATION", "WIND DOWN", "FINAL DISTRIBUTION", "ESCROW RELEASE"
**Direction**: Positive
**Indicators**:
- Company is dissolving/liquidating
- May be escrow release (contains "ACQUIOM", "ESCROW")

```
Debit:  Cash - Bank
Credit: Investment - Portfolio Co (at cost basis)
Credit: Gain/Loss on Liquidation
** DISPOSE ALL REMAINING LOTS FOR SECURITY **
```

#### 15. BROKER-FEES
**Keywords**: "BROKER FEE", "TRANSACTION FEE", "SECONDARY MARKET FEE", "PLACEMENT FEE"
**Direction**: Negative
**Indicators**:
- Other party is broker (BGC, JPM Securities, etc.)
- Related to a recent investment transaction

```
Debit:  Investment - [Related Security] (capitalize to basis)
Credit: Cash - Bank
** ADD TO TAX LOT COST BASIS **
```

#### 16. RETURN OF FUNDS
**Keywords**: "REFUND", "RETURN OF FUNDS", "CANCELLED", "REVERSAL"
**Direction**: Positive
**Indicators**:
- Returning previously paid funds
- May be failed transaction reversal

```
Debit:  Cash - Bank
Credit: Investment - [Related Security] (reduce basis)
```

#### 17. PUBLIC MARKET TRANSACTIONS
**Sub-types**:

**T-Bill Purchase** (negative amount):
```
Keywords: "TREASURY", "T-BILL", "US TREASURIES"
Debit:  Marketable Securities - T-Bills
Credit: Cash - Bank
```

**T-Bill Maturity/Sale** (positive amount):
```
Debit:  Cash - Bank
Credit: Marketable Securities - T-Bills (at cost)
Credit: Interest Income (discount earned)
```

**Crypto/Token Sale** (positive amount):
```
Keywords: "CRYPTO", "TOKEN", "HYPERLIQUID", "BITCOIN", "ETH"
Debit:  Cash - Bank
Credit: Digital Assets - [Token Name]
Credit: Gain/Loss - Digital Assets
```

#### 18. UNCLASSIFIED (Fallback)
**When**: No keywords match, unclear transaction type
**Action**: Flag for manual review

```
Debit:  Cash - Bank (if positive)
Credit: Suspense / Unclassified (Equity)
-- OR --
Debit:  Suspense / Unclassified
Credit: Cash - Bank (if negative)
```

## Entity Detection Logic

### Pattern Matching for Entity Names
```python
ENTITY_PATTERNS = {
    "LLC": EntityType.LLC,
    "L.L.C.": EntityType.LLC,
    "HOLDINGS": EntityType.HOLDING_CO,
    "INVESTMENTS": EntityType.HOLDING_CO,
    "TRUST": EntityType.TRUST,
    "PARTNERSHIP": EntityType.PARTNERSHIP,
    "LP": EntityType.PARTNERSHIP,
    "L.P.": EntityType.PARTNERSHIP,
}
```

### Account Name Parsing Examples
| Bank Account Name | Entity | Account |
|-------------------|--------|---------|
| "ENTROPY MANAGEMENT GROUP - 7111" | Entropy Management Group | Checking 7111 |
| "Kaneda - 8231 - 8231" | Kaneda Investments LLC | Account 8231 |
| "Atlantic Blue" | Atlantic Blue LLC | Main Account |
| "THE KANEDA TRUST" | The Kaneda Trust | Trust Account |
| "Citigold Interest Checking" | [Default Entity] | Citigold Checking |

## Account Mapping from Workbooks

### From Entropy Wires CITI_WIRE_MAPPING:
Maps sender/receiver names and last-four digits to friendly account names

### From Entropy Wires Acct_Map:
Maps account numbers to entities and account types

## Transfer Matching Algorithm

```python
def match_transfers(transactions: list[ParsedTransaction]) -> list[TransferPair]:
    """Match transfers by date + amount + direction"""
    
    # Group by date
    by_date = defaultdict(list)
    for txn in transactions:
        by_date[txn.date].append(txn)
    
    pairs = []
    for date, txns in by_date.items():
        # Find positive/negative pairs with equal absolute amounts
        positives = [t for t in txns if t.amount > 0 and is_wire(t)]
        negatives = [t for t in txns if t.amount < 0 and is_wire(t)]
        
        for pos in positives:
            for neg in negatives:
                if abs(pos.amount) == abs(neg.amount):
                    # Check if both accounts are ours
                    if is_our_entity(pos.account) and is_our_entity(neg.account):
                        pairs.append(TransferPair(source=neg, dest=pos))
    
    return pairs
```

## Open Questions (Resolved)

1. **Auto-detect transaction type**: Use keyword matching + direction + CUSIP presence + counterparty name
2. **Unknown transactions**: Assign UNCLASSIFIED, book to Suspense account, flag for review
3. **Transfer matching**: Same date, equal-opposite amounts, both accounts are ours
4. **Entity ownership**: Use Acct_Map lookups; default to "Unknown Entity" if not found

## Research Findings

### From Domain Models:
- Entity has `entity_type: EntityType` enum (LLC, TRUST, PARTNERSHIP, INDIVIDUAL, HOLDING_CO)
- Account has `account_type: AccountType` (ASSET, LIABILITY, EQUITY, INCOME, EXPENSE)
- Transaction with Entry list must be balanced (debits == credits)
- TaxLot tracks acquisition_date, cost_per_share, remaining_quantity

### From Service Patterns:
- `LedgerService.post_transaction(txn)` validates and saves
- `LotMatchingService.execute_sale()` disposes lots and returns LotDisposition
- Repository interfaces for create/get/update operations

### From Parser Patterns:
- CSVParser has `_generate_import_id()` using SHA256 hash
- Output format: `{"import_id", "date", "description", "amount"}`
- Invalid rows silently skipped

## Technical Decisions

1. **Parser architecture**: Create bank-specific parsers extending base pattern
2. **Transaction type enum**: Add new TransactionType enum to value_objects.py
3. **Rules engine**: Implement as ordered list of pattern matchers
4. **Account creation**: Use get_or_create pattern to avoid duplicates
5. **Tax lot creation**: Only for PURCHASE-* types with securities
