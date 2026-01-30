# Investment Accounting Application: UI/UX Design Research Document

**Version:** 1.0
**Date:** January 2026
**Purpose:** Design patterns and information architecture recommendations for a tax-aware investment accounting application targeting sophisticated investors and family offices

---

## Executive Summary

### Key Findings

After analyzing Kubera, Quicken, Addepar, Sharesight, Portfolio Performance, and adjacent tools, three critical insights emerge:

1. **The market bifurcates between "wealth snapshot" and "accounting depth"** — Kubera excels at aggregation and HNW aesthetics but lacks transaction-level control; Quicken provides accounting depth but with dated UX. No product successfully bridges both.

2. **Tax-awareness is universally treated as a reporting afterthought** — Tax implications (lots, wash sales, holding periods) are surfaced in reports, not integrated into the daily investment view. This represents your largest differentiation opportunity.

3. **Multi-entity management is solved only at institutional scale** — Addepar and family office platforms handle complex structures well, but at price points and complexity levels inappropriate for individual sophisticated investors.

### Recommended Strategic Position

Build "Kubera's elegance + Quicken's depth + tax-first thinking" — a platform where:
- Net worth aggregation is the entry point (Kubera pattern)
- Transaction-level accounting is seamlessly accessible (Quicken pattern)
- Tax implications are surfaced throughout, not siloed (novel pattern)
- Multi-entity support is built-in but not enterprise-complex (Addepar-lite)

### Priority Design Principles

| Principle | Rationale |
|-----------|-----------|
| **Allocation tree as primary structure** | Addepar's Household → Client → Entity → Account model enables ownership tracking, joint accounts, and look-through reporting |
| **Tax implications visible at every layer** | Differentiation; sophisticated users care about after-tax returns |
| **Drill-down, not switch-context** | Household → Client → Entity → Account → Holding → Lot should be continuous navigation |
| **Reconciliation as first-class workflow** | Accounting-grade accuracy requires matching to statements |
| **Sensible defaults with expert overrides** | FIFO by default, but SpecID available; auto-categorize, but allow manual |

---

## Part 1: Pattern Library

### 1.1 Kubera Patterns

| Pattern | Description | Adopt? | Adaptation Notes |
|---------|-------------|--------|------------------|
| **Spreadsheet-style dashboard** | Clean rows with holdings, columns for value/change/allocation | **Steal** | Add tax lot expansion beneath each row |
| **Multi-source aggregation** | 20,000+ bank/brokerage connections via Plaid/Yodlee/Salt Edge | **Steal** | Essential for capturing complete picture |
| **Manual asset entry** | Real estate, vehicles, collectibles tracked alongside liquid assets | **Steal** | Extend with cost basis tracking for non-securities |
| **Life Beat (beneficiary access)** | Dead man's switch for estate planning | **Adapt** | Useful for family office/trust scenarios; implement as "delegate view" |
| **AI import (CSV/PDF/screenshot)** | 2025 feature for automated data entry | **Steal** | Critical for brokerage statement reconciliation |
| **Base currency consolidation** | 100+ currencies with real-time FX | **Steal** | Essential for international holdings |
| **Time-weighted return (TWRR)** | Performance calculation method | **Steal** | Also offer IRR; let user choose |
| **No transaction editing** | View-only; can't modify positions | **Avoid** | Your app needs full transaction control |

### 1.2 Quicken Patterns

| Pattern | Description | Adopt? | Adaptation Notes |
|---------|-------------|--------|------------------|
| **Tax Loss Harvesting Report** | Shows unrealized gains/losses by lot with holding period | **Steal** | Make this a first-class view, not just a report |
| **Account Bar with subtotals** | Grouped accounts showing category totals | **Steal** | Group by entity (Personal, Trust A, LLC B) |
| **In-context report settings** | Filter/date range controls within report view | **Steal** | Avoid modal dialogs; inline controls |
| **Cost basis method awareness** | Tracks FIFO, LIFO, SpecID, Average Cost | **Steal** | Show active method per account with override option |
| **IRR + TWR dual metrics** | Both return calculation methods available | **Steal** | Different use cases; sophisticated users want both |
| **Reconciliation workflow** | Match to brokerage statements | **Adapt** | Needs modernization; see wireframe section |
| **Dense data tables** | Traditional accounting-style layouts | **Avoid** | Use Kubera's visual language instead |

### 1.3 Addepar Patterns

| Pattern | Description | Adopt? | Adaptation Notes |
|---------|-------------|--------|------------------|
| **Allocation tree hierarchy** | Household → Client → Legal Entity → Account → Investment | **Steal** | Core architecture; enables look-through and joint ownership |
| **Financial Graph model** | Nodes are entities, edges are ownership relationships with percentages | **Steal** | Supports complex ownership (50/50 joint accounts, trust beneficiaries) |
| **Householding** | Combine multiple accounts under one allocation strategy | **Steal** | Natural grouping for families; mirrors advisor practice |
| **Look-through reporting** | See underlying holdings across structures | **Steal** | Critical for trust/LLC aggregation |
| **Ownership map visualization** | Interactive tree showing hierarchy with values and percentages | **Steal** | Makes complex structures comprehensible |
| **Customizable dashboards** | Drag-and-drop widget placement | **Adapt** | Offer 3-4 preset layouts, not full customization |
| **Real-time report updates** | Reports reflect current data instantly | **Steal** | No "generate report" button; always live |
| **Asset allocation modeling** | Including illiquid assets | **Steal** | Important for HNW with alternatives |
| **Steep learning curve** | Enterprise complexity | **Avoid** | Your onboarding should be Kubera-fast |

### 1.4 Sharesight Patterns

| Pattern | Description | Adopt? | Adaptation Notes |
|---------|-------------|--------|------------------|
| **Taxable Income Report** | Income broken by local/foreign source | **Steal** | Critical for international holdings |
| **Sold Securities Report** | Realized gains with cost basis methodology | **Steal** | Extend with lot-level detail |
| **20-year corporate action history** | Auto-applied dividends, splits | **Steal** | Eliminates manual entry for historical positions |
| **Accountant sharing** | Secure read-only access to tax reports | **Steal** | Implement as role-based access |
| **Broker import integrations** | Direct connections for trade history | **Steal** | Reduces reconciliation burden |
| **Average cost only** | Limited cost basis methods | **Avoid** | Must support SpecID for tax optimization |

### 1.5 Portfolio Performance Patterns

| Pattern | Description | Adopt? | Adaptation Notes |
|---------|-------------|--------|------------------|
| **XML/CSV/JSON export** | Data portability | **Steal** | Users own their data; enable full export |
| **Multiple price sources** | Yahoo, AlphaVantage, custom | **Steal** | Redundancy for pricing reliability |
| **Desktop-first with mobile companion** | Full features on desktop, view on mobile | **Adapt** | Web-first, but don't over-simplify for mobile |
| **SMA overlays on charts** | Technical analysis indicators | **Skip** | Out of scope for accounting focus |
| **Rebalancing tools** | Target allocation comparison | **Adapt** | Useful but not core; phase 2 feature |

### 1.6 Tax Lot Selection Patterns (Cross-Platform)

| Pattern | Source | Adopt? | Notes |
|---------|--------|--------|-------|
| **Lot picker at sell time** | Schwab, Fidelity | **Steal** | Show lot table with purchase date, basis, gain/loss, holding period |
| **Max 4 lots online limit** | Vanguard | **Avoid** | Artificial constraint; allow unlimited selection |
| **Secondary fallback method** | Schwab | **Steal** | If user doesn't specify, use account default (FIFO/HIFO/etc.) |
| **Pre-trade tax impact preview** | Intelliflo RedBlack | **Steal** | Before confirming sale, show projected tax impact |
| **Lot-level wash sale warning** | TradeLog | **Steal** | Flag lots that would trigger wash sale |

### 1.7 Multi-Entity Patterns (Family Office Software)

| Pattern | Source | Adopt? | Notes |
|---------|--------|--------|-------|
| **Entity type taxonomy** | Asset Vantage | **Steal** | Individual, Trust, LLC, Partnership, S-Corp, Estate, Foundation |
| **Inter-entity transactions** | Asset Vantage, Archway | **Steal** | Track transfers, distributions, capital calls between entities |
| **Beneficial ownership tracking** | Archway | **Adapt** | Show ultimate ownership through nested structures |
| **Multi-entity consolidation** | Sage Intacct | **Steal** | Roll-up views across all entities |
| **Entity-specific tax treatment** | Family office platforms | **Steal** | Different tax rules per entity type (pass-through vs. C-corp) |

---

## Part 2: Proposed Information Architecture

### 2.1 Primary Navigation Structure (Addepar-Inspired Allocation Tree)

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Logo]   Dashboard │ Allocation │ Transactions │ Tax Center │ Reports │ Settings
└─────────────────────────────────────────────────────────────────────┘

├── Dashboard (Net Worth Overview)
│   ├── Total Net Worth (all households)
│   ├── Performance Summary (MTD, YTD, ITD)
│   ├── Asset Allocation Chart
│   ├── Recent Activity Feed
│   └── Tax Alerts (wash sales, holding periods approaching LT)
│
├── Allocation (Ownership Tree - Addepar Model)
│   │
│   ├── [Smith Family Household]                    ← HOUSEHOLD (top level)
│   │   │
│   │   ├── [John Smith]                            ← CLIENT (beneficial owner)
│   │   │   │
│   │   │   ├── Direct Holdings
│   │   │   │   ├── [Fidelity Brokerage]            ← ACCOUNT
│   │   │   │   │   ├── Holdings
│   │   │   │   │   │   ├── [AAPL - 500 shares]     ← INVESTMENT
│   │   │   │   │   │   │   ├── Position Summary
│   │   │   │   │   │   │   ├── Tax Lots (expandable)
│   │   │   │   │   │   │   │   ├── Lot 1: 100sh @ $120, 2021-03-15, LT, +$8,000
│   │   │   │   │   │   │   │   ├── Lot 2: 200sh @ $150, 2022-06-20, LT, +$4,000
│   │   │   │   │   │   │   │   └── Lot 3: 200sh @ $180, 2024-01-10, ST, -$2,000
│   │   │   │   │   │   │   └── Transactions (for this holding)
│   │   │   │   │   │   └── [MSFT - 300 shares]
│   │   │   │   │   └── Transactions (all for this account)
│   │   │   │   └── [Schwab IRA]
│   │   │   │
│   │   │   └── Through Entities
│   │   │       ├── [Smith Family Trust] (50% beneficial)  ← LEGAL ENTITY
│   │   │       │   └── [Schwab Trust Account]
│   │   │       │       └── Holdings...
│   │   │       └── [Smith Investment LLC] (100% owner)
│   │   │           └── [LLC Brokerage Account]
│   │   │               └── Holdings...
│   │   │
│   │   ├── [Jane Smith]                            ← CLIENT
│   │   │   ├── Direct Holdings
│   │   │   │   └── [Vanguard Brokerage]
│   │   │   └── Through Entities
│   │   │       └── [Smith Family Trust] (50% beneficial)
│   │   │
│   │   └── [Joint - John & Jane]                   ← JOINT OWNERSHIP
│   │       └── [Schwab Joint Brokerage]
│   │           └── Holdings...
│   │
│   └── [+ Add Household]
│
├── Transactions (Unified Ledger)
│   ├── Filter: Entity | Account | Type | Date Range | Security
│   ├── Import (CSV, PDF, Broker Connect)
│   ├── Add Manual Transaction
│   └── Reconciliation Queue
│
├── Tax Center
│   ├── Unrealized Gains/Losses (by lot)
│   ├── Realized Gains/Losses (current year)
│   ├── Wash Sale Tracker
│   ├── QSBS Tracker
│   ├── Holding Period Monitor (approaching LT threshold)
│   ├── Tax Loss Harvesting Opportunities
│   └── Estimated Tax Liability
│
├── Reports
│   ├── Performance Reports
│   │   ├── Time-Weighted Return
│   │   └── Internal Rate of Return
│   ├── Tax Reports
│   │   ├── Schedule D Preview
│   │   ├── Form 8949 Preview
│   │   ├── Taxable Income Summary
│   │   └── QSBS Eligibility Report
│   ├── Statements
│   │   ├── Net Worth Statement
│   │   ├── Asset Allocation Report
│   │   └── Holdings Report
│   └── Custom Report Builder
│
└── Settings
    ├── Entities (add/edit entity details)
    ├── Accounts (add/edit accounts, connections)
    ├── Tax Settings (default cost basis methods, tax rates)
    ├── Users & Sharing (accountant access, family members)
    ├── Import/Export
    └── Preferences
```

### 2.2 Entity Model (Addepar Financial Graph)

```
ALLOCATION TREE HIERARCHY
═════════════════════════

Household (top-level grouping)
│   ├── Name: "Smith Family"
│   ├── Primary Contact
│   └── Aggregates all clients and their holdings
│
├── Client (beneficial owner / natural person)
│   │   ├── Name: "John Smith"
│   │   ├── SSN/Tax ID (for tax reporting)
│   │   ├── Tax Filing Status
│   │   └── Can own: Legal Entities, Accounts, Investments directly
│   │
│   ├── Legal Entity (owned by clients, can own other entities)
│   │   │   ├── Type: Trust | LLC | Partnership | S-Corp | C-Corp | Estate | Foundation
│   │   │   ├── EIN/Tax ID
│   │   │   ├── Tax Treatment: Pass-through | C-Corp | Tax-Exempt
│   │   │   ├── Formation Date
│   │   │   └── Ownership: List of (Client, percentage) pairs
│   │   │       Example: [(John Smith, 50%), (Jane Smith, 50%)]
│   │   │
│   │   └── Can own: Other Legal Entities, Accounts, Investments
│   │
│   ├── Account (held at custodian)
│   │       ├── Type: Brokerage | Retirement | Bank | Real Estate | Crypto | Manual
│   │       ├── Custodian/Institution
│   │       ├── Account Number
│   │       ├── Default Cost Basis Method
│   │       ├── Connection Status: linked | manual
│   │       ├── Owned By: Client | Legal Entity | Joint (multiple clients)
│   │       └── Ownership Percentage (for joint/shared)
│   │
│   ├── Investment / Holding (position in an account)
│   │       ├── Security (ticker, CUSIP, or manual description)
│   │       ├── Total Shares/Units
│   │       ├── Current Value
│   │       ├── Tax Status: Standard | QSBS | Section 1244 | AMT Preference
│   │       └── Aggregated from underlying Lots
│   │
│   ├── Lot (tax lot - atomic unit for cost basis)
│   │       ├── Shares/Units
│   │       ├── Acquisition Date
│   │       ├── Cost Basis (per share and total)
│   │       ├── Holding Period: ST (<1yr) | LT (≥1yr)
│   │       ├── Unrealized Gain/Loss
│   │       ├── Wash Sale Disallowed Amount
│   │       └── QSBS Acquisition Date (if applicable)
│   │
│   └── Transaction (atomic event)
│           ├── Type: Buy | Sell | Dividend | Distribution | Split | Merger | Transfer | Fee
│           ├── Date
│           ├── Security
│           ├── Quantity
│           ├── Price
│           ├── Fees/Commissions
│           ├── Lot Assignment (for sells: which lots, how many shares each)
│           └── Reconciliation Status: Pending | Matched | Manual | Discrepancy

OWNERSHIP RELATIONSHIPS (Edges in the Financial Graph)
══════════════════════════════════════════════════════

Position = Edge connecting two nodes with:
    ├── Owner (parent node)
    ├── Owned (child node)
    ├── Ownership Percentage (0-100%)
    ├── Value (computed from owned node × percentage)
    └── Inception Date

Examples:
    • John Smith ──[100%]──> Fidelity Brokerage (direct ownership)
    • John Smith ──[50%]──> Smith Family Trust (partial beneficial ownership)
    • Smith Family Trust ──[100%]──> Schwab Trust Account
    • John & Jane ──[50%/50%]──> Joint Brokerage (joint ownership)
```

### 2.3 View Hierarchy (Progressive Disclosure)

| Level | View | What's Shown | What's Hidden |
|-------|------|--------------|---------------|
| **L0** | Dashboard | Net worth, allocation pie, performance %, alerts | All detail |
| **L1** | Household List | Each household's total value, member count | Clients, entities |
| **L2** | Household Detail | Clients in household, household-level performance | Direct/indirect holdings |
| **L3** | Client Detail | Direct accounts + owned entities, client net worth | Account holdings |
| **L4** | Legal Entity Detail | Entity accounts, ownership breakdown, pass-through K-1 info | Holdings, lots |
| **L5** | Account Detail | Holdings list, account performance, balance | Lots, transactions |
| **L6** | Holding Detail | Position summary, all lots with tax info | Transaction history |
| **L7** | Lot Detail | Full lot information, associated transactions | — |
| **L8** | Transaction Detail | Complete transaction record | — |

### 2.4 Ownership Visualization (Addepar Ownership Map)

```
┌─────────────────────────────────────────────────────────────────────┐
│ OWNERSHIP MAP: Smith Family Household                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                    ┌─────────────────────┐                          │
│                    │   Smith Family      │                          │
│                    │   Household         │                          │
│                    │   $2,082,234        │                          │
│                    └─────────┬───────────┘                          │
│                              │                                       │
│            ┌─────────────────┼─────────────────┐                    │
│            │                 │                 │                    │
│            ▼                 ▼                 ▼                    │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐              │
│   │ John Smith  │   │ Jane Smith  │   │ Joint       │              │
│   │ $987,234    │   │ $645,000    │   │ $450,000    │              │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘              │
│          │                 │                 │                      │
│    ┌─────┴─────┐     ┌─────┴─────┐          │                      │
│    │           │     │           │          │                      │
│    ▼           ▼     ▼           ▼          ▼                      │
│ ┌──────┐ ┌────────┐ ┌──────┐ ┌────────┐ ┌────────┐                 │
│ │Fidel.│ │Trust   │ │Vang. │ │Trust   │ │Schwab  │                 │
│ │Broker│ │(50%)   │ │Broker│ │(50%)   │ │Joint   │                 │
│ │$487K │ │$250K   │ │$395K │ │$250K   │ │$450K   │                 │
│ └──────┘ └────┬───┘ └──────┘ └────┬───┘ └────────┘                 │
│               │                   │                                 │
│               └─────────┬─────────┘                                 │
│                         ▼                                           │
│                  ┌─────────────┐                                    │
│                  │Smith Family │                                    │
│                  │Trust        │                                    │
│                  │$500,000     │                                    │
│                  └─────────────┘                                    │
│                                                                      │
│  Legend: [Client] [Legal Entity] [Account]                          │
│  Click any node to drill down • Hover for ownership %               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 3: Decision Framework

### 3.1 Navigation Axis

| Decision | Option A: By Allocation Tree (Addepar) | Option B: By Asset Class | Recommendation |
|----------|---------------------------------------|-------------------------|----------------|
| **Structure** | Household → Client → Entity → Account → Holding | Equities → AAPL → [lots by account] | **Option A** |
| **Pro** | Matches ownership reality; tax lots are per-account; supports look-through reporting | Cross-account view of same security | |
| **Con** | More levels to navigate; learning curve for simple users | Tax lot selection becomes confusing (which account's lots?) | |
| **Rationale** | Addepar's allocation tree is the right model. Household groups a family's wealth; Clients are the beneficial owners; Entities provide legal/tax structure; Accounts hold the assets. This enables: (1) proper tax attribution, (2) joint ownership, (3) look-through reporting, (4) K-1 tracking for pass-through entities. Provide cross-household aggregation via Dashboard. |

### 3.2 Transaction Entry Model

| Decision | Option A: Form-Based | Option B: Spreadsheet-Style | Recommendation |
|----------|---------------------|---------------------------|----------------|
| **Interface** | Modal/panel with labeled fields | Inline row editing like Excel | **Hybrid** |
| **Pro** | Clear validation, guided entry | Fast bulk entry, power-user friendly | |
| **Con** | Slow for bulk entry | Error-prone, less guidance | |
| **Rationale** | Default to form-based for single transactions (better validation, lot selection UI). Offer "bulk entry mode" or CSV import for power users. |

### 3.3 Lot Selection Default

| Decision | Option A: Automatic (FIFO) | Option B: Always Ask | Recommendation |
|----------|---------------------------|---------------------|----------------|
| **Behavior** | System uses account default method unless overridden | Prompt user to select lots on every sale | **Option A with preview** |
| **Pro** | Frictionless for most transactions | Maximum tax optimization control | |
| **Con** | User might not realize tax implications | Annoying for routine transactions | |
| **Rationale** | Use account's default cost basis method (user-configurable: FIFO, LIFO, HIFO, SpecID). Show tax impact preview before confirming sale. Allow override to SpecID at any time. |

### 3.4 Reconciliation Model

| Decision | Option A: Statement-Driven | Option B: Transaction-Driven | Recommendation |
|----------|---------------------------|----------------------------|----------------|
| **Flow** | Import statement, match to existing transactions | Enter transactions, compare to statement at end | **Option A** |
| **Pro** | Ensures completeness; catches missing transactions | Users control data entry | |
| **Con** | Requires good import/parsing | Reconciliation becomes tedious verification | |
| **Rationale** | Sophisticated users have brokerage statements as source of truth. Import statement → auto-match → flag discrepancies → resolve queue. |

### 3.5 Tax Data Visibility

| Decision | Option A: On-Demand (Reports) | Option B: Always Visible | Recommendation |
|----------|------------------------------|-------------------------|----------------|
| **Placement** | Tax info only in Tax Center and Reports | Tax badges/indicators throughout UI | **Option B** |
| **Pro** | Cleaner primary views | Tax-aware decision-making everywhere | |
| **Con** | Users forget about tax implications | Visual clutter | |
| **Rationale** | Key differentiator. Show holding period (ST/LT badge), unrealized gain/loss, wash sale warnings inline. Keep detail in Tax Center but surface key indicators everywhere. |

### 3.6 Multi-Currency Handling

| Decision | Option A: Single Base Currency | Option B: Native + Base | Recommendation |
|----------|-------------------------------|------------------------|----------------|
| **Display** | Everything converted to USD (or user's base) | Show native currency, with base currency equivalent | **Option B** |
| **Pro** | Simple totals | Accurate for tax reporting (need original currency) | |
| **Con** | Hides FX impact | More visual complexity | |
| **Rationale** | Tax cost basis is in acquisition currency. Show "£10,000 / $12,500" format. Let users toggle to base-only for simplified view. |

### 3.7 Mobile Scope

| Decision | Option A: Full Feature Parity | Option B: View-Only Companion | Recommendation |
|----------|-----------------------------|-----------------------------|----------------|
| **Capability** | All features work on mobile | View dashboards, holdings; no editing | **Option B+** |
| **Pro** | One app for everything | Faster mobile development; editing on small screen is error-prone | |
| **Con** | Complex UI on small screen | Users can't act on mobile | |
| **Rationale** | View + light actions (mark transaction reconciled, acknowledge alert). No lot selection or complex entry on mobile. |

---

## Part 4: Wireframe Descriptions

### 4.1 Flow: Adding a Buy Transaction with Lot Creation

**Context:** User wants to manually record purchasing 100 shares of AAPL.

```
┌─────────────────────────────────────────────────────────────────────┐
│ ADD TRANSACTION                                              [X Close]
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Transaction Type:  ○ Buy  ○ Sell  ○ Dividend  ○ Transfer  ○ Other  │
│                     ●                                               │
│                                                                      │
│  Household:        [Smith Family                    ▼]              │
│  Client/Entity:    [John Smith (Direct)             ▼]              │
│  Account:          [Fidelity Brokerage              ▼]              │
│                                                                      │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                      │
│  Security:         [AAPL - Apple Inc.               ▼] 🔍           │
│  Trade Date:       [2026-01-15                      📅]              │
│  Settlement Date:  [2026-01-17                      📅] (auto-filled)│
│                                                                      │
│  Quantity:         [100        ] shares                             │
│  Price per Share:  [$225.50    ]                                    │
│  Commission/Fees:  [$0.00      ]                                    │
│                                                                      │
│  ─────────────────────────────────────────────────────────────────  │
│  COST BASIS SUMMARY                                                 │
│                                                                      │
│  Total Cost:           $22,550.00                                   │
│  Cost per Share:       $225.50                                      │
│  Long-Term Date:       2027-01-16 (in 366 days)                    │
│                                                                      │
│  ─────────────────────────────────────────────────────────────────  │
│  TAX STATUS (optional)                                              │
│                                                                      │
│  ☐ QSBS Eligible (Section 1202)                                     │
│  ☐ Section 1244 Stock                                               │
│                                                                      │
│  Notes: [                                                    ]      │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                           [Cancel]  [Save Transaction]              │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Elements:**
- Transaction type as radio buttons (most common action: buy)
- **Household → Client/Entity → Account cascade**: Dropdowns filter based on selection; pre-fill if user entered from account context
- Security search with typeahead (ticker or company name)
- Settlement date auto-calculated (T+1 for equities)
- Cost basis summary computed in real-time
- Long-term threshold date shown (tax-aware!)
- QSBS/Section 1244 flags for special tax treatment

### 4.2 Flow: Selling Partial Position with Specific Lot Selection

**Context:** User owns 500 shares of AAPL across 3 lots, wants to sell 150 shares.

```
┌─────────────────────────────────────────────────────────────────────┐
│ SELL SHARES: AAPL                                           [X Close]
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Account:     Fidelity Brokerage (Personal)                         │
│  Current Position: 500 shares @ $225.00 = $112,500                  │
│                                                                      │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                      │
│  Shares to Sell:   [150        ]                                    │
│  Price per Share:  [$227.50    ]  (pre-filled with current price)   │
│  Commission/Fees:  [$0.00      ]                                    │
│                                                                      │
│  ─────────────────────────────────────────────────────────────────  │
│  LOT SELECTION                                                      │
│                                                                      │
│  Method: ○ Use Account Default (FIFO)  ● Specific Identification    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Select Lots                                   Selling: 150 / 150││
│  ├────────┬──────────┬─────────┬────────┬───────────┬─────────────┤│
│  │ Select │ Acquired │ Shares  │ Basis  │ Period    │ Est. Gain   ││
│  ├────────┼──────────┼─────────┼────────┼───────────┼─────────────┤│
│  │ [100 ] │ 03/15/21 │ 100 avl │ $120   │ LT ✓      │ +$10,750    ││
│  │ [50  ] │ 06/20/22 │ 200 avl │ $150   │ LT ✓      │ +$3,875     ││
│  │ [0   ] │ 01/10/24 │ 200 avl │ $180   │ LT ✓      │ +$9,500     ││
│  └────────┴──────────┴─────────┴────────┴───────────┴─────────────┘│
│                                                                      │
│  ─────────────────────────────────────────────────────────────────  │
│  TAX IMPACT PREVIEW                                                 │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Proceeds:                          $34,125.00                 │  │
│  │ Cost Basis:                       -$19,500.00                 │  │
│  │ ─────────────────────────────────────────────────────────────│  │
│  │ Estimated Gain:                    $14,625.00                 │  │
│  │ ─────────────────────────────────────────────────────────────│  │
│  │ Tax Treatment:     Long-Term Capital Gain (100%)             │  │
│  │ Est. Federal Tax:  $2,193.75 (@ 15% LTCG rate)               │  │
│  │                                                               │  │
│  │ ⚠️ No wash sale issues detected                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                           [Cancel]  [Confirm Sale]                  │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Elements:**
- Lot table with inline quantity selectors (not checkboxes—allows partial lot sales)
- Real-time validation: "Selling: 150 / 150" shows progress toward target
- Holding period badges (LT ✓ or ST) for quick scanning
- Per-lot estimated gain shown
- Tax impact preview computed dynamically as lots are selected
- Wash sale warning system (would show ⚠️ if selling at loss within 30 days of purchase)
- Tax treatment breakdown (LT vs ST percentages if mixed)

### 4.3 Flow: Reconciling Imported Brokerage Data

**Context:** User imports monthly statement; system needs to match against existing records.

```
┌─────────────────────────────────────────────────────────────────────┐
│ RECONCILIATION: Fidelity Brokerage - January 2026                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Import Source: Fidelity_Jan2026.csv       Status: 47 items imported│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Matched (42)    │ Needs Review (3)    │ New (2)                 ││
│  │ ████████████████  ███                   ██                      ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ═══════════════════════════════════════════════════════════════════│
│  NEEDS REVIEW                                                   3   │
│  ═══════════════════════════════════════════════════════════════════│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ ⚠️ PRICE MISMATCH                                               ││
│  │ Statement: Buy 50 MSFT @ $415.00 on 01/12/2026                  ││
│  │ Your Record: Buy 50 MSFT @ $414.50 on 01/12/2026                ││
│  │ Difference: $0.50/share ($25.00 total)                          ││
│  │                                                                  ││
│  │ [Use Statement Price] [Keep My Record] [Edit Manually]          ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ ⚠️ POSSIBLE DUPLICATE                                           ││
│  │ Statement: Dividend AAPL $124.00 on 01/15/2026                  ││
│  │ Existing Record: Dividend AAPL $124.00 on 01/15/2026 (matched)  ││
│  │                                                                  ││
│  │ [Mark as Duplicate] [Create New Record] [View Existing]         ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ ❓ NO MATCH FOUND                                                ││
│  │ Statement: Fee $4.95 on 01/20/2026 - "ADR Fee"                  ││
│  │                                                                  ││
│  │ [Create as New Transaction] [Ignore] [Assign to Holding: ▼]    ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ═══════════════════════════════════════════════════════════════════│
│  NEW TRANSACTIONS (not in your records)                         2   │
│  ═══════════════════════════════════════════════════════════════════│
│                                                                      │
│  ☑️ Buy 25 VTI @ $280.00 on 01/22/2026 - DRIP                       │
│  ☑️ Dividend VTI $45.20 on 01/22/2026                                │
│                                                                      │
│  [Import Selected New Transactions]                                 │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Ending Balance Check:                                              │
│  Statement: $487,234.56    Your Records: $487,234.56    ✅ Match    │
├─────────────────────────────────────────────────────────────────────┤
│           [Save Progress]  [Complete Reconciliation]                │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Elements:**
- Progress bar showing match status at a glance
- Three categories: Matched (green), Needs Review (yellow), New (blue)
- Card-based display for each discrepancy with clear action buttons
- Tolerance-aware matching (small price differences flagged, not auto-rejected)
- Ending balance verification as final check
- Ability to save progress and return later

### 4.4 Flow: Viewing Tax Lots with Unrealized Gain/Loss

**Context:** User drills into a holding to see all lots and their tax status.

```
┌─────────────────────────────────────────────────────────────────────┐
│ AAPL - Apple Inc.                                                   │
│ Smith Family > John Smith > Fidelity Brokerage                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Position Summary                                                │ │
│  ├───────────────┬───────────────┬────────────────┬───────────────┤ │
│  │ Shares        │ Current Value │ Total Basis    │ Unrealized G/L│ │
│  │ 500           │ $112,500.00   │ $75,000.00     │ +$37,500.00   │ │
│  │               │ @ $225.00     │ avg $150.00    │ +50.00%       │ │
│  └───────────────┴───────────────┴────────────────┴───────────────┘ │
│                                                                      │
│  ─────────────────────────────────────────────────────────────────  │
│  TAX LOTS                                           Sort: [Date ▼]  │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Lot #1                                               [LT] ✓ │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │ Acquired:    March 15, 2021 (4y 10m ago)                     │   │
│  │ Shares:      100                                             │   │
│  │ Cost Basis:  $12,000.00 ($120.00/share)                      │   │
│  │ Current:     $22,500.00 ($225.00/share)                      │   │
│  │ Gain/Loss:   +$10,500.00 (+87.5%)                            │   │
│  │ Tax Impact:  ~$1,575 LTCG tax if sold (@ 15%)                │   │
│  │                                                              │   │
│  │              [View Transactions]  [Sell from This Lot]       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Lot #2                                               [LT] ✓ │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │ Acquired:    June 20, 2022 (3y 7m ago)                       │   │
│  │ Shares:      200                                             │   │
│  │ Cost Basis:  $30,000.00 ($150.00/share)                      │   │
│  │ Current:     $45,000.00 ($225.00/share)                      │   │
│  │ Gain/Loss:   +$15,000.00 (+50.0%)                            │   │
│  │ Tax Impact:  ~$2,250 LTCG tax if sold (@ 15%)                │   │
│  │                                                              │   │
│  │              [View Transactions]  [Sell from This Lot]       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Lot #3                                               [LT] ✓ │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │ Acquired:    January 10, 2024 (2y 0m ago)                    │   │
│  │ Shares:      200                                             │   │
│  │ Cost Basis:  $36,000.00 ($180.00/share)                      │   │
│  │ Current:     $45,000.00 ($225.00/share)                      │   │
│  │ Gain/Loss:   +$9,000.00 (+25.0%)                             │   │
│  │ Tax Impact:  ~$1,350 LTCG tax if sold (@ 15%)                │   │
│  │                                                              │   │
│  │ 🔔 QSBS Eligible - 5-year date: January 10, 2029             │   │
│  │                                                              │   │
│  │              [View Transactions]  [Sell from This Lot]       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ─────────────────────────────────────────────────────────────────  │
│  TAX OPTIMIZATION INSIGHTS                                          │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                      │
│  💡 All lots are long-term; no holding period optimization needed   │
│  💡 Lot #3 is QSBS eligible; consider holding until 2029 for        │
│     potential $10M+ gain exclusion                                   │
│  ⚠️ No tax-loss harvesting opportunities in this position           │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  [← Back to Holdings]  [View All Transactions]  [Sell Shares]       │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Elements:**
- Position summary with aggregate metrics
- Individual lot cards with full tax detail
- Holding period badges: [LT] for long-term, [ST] for short-term
- Time since acquisition in human-readable format
- Per-lot tax impact estimates
- QSBS call-out with 5-year eligibility date
- Tax optimization insights section
- Direct action buttons per lot

### 4.5 Flow: Navigating the Allocation Tree (Household → Client → Entity)

**Context:** User wants to explore their household structure and drill into the Family Trust.

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Logo]   Dashboard │ Allocation │ Transactions │ Tax Center │ ...  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ALLOCATION TREE                          [Tree View] [Map View]    │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ 🏠 SMITH FAMILY HOUSEHOLD                      $2,082,234      │ │
│  │    2 clients · 3 legal entities · 6 accounts                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ├─ CLIENTS ─────────────────────────────────────────────────────  │
│                                                                      │
│  │  ┌──────────────────────────────────────────────────────────┐   │
│  │  │ 👤 John Smith                                 $987,234   │   │
│  │  │    Direct: $487,234 · Through Entities: $500,000         │   │
│  │  │    [View Client →]                                       │   │
│  │  └──────────────────────────────────────────────────────────┘   │
│  │                                                                  │
│  │  ┌──────────────────────────────────────────────────────────┐   │
│  │  │ 👤 Jane Smith                                 $645,000   │   │
│  │  │    Direct: $395,000 · Through Entities: $250,000         │   │
│  │  │    [View Client →]                                       │   │
│  │  └──────────────────────────────────────────────────────────┘   │
│  │                                                                  │
│  │  ┌──────────────────────────────────────────────────────────┐   │
│  │  │ 👥 Joint (John & Jane)                        $450,000   │   │
│  │  │    1 joint account                                       │   │
│  │  │    [View Joint Holdings →]                               │   │
│  │  └──────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ├─ LEGAL ENTITIES ──────────────────────────────────────────────  │
│                                                                      │
│  │  ┌──────────────────────────────────────────────────────────┐   │
│  │  │ 🏛️ Smith Family Trust                ← EXPANDED          │   │
│  │  │    Irrevocable Trust · $500,000                          │   │
│  │  │    Owners: John (50%), Jane (50%)                        │   │
│  │  ├──────────────────────────────────────────────────────────┤   │
│  │  │                                                           │   │
│  │  │  Accounts:                                                │   │
│  │  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  │ Schwab Trust Account                    $375,000   │  │   │
│  │  │  │ 8 holdings · Last synced: 1 hour ago               │  │   │
│  │  │  └────────────────────────────────────────────────────┘  │   │
│  │  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  │ Trust Real Estate                       $125,000   │  │   │
│  │  │  │ 1 property · Manual valuation                      │  │   │
│  │  │  └────────────────────────────────────────────────────┘  │   │
│  │  │                                                           │   │
│  │  │  Trust Summary:                                           │   │
│  │  │  YTD: +8.2%  Unrealized G/L: +$56,000                    │   │
│  │  │  Tax: Pass-through (K-1 to John 50%, Jane 50%)           │   │
│  │  │                                                           │   │
│  │  └──────────────────────────────────────────────────────────┘   │
│  │                                                                  │
│  │  ┌──────────────────────────────────────────────────────────┐   │
│  │  │ 🏢 Smith Investment LLC                       $350,000   │   │
│  │  │    LLC · Owner: John (100%)                              │   │
│  │  │    [View Entity →]                                       │   │
│  │  └──────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ─────────────────────────────────────────────────────────────────  │
│  [+ Add Client]  [+ Add Legal Entity]  [+ Add Account]              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Elements:**
- **Household as top container**: Groups all family wealth
- **Clients section**: Shows each beneficial owner with direct + indirect holdings
- **Joint ownership**: First-class representation for jointly-held accounts
- **Legal Entities section**: Trusts, LLCs with ownership percentages displayed
- **Expandable cards**: Click to reveal accounts within entity
- **Pass-through tax info**: Shows K-1 allocation percentages
- **Tree View / Map View toggle**: Switch between list and visual ownership map
- **Breadcrumb**: Dashboard > Smith Family > Smith Family Trust > Schwab Trust Account

---

## Part 5: Gap Analysis & Opportunity Space

### 5.1 What No Reference Product Does Well

| Gap | Current State | Opportunity |
|-----|---------------|-------------|
| **Tax-integrated daily view** | Tax info buried in reports; not visible during normal portfolio review | Surface holding period badges, unrealized gain/loss, wash sale warnings in holding lists |
| **QSBS tracking** | No mainstream tool tracks QSBS eligibility dates or acquisition requirements | First-class QSBS support: flag eligible holdings, track 5-year date, warn before disqualifying events |
| **Wash sale prevention** | Reported after the fact by brokers; no proactive warnings | Pre-trade wash sale check: "This sale would trigger a wash sale with lot purchased 01/05" |
| **Cross-entity wash sale tracking** | IRS requires tracking across all accounts; no tool does this | Unified wash sale monitoring across entities (Personal + Trust + IRA = one wash sale universe) |
| **Tax lot selection UX** | Schwab/Fidelity: clunky 4-lot limit; Quicken: accounting-style tables | Modern lot picker with inline quantity selectors, real-time tax impact preview |
| **Reconciliation workflow** | Quicken: dated; Kubera: none; Family office tools: overkill | Statement import → fuzzy matching → exception queue → balance verification |
| **Multi-entity for individuals** | Either consumer-simple or enterprise-complex | Right-sized multi-entity: 2-10 entities, not 100+; simple setup, no consultant required |
| **Corporate action tracking** | Often missed or manually adjusted after the fact | Corporate action calendar, auto-application of splits/mergers, audit trail |

### 5.2 Differentiation Opportunities

#### Tier 1: Core Differentiators (Must-Have)

1. **Tax-First Philosophy**
   - Every holding shows: current value, cost basis, unrealized G/L, holding period
   - Tax impact preview on every sell transaction
   - Wash sale warnings proactive, not reactive

2. **Lot-Level Accounting as Default**
   - Not "average cost" by default; actual lot tracking
   - SpecID available on every sale, not hidden in settings
   - Lot history preserved with full audit trail

3. **Reconciliation Excellence**
   - Import brokerage statements (CSV, PDF, broker API)
   - Intelligent matching with tolerance settings
   - Discrepancy queue with clear resolution actions

#### Tier 2: Significant Differentiators (Should-Have)

4. **QSBS & Special Tax Treatment**
   - Flag holdings as QSBS eligible
   - Track 5-year holding period countdown
   - Warn before events that would disqualify QSBS (e.g., stock redemption)

5. **Multi-Entity Right-Sizing**
   - Support for Individual, Trust, LLC, Partnership out of the box
   - Inter-entity transfer tracking
   - Consolidated reporting with entity-level drill-down

6. **Cross-Account Wash Sale Monitoring**
   - Unified 30-day look-back across all accounts and entities
   - Pre-trade warning: "This purchase would wash a loss from [other account]"

#### Tier 3: Nice-to-Have Differentiators

7. **Estate Planning Features**
   - Beneficiary designation tracking
   - Step-up basis projection ("If inherited today, basis would be $X")
   - Document vault integration (wills, trust documents)

8. **Advisor/Accountant Portal**
   - Read-only access for tax preparer
   - Pre-formatted exports for Schedule D, Form 8949
   - Client reporting dashboards

### 5.3 Anti-Patterns to Avoid

| Anti-Pattern | Seen In | Why to Avoid |
|--------------|---------|--------------|
| **Average cost default** | Many consumer tools | Loses tax optimization opportunity |
| **Reconciliation as afterthought** | Kubera, Personal Capital | Users can't trust data without verification |
| **Tax reports only** | Most tools | Tax awareness should be continuous, not end-of-year |
| **Overwhelming entity structure** | Addepar | Individual users don't need fund-of-funds complexity |
| **No mobile at all** | Quicken Desktop | Users expect at least view access on phone |
| **Lots hidden in "advanced" settings** | Several brokerages | Lots are core to investment accounting, not advanced |

---

## Appendix

### A.1 Competitive Feature Matrix

| Feature | Kubera | Quicken | Addepar | Sharesight | Portfolio Performance |
|---------|--------|---------|---------|------------|----------------------|
| Net Worth Aggregation | ★★★★★ | ★★★☆☆ | ★★★★★ | ★★☆☆☆ | ★★☆☆☆ |
| Transaction Entry | ☆☆☆☆☆ | ★★★★★ | ★★★★☆ | ★★★☆☆ | ★★★★☆ |
| Tax Lot Tracking | ☆☆☆☆☆ | ★★★★☆ | ★★★★★ | ★★★☆☆ | ★★★☆☆ |
| Cost Basis Methods | N/A | ★★★★☆ | ★★★★★ | ★★☆☆☆ | ★★★☆☆ |
| Reconciliation | ☆☆☆☆☆ | ★★★★☆ | ★★★★★ | ★★☆☆☆ | ★★★☆☆ |
| Multi-Entity | ☆☆☆☆☆ | ★★☆☆☆ | ★★★★★ | ★☆☆☆☆ | ★★☆☆☆ |
| Modern UX | ★★★★★ | ★★☆☆☆ | ★★★★☆ | ★★★★☆ | ★★★☆☆ |
| Crypto Support | ★★★★★ | ★★☆☆☆ | ★★★☆☆ | ★★★☆☆ | ★★★★☆ |
| International | ★★★★★ | ★☆☆☆☆ | ★★★★★ | ★★★★★ | ★★★★★ |
| Price | $150/yr | $35-100/yr | $$$$$ | $0-300/yr | Free |

### A.2 Reference Links

**Primary References:**
- [Kubera](https://www.kubera.com/) - Net worth tracking for HNW
- [Quicken](https://www.quicken.com/) - Personal finance and investment tracking
- [Quicken Classic Premier](https://www.quicken.com/products/classic-premier/) - Investment-focused tier

**Secondary References:**
- [Addepar](https://addepar.com/) - Institutional wealth management
- [Sharesight](https://www.sharesight.com/) - Tax-aware portfolio tracking
- [Portfolio Performance](https://www.portfolio-performance.info/en/) - Open source investment tracking

**Family Office Platforms:**
- [Asset Vantage](https://www.assetvantage.com/) - Multi-entity family office
- [Archway](https://www.archwaytechnology.net/) - Family office accounting
- [Sage Intacct](https://www.sage.com/en-us/sage-business-cloud/intacct/) - Multi-entity accounting

**Tax Lot & Wash Sale Tools:**
- [TradeLog](https://tradelog.com/) - Wash sale tracking for traders
- [Mezzi](https://www.mezzi.com/) - AI-powered wash sale tracking

**Cost Basis Method References:**
- [Vanguard Cost Basis Methods](https://investor.vanguard.com/investor-resources-education/taxes/cost-basis-methods-available-at-vanguard)
- [Schwab Cost Basis Guide](https://www.schwab.com/learn/story/save-on-taxes-know-your-cost-basis)
- [Bogleheads: Specific Identification](https://www.bogleheads.org/wiki/Specific_identification_of_shares)

**QSBS Resources:**
- [Carta QSBS Guide](https://carta.com/learn/startups/tax-planning/qsbs/)
- [Pulley QSBS Tracking](https://pulley.com/guides/qualified-small-business-stock-qsbs)

### A.3 Glossary

| Term | Definition |
|------|------------|
| **FIFO** | First-In, First-Out cost basis method |
| **LIFO** | Last-In, First-Out cost basis method |
| **HIFO** | Highest-In, First-Out (tax loss harvesting) |
| **SpecID** | Specific Identification - user selects exact lots to sell |
| **LTCG/STCG** | Long-Term / Short-Term Capital Gain |
| **QSBS** | Qualified Small Business Stock (Section 1202) |
| **Wash Sale** | IRS rule disallowing loss if substantially identical security bought within 30 days |
| **TWR** | Time-Weighted Return - performance excluding cash flow timing |
| **IRR** | Internal Rate of Return - performance including cash flow timing |
| **Lot** | A distinct purchase of securities with unique acquisition date and cost |

---

*Document prepared for UI/UX design handoff. Questions: [your contact]*
