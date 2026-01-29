# Family Office Ledger - Architecture Diagrams

## 1. Core Data Schema (Entity Relationship)

```mermaid
erDiagram
    Household ||--o{ HouseholdMember : contains
    HouseholdMember }o--|| Entity : references
    
    Entity ||--o{ Account : owns
    Entity ||--o{ EntityOwnership : "owns (as owner)"
    Entity ||--o{ EntityOwnership : "is owned (as target)"
    
    Account ||--o{ Position : holds
    Account ||--o{ Entry : "debits/credits"
    
    Position ||--o{ TaxLot : "has lots"
    Position }o--|| Security : tracks
    
    Transaction ||--o{ Entry : contains
    Transaction }o--o| Vendor : "paid to"
    
    Entry }o--o| TaxLot : "affects"
    
    Household {
        uuid id PK
        string name
        uuid primary_contact_entity_id FK
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    HouseholdMember {
        uuid id PK
        uuid household_id FK
        uuid entity_id FK
        string role
        string display_name
        date effective_start_date
        date effective_end_date
    }
    
    Entity {
        uuid id PK
        string name UK
        enum entity_type
        date fiscal_year_end
        boolean is_active
        enum tax_treatment
        string tax_id
    }
    
    EntityOwnership {
        uuid id PK
        uuid owner_entity_id FK
        uuid owned_entity_id FK
        decimal ownership_fraction
        date effective_start_date
        date effective_end_date
        string ownership_type
    }
    
    Account {
        uuid id PK
        string name
        uuid entity_id FK
        enum account_type
        enum sub_type
        string currency
        boolean is_investment_account
    }
    
    Transaction {
        uuid id PK
        date transaction_date
        date posted_date
        string memo
        string reference
        boolean is_reversed
    }
    
    Entry {
        uuid id PK
        uuid transaction_id FK
        uuid account_id FK
        money debit_amount
        money credit_amount
        string memo
    }
    
    Security {
        uuid id PK
        string symbol UK
        string name
        string cusip
        enum asset_class
        boolean is_qsbs_eligible
    }
    
    Position {
        uuid id PK
        uuid account_id FK
        uuid security_id FK
        quantity quantity
        money cost_basis
        money market_value
    }
    
    TaxLot {
        uuid id PK
        uuid position_id FK
        date acquisition_date
        money cost_per_share
        quantity original_quantity
        quantity remaining_quantity
        enum acquisition_type
    }
```

## 2. Ownership Graph Model (Addepar-style)

```mermaid
graph TD
    subgraph "Household: Smith Family"
        H[("Household<br/>Smith Family")]
    end
    
    subgraph "Clients (Individuals)"
        A["Alice Smith<br/>(INDIVIDUAL)<br/>role=client"]
        B["Bob Smith<br/>(INDIVIDUAL)<br/>role=client"]
    end
    
    subgraph "Owned Entities"
        T["Smith Family Trust<br/>(TRUST)"]
        LLC["Smith Holdings LLC<br/>(LLC)"]
        J["A&B Joint Account<br/>(JOINT)"]
    end
    
    subgraph "Accounts & Holdings"
        A_CHK[("Alice Checking<br/>$10,000")]
        B_CHK[("Bob Checking<br/>$20,000")]
        T_BROK[("Trust Brokerage<br/>$100,000")]
        LLC_ACC[("LLC Account<br/>$50,000")]
    end
    
    H -.->|"member<br/>role=client"| A
    H -.->|"member<br/>role=client"| B
    H -.->|"member<br/>role=entity"| T
    
    A -->|"owns 50%"| T
    B -->|"owns 50%"| T
    A -->|"owns 50%"| J
    B -->|"owns 50%"| J
    T -->|"owns 100%"| LLC
    
    A --- A_CHK
    B --- B_CHK
    T --- T_BROK
    LLC --- LLC_ACC

    style H fill:#e1f5fe
    style A fill:#c8e6c9
    style B fill:#c8e6c9
    style T fill:#fff3e0
    style LLC fill:#fff3e0
    style J fill:#fff3e0
```

### Look-Through Net Worth Calculation

```mermaid
flowchart LR
    subgraph "Direct Holdings"
        A1["Alice: $10,000<br/>(100% × $10k)"]
        B1["Bob: $20,000<br/>(100% × $20k)"]
    end
    
    subgraph "Through Trust (50% each)"
        A2["Alice: $50,000<br/>(50% × $100k)"]
        B2["Bob: $50,000<br/>(50% × $100k)"]
    end
    
    subgraph "Through LLC (via Trust)"
        A3["Alice: $25,000<br/>(50% × 100% × $50k)"]
        B3["Bob: $25,000<br/>(50% × 100% × $50k)"]
    end
    
    A1 --> AT["Alice Total:<br/>$85,000"]
    A2 --> AT
    A3 --> AT
    
    B1 --> BT["Bob Total:<br/>$95,000"]
    B2 --> BT
    B3 --> BT
    
    AT --> HT["Household Total:<br/>$180,000"]
    BT --> HT
    
    style AT fill:#c8e6c9
    style BT fill:#c8e6c9
    style HT fill:#e1f5fe
```

## 3. Double-Entry Transaction Flow

```mermaid
flowchart TB
    subgraph "Transaction: Capital Contribution $10,000"
        TXN["Transaction<br/>date: 2024-01-15<br/>memo: Capital contribution"]
        
        E1["Entry 1<br/>DEBIT: Cash $10,000"]
        E2["Entry 2<br/>CREDIT: Member's Capital $10,000"]
        
        TXN --> E1
        TXN --> E2
    end
    
    subgraph "Account Balances"
        CASH[("Cash Account<br/>(ASSET)<br/>+$10,000")]
        CAP[("Member's Capital<br/>(EQUITY)<br/>+$10,000")]
    end
    
    E1 -->|"increases"| CASH
    E2 -->|"increases"| CAP
    
    subgraph "Accounting Equation"
        EQ["Assets = Liabilities + Equity<br/>$10,000 = $0 + $10,000 ✓"]
    end
    
    CASH --> EQ
    CAP --> EQ
```

### Investment Purchase Flow

```mermaid
flowchart TB
    subgraph "Buy 100 shares AAPL @ $150"
        TXN2["Transaction<br/>date: 2024-01-20"]
        
        E3["Entry: DEBIT<br/>Brokerage (AAPL)<br/>$15,000"]
        E4["Entry: CREDIT<br/>Cash<br/>$15,000"]
        
        TXN2 --> E3
        TXN2 --> E4
    end
    
    subgraph "Position & Tax Lot Created"
        POS["Position<br/>Account: Brokerage<br/>Security: AAPL<br/>Qty: 100"]
        
        LOT["TaxLot<br/>Acquired: 2024-01-20<br/>Cost/share: $150<br/>Qty: 100<br/>Type: PURCHASE"]
        
        POS --> LOT
    end
    
    E3 -->|"creates"| POS
    
    subgraph "Future: Sell 50 shares @ $180"
        SELL["Sell Transaction"]
        LOT2["TaxLot Updated<br/>Remaining: 50<br/>Gain: $1,500"]
    end
    
    LOT -.->|"FIFO/LIFO/etc"| LOT2
```

## 4. Reconciliation Workflow

```mermaid
stateDiagram-v2
    [*] --> CreateSession: Upload bank file
    
    CreateSession --> MatchPending: Parse transactions
    
    state MatchPending {
        [*] --> AutoMatch
        AutoMatch --> Review: Confidence scores calculated
        Review --> Confirm: High confidence match
        Review --> Reject: Wrong match
        Review --> Skip: Decide later
        Review --> Create: No match exists
    }
    
    MatchPending --> SessionComplete: All matches resolved
    MatchPending --> SessionAbandoned: User abandons
    
    SessionComplete --> [*]
    SessionAbandoned --> [*]
```

### Match Scoring Algorithm

```mermaid
flowchart LR
    subgraph "Imported Transaction"
        IMP["Bank Import<br/>Date: 2024-01-15<br/>Amount: $500.00<br/>Desc: ACME CORP"]
    end
    
    subgraph "Scoring Factors"
        AMT["Amount Match<br/>Exact: 50 pts<br/>±$1: 40 pts<br/>±$5: 20 pts"]
        
        DATE["Date Proximity<br/>Same day: 30 pts<br/>±1 day: 25 pts<br/>±3 days: 15 pts"]
        
        MEMO["Memo Similarity<br/>Fuzzy match: 0-20 pts"]
    end
    
    subgraph "Candidate Ledger Txn"
        LED["Ledger Txn<br/>Date: 2024-01-15<br/>Amount: $500.00<br/>Memo: Payment to Acme"]
    end
    
    IMP --> AMT
    IMP --> DATE
    IMP --> MEMO
    LED --> AMT
    LED --> DATE
    LED --> MEMO
    
    AMT --> SCORE["Total Score: 95<br/>(High Confidence)"]
    DATE --> SCORE
    MEMO --> SCORE
    
    SCORE --> STATUS{">= 80?"}
    STATUS -->|Yes| AUTO["Auto-suggest<br/>for confirmation"]
    STATUS -->|No| MANUAL["Manual review<br/>required"]
```

## 5. User Journey: Complete Workflow

```mermaid
journey
    title Family Office User Journey
    section Setup
      Create household: 5: User
      Add family members: 5: User
      Create entities (trusts, LLCs): 4: User
      Set up ownership structure: 4: User
      Create accounts: 5: User
    section Daily Operations
      Import bank statements: 4: User
      Reconcile transactions: 3: User
      Categorize expenses: 4: User
      Review matches: 3: User
    section Investment Tracking
      Record purchases: 4: User
      Track tax lots: 3: System
      Monitor positions: 5: User
      Calculate gains/losses: 5: System
    section Reporting
      View household net worth: 5: User
      Look-through analysis: 5: User
      Generate tax reports: 4: System
      Budget vs actual: 4: User
```

## 6. System Architecture (Layered)

```mermaid
flowchart TB
    subgraph "Presentation Layer"
        CLI["CLI<br/>(fol command)"]
        API["FastAPI<br/>(REST API)"]
        STREAM["Streamlit<br/>(Web UI)"]
        NICE["NiceGUI<br/>(Alt Web UI)"]
    end
    
    subgraph "Service Layer"
        LED_SVC["LedgerService<br/>Double-entry posting"]
        REP_SVC["ReportingService<br/>Net worth, P&L"]
        REC_SVC["ReconciliationService<br/>Bank matching"]
        OWN_SVC["OwnershipGraphService<br/>Look-through calc"]
        ING_SVC["IngestionService<br/>Transaction parsing"]
        LOT_SVC["LotMatchingService<br/>FIFO/LIFO/etc"]
    end
    
    subgraph "Repository Layer"
        REPO["Repository Interfaces"]
        SQLITE["SQLite Implementation"]
        POSTGRES["Postgres Implementation"]
    end
    
    subgraph "Domain Layer"
        ENT["Entity, Account"]
        TXN["Transaction, Entry"]
        HH["Household, Member"]
        OWN["EntityOwnership"]
        LOT["Position, TaxLot"]
    end
    
    CLI --> LED_SVC
    CLI --> REC_SVC
    CLI --> ING_SVC
    API --> LED_SVC
    API --> REP_SVC
    API --> OWN_SVC
    STREAM --> API
    NICE --> API
    
    LED_SVC --> REPO
    REP_SVC --> REPO
    REC_SVC --> REPO
    OWN_SVC --> REPO
    ING_SVC --> REPO
    LOT_SVC --> REPO
    
    REPO --> SQLITE
    REPO --> POSTGRES
    
    SQLITE --> ENT
    SQLITE --> TXN
    SQLITE --> HH
    SQLITE --> OWN
    SQLITE --> LOT
```

## 7. Entity Types & Tax Treatment

```mermaid
mindmap
  root((Entity Types))
    Individual
      Personal accounts
      Tax: Individual rates
    Joint
      Co-owned accounts
      Tax: Split reporting
    Trust
      Revocable/Irrevocable
      Tax: Pass-through or Entity
    LLC
      Single/Multi-member
      Tax: Disregarded or Partnership
    Partnership
      Tax: K-1 reporting
      Capital accounts
    S-Corp
      Tax: Pass-through
      Shareholder basis
    C-Corp
      Tax: Corporate rates
      Dividend taxation
    Foundation
      Tax: Exempt
      Charitable purpose
    Estate
      Tax: Estate/inheritance
      Probate assets
    Holding Company
      Tax: Varies
      Investment vehicle
```

## 8. Account Type Hierarchy

```mermaid
graph TD
    subgraph "Account Types"
        ASSET["ASSET<br/>Normal: Debit"]
        LIABILITY["LIABILITY<br/>Normal: Credit"]
        EQUITY["EQUITY<br/>Normal: Credit"]
        INCOME["INCOME<br/>Normal: Credit"]
        EXPENSE["EXPENSE<br/>Normal: Debit"]
    end
    
    subgraph "Asset Subtypes"
        ASSET --> CHK["Checking"]
        ASSET --> SAV["Savings"]
        ASSET --> BROK["Brokerage"]
        ASSET --> IRA["IRA/401k/529"]
        ASSET --> RE["Real Estate"]
        ASSET --> PE["Private Equity"]
        ASSET --> CRYPTO["Crypto"]
    end
    
    subgraph "Liability Subtypes"
        LIABILITY --> CC["Credit Card"]
        LIABILITY --> LOAN["Loan"]
    end
    
    subgraph "Equity Subtypes"
        EQUITY --> CAP["Member's Capital"]
        EQUITY --> RET["Retained Earnings"]
    end
    
    style ASSET fill:#c8e6c9
    style LIABILITY fill:#ffcdd2
    style EQUITY fill:#e1f5fe
    style INCOME fill:#c8e6c9
    style EXPENSE fill:#ffcdd2
```

## 9. Diamond Ownership Pattern (Fixed Bug)

```mermaid
graph TD
    subgraph "Diamond Structure"
        ROOT["Root (Individual)<br/>Alice"]
        LEFT["Left Path<br/>Trust A"]
        RIGHT["Right Path<br/>Trust B"]
        BOTTOM["Bottom<br/>LLC"]
    end
    
    ROOT -->|"50%"| LEFT
    ROOT -->|"50%"| RIGHT
    LEFT -->|"50%"| BOTTOM
    RIGHT -->|"50%"| BOTTOM
    
    subgraph "Effective Ownership Calculation"
        CALC["Alice's effective ownership of LLC:<br/>Path 1: 50% × 50% = 25%<br/>Path 2: 50% × 50% = 25%<br/>Total: 25% + 25% = 50%"]
    end
    
    BOTTOM --> CALC
    
    style ROOT fill:#c8e6c9
    style BOTTOM fill:#fff3e0
    style CALC fill:#e1f5fe
```
