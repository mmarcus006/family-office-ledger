# Partnership & Family Office Accounting Software: Data Model Comparative Analysis

**Version:** 1.0
**Date:** January 2026
**Purpose:** Comprehensive comparison of data models across partnership accounting and family office software platforms

---

## Executive Summary

This report analyzes the data models of 14 leading partnership accounting and family office software platforms. The analysis reveals three dominant architectural patterns:

### Pattern 1: Graph-Based Ownership (Addepar, LemonEdge, Masttro)
- Entities as nodes, ownership relationships as edges
- Supports fractional ownership, joint ownership, look-through
- Most flexible for complex family structures

### Pattern 2: Hierarchical Tree (Archway, Asset Vantage, Eton AtlasFive)
- Strict parent-child relationships
- Natural for consolidation accounting
- Simpler but less flexible for complex ownership

### Pattern 3: Partnership-Centric (FundCount, Investran, Allvue)
- GP/LP relationships as primary organizing principle
- Capital accounts and waterfalls as core constructs
- Optimized for fund accounting, less suited for personal wealth

### Key Insight
**Addepar's "Financial Graph" model** (Household → Client → Legal Entity → Account → Investment, with percentage-based ownership edges) represents the most sophisticated approach for family office use cases. It balances flexibility with comprehensibility.

---

## Part 1: Individual Platform Data Models

### 1.1 Addepar

**Architecture Type:** Graph-Based Ownership (Financial Graph)

**Entity Hierarchy:**
```
Household
├── Client (Person)
│   ├── Legal Entity (Trust, LLC, Partnership, etc.)
│   │   ├── Account
│   │   │   └── Investment
│   │   └── Legal Entity (nested)
│   └── Account (direct)
│       └── Investment
└── Client (Person)
    └── ...
```

**Core Data Model:**

| Entity Type | Description | Can Own |
|-------------|-------------|---------|
| **Household** | Top-level grouping for a family | All below |
| **Client** | Beneficial owner (natural person) | Legal Entities, Accounts, Investments |
| **Legal Entity** | Trust, LLC, Partnership, etc. | Legal Entities, Accounts, Investments |
| **Account** | Custodial account at institution | Accounts (sub-accounts), Investments |
| **Investment** | Security position | Nothing |

**Position (Edge) Model:**
```json
{
  "owner_id": "entity_123",
  "owned_id": "entity_456",
  "ownership_percentage": 50.0,
  "value": 500000,
  "inception_date": "2020-01-15",
  "ownership_type": "percent_based | share_based"
}
```

**Key API Entities:**
- `PERSON_NODE` - Clients/people
- `FINANCIAL_ACCOUNT` - Accounts
- `STOCK`, `BOND`, `MUTUAL_FUND` - Investment types
- Custom entity types via Entity Types API

**Strengths:**
- True graph model enables any ownership structure
- Percentage-based ownership supports look-through
- Joint ownership is first-class concept
- Well-documented REST API

**Limitations:**
- Steep learning curve
- Enterprise pricing
- No built-in general ledger

**Sources:** [Addepar Developer Portal](https://developers.addepar.com/docs/about-addepar), [Entities API](https://developers.addepar.com/docs/entities), [Positions API](https://developers.addepar.com/docs/positions)

---

### 1.2 SEI Archway Platform

**Architecture Type:** Hierarchical Tree with Partnership Accounting

**Entity Hierarchy:**
```
Family Office
├── Individual
│   ├── Trust
│   │   └── Account
│   ├── LLC
│   │   └── Account
│   └── Direct Account
├── Foundation
│   └── Account
└── Partnership (Master-Feeder)
    ├── Feeder Fund
    │   └── Account
    └── Feeder Fund
        └── Account
```

**Core Data Model:**

| Entity Type | Description | Key Attributes |
|-------------|-------------|----------------|
| **Entity** | Individual, Trust, Foundation, LLC, LP | Type, Tax ID, Chart of Accounts |
| **Account** | Custodial account | Custodian, Currency, Connection |
| **Holding** | Position in account | Security, Quantity, Cost Basis |
| **Transaction** | Atomic movement | Type, Amount, Date, Allocation |

**Partnership Accounting Features:**
- N-tier ownership structures
- Look-through reporting across nested entities
- Automated ownership calculations (contributions/withdrawals)
- P/L allocation from top-level through underlying entities
- Multi-currency chart of accounts (~150 entities supported)

**Key Differentiators:**
- Core general ledger foundation
- Automated accounting record creation
- Fund accounting integration
- Direct custodian data feeds

**Limitations:**
- Less flexible than graph model for unusual structures
- Enterprise-focused pricing and implementation

**Sources:** [Archway Family Office Software](https://www.archwaytechnology.net/family-office-accounting-software), [Archway Platform](https://www.archwaytechnology.net/archway-platform)

---

### 1.3 Asset Vantage

**Architecture Type:** Hierarchical with Accounting Integration

**Entity Hierarchy:**
```
Family
├── Entity (Individual, Trust, LLC, Partnership, etc.)
│   ├── Account (Brokerage, Bank, Alternative)
│   │   ├── Holding
│   │   │   └── Lot
│   │   └── Transaction
│   └── Private Asset (Real Estate, Art, etc.)
└── Entity
    └── ...
```

**Core Data Model:**

| Entity Type | Description | Key Attributes |
|-------------|-------------|----------------|
| **Entity** | Legal structure with tax ID | Type (Individual, Trust, LLC, Partnership, S-Corp, Estate, Foundation), Tax ID |
| **Account** | Connection to custodian/bank | Institution, Account Number, Asset Class |
| **Holding** | Position | Security, Quantity, Current Value |
| **Transaction** | Cash flow event | Type, Amount, Date, Entity, Beneficiary |

**Transaction Classification:**
Automated workflows classify each transaction by:
- Asset class
- Entity
- Beneficiary

**Asset Class Coverage:**
- Public securities
- Private equity/venture capital
- Real estate
- Personal assets (homes, planes, cars, insurance, collectibles)

**Key Differentiators:**
- Accounting-first design (positions align with GL)
- 45+ custodian integrations
- Private equity cash flow tracking (capital calls, distributions)
- Multi-family office support with data isolation

**Sources:** [Asset Vantage](https://www.assetvantage.com/), [Family Office Exchange - Asset Vantage](https://www.familyoffice.com/technology-partner/assetvantage)

---

### 1.4 Masttro

**Architecture Type:** Graph-Based with Document Intelligence

**Entity Hierarchy (WealthArchitecture):**
```
Estate/Family
├── Company
│   └── Account
├── Trust
│   ├── Beneficiary (linked)
│   └── Account
├── Individual
│   └── Account
└── Group
    └── Aggregated View
```

**Core Data Model:**

| Concept | Description | Key Attributes |
|---------|-------------|----------------|
| **Entity** | Any legal structure | Type, Jurisdiction, Ownership % |
| **Account** | Custodial connection | Custodian (650+ feeds), Currency |
| **Asset** | Financial or non-financial | Class, Value, Liquidity |
| **Relationship** | Ownership edge | Owner, Owned, Percentage |

**Visualization: Global Wealth Map**
- Interactive visualization connecting entities, trusts, assets, liabilities, beneficiaries
- Multi-currency support with flexible FX rate applications
- View entire estate across companies, trusts, groups, individuals

**Unique Features:**
- 650+ direct custodian connections (no screen-scraping)
- AI-powered document processing (Masttro Intelligence)
- Client-controlled encryption keys
- Swiss-based infrastructure

**Target Market:**
- UHNW single family offices
- Private banks
- RIAs

**Sources:** [Masttro](https://masttro.com/), [Masttro Family Office Software](https://masttro.com/family-office-software)

---

### 1.5 Eton Solutions AtlasFive

**Architecture Type:** Knowledge Graph with CRM Integration

**Entity Hierarchy:**
```
Family Office
├── Client (Individual)
│   ├── Portfolio
│   │   └── Account
│   │       └── Position
│   └── Relationship (to other clients)
├── Entity (Trust, LLC, Partnership, Holding Company)
│   ├── Ownership (linked to clients with %)
│   └── Account
└── Activity/Document
    └── Linked to Entity/Client
```

**Core Data Model (Proprietary):**

| Concept | Description | Key Attributes |
|---------|-------------|----------------|
| **Client** | Natural person | Contact info, Relationships |
| **Entity** | Legal structure | Type, Ownership structure |
| **Portfolio** | Grouping of accounts | Strategy, Benchmark |
| **Account** | Custodial account | Institution, Holdings |
| **Position** | Security holding | Quantity, Cost, Value |
| **Relationship** | Inter-entity connection | Type, Percentage |

**Knowledge Graph Integration:**
- CRM Knowledge Graph connects clients, entities, documents, activities
- AI (EtonAI) understands context and relationships between data points
- Enables automation of complex cognitive tasks

**Key Differentiators:**
- Single integrated database (one source of truth)
- Unlimited entities, accounts, relationships
- Fund and trust accounting built-in
- Tax ledger integration
- Microsoft Azure infrastructure

**Sources:** [AtlasFive](https://eton-solutions.com/solutions/atlasfive/), [Eton Solutions](https://andsimple.co/companies/eton-solutions/)

---

### 1.6 Sage Intacct

**Architecture Type:** Dimensional Multi-Entity Accounting

**Entity Hierarchy:**
```
Organization
├── Entity (Subsidiary/Legal Entity)
│   ├── Location (optional dimension)
│   ├── Department (optional dimension)
│   └── General Ledger
│       ├── Account
│       └── Journal Entry
└── Consolidation Rules
    ├── Eliminations
    └── Currency Translation
```

**Core Data Model:**

| Concept | Description | Key Attributes |
|---------|-------------|----------------|
| **Entity** | Legal subsidiary | Currency, Tax Rules, Chart of Accounts |
| **Dimension** | Flexible categorization | Location, Department, Project, Custom |
| **Account** | GL account | Type, Category, Balance |
| **Transaction** | Journal entry | Date, Amounts, Dimensions |
| **Consolidation** | Roll-up rules | Entity hierarchy, Eliminations |

**Dimensional Model:**
Instead of hard-coded account segments:
```
Traditional: 1000-100-NYC-SALES (Account-Dept-Location-Project)
Sage Intacct: Account 1000, tagged with dimensions
```

Dimensions can include:
- Location
- Department
- Project
- Customer/Vendor
- Custom dimensions (unlimited)

**Key Features:**
- Multi-entity consolidation (domestic + global)
- Automated intercompany eliminations (due-to/due-from)
- Multi-currency with CTA automation
- Inheritance-based entity templates
- Real-time dashboards by any dimension

**Limitations:**
- General accounting focus, not investment-specific
- No native tax lot tracking
- No built-in partnership accounting

**Sources:** [Sage Intacct Consolidation](https://www.sage.com/en-us/sage-business-cloud/intacct/product-capabilities/extended-capabilities/consolidation-accounting/), [Sage Intacct Dimensions](https://www.sage.com/en-us/sage-business-cloud/intacct/product-capabilities/extended-capabilities/financial-reporting/multi-dimensional-system/)

---

### 1.7 FundCount

**Architecture Type:** Integrated Partnership + Portfolio + GL

**Entity Hierarchy:**
```
Fund/Partnership
├── Partner (GP or LP)
│   ├── Capital Account
│   │   ├── Contribution
│   │   ├── Distribution
│   │   └── Allocation
│   └── K-1 Output
├── Investment
│   └── Position
└── General Ledger
    └── Integrated with above
```

**Core Data Model:**

| Concept | Description | Key Attributes |
|---------|-------------|----------------|
| **Fund** | Partnership vehicle | Structure (single/multi-class), Currency |
| **Partner** | GP or LP | Type, Commitment, Ownership % |
| **Capital Account** | Partner's equity | Contributions, Distributions, Allocations |
| **Investment** | Portfolio holding | Security, Cost, Fair Value |
| **Waterfall** | Distribution rules | Tiers, Hurdles, Carry |

**Nested Entity Control Center:**
- Visual display of family entity relationships
- Inter-entity reconciliation
- Investment activity disbursement through entity layers

**Continuous Accounting Paradigm:**
- All transactions through real-time general ledger
- No waiting for period-end to strike NAV
- Instant investor reporting

**Three Product Versions:**
1. **FC Portfolio** - Investment tracking only
2. **FC Partner** - Partnership accounting only
3. **FC Integrated** - Full integration of both

**Key Differentiators:**
- Portfolio + partnership + GL in single data model
- Master-feeder structure support
- Series of shares
- Waterfall calculations built-in

**Sources:** [FundCount](https://fundcount.com/), [FundCount Partnership Accounting](https://fundcount.com/solutions/partnership-accounting/)

---

### 1.8 Black Diamond Wealth Platform

**Architecture Type:** Hierarchical Portfolio Management

**Entity Hierarchy:**
```
Firm
├── Team
│   └── User
├── Client Relationship
│   └── Portfolio
│       └── Account
│           └── Position
│               └── Classification (Class/Segment)
└── Model/Target
    └── Allocation Rules
```

**Core Data Model:**

| Concept | Description | Key Attributes |
|---------|-------------|----------------|
| **Account** | Core data level | Custodian feed, Holdings |
| **Portfolio** | Account grouping | Can be for billing, rebalancing, reporting |
| **Client Relationship** | Typically owns portfolios | Contact, Objectives |
| **Class** | High-level asset classification | Equities, Fixed Income, Alternatives |
| **Segment** | Lower-level classification | Small Cap Value, Private Equity, Gov't Bonds |
| **Target** | Model allocation | Percentages by Class/Segment/Asset |
| **Manager** | Optional account grouping | Investment manager |
| **Style** | Optional strategy designation | Conservative, Aggressive, etc. |

**Classification Schema:**
- Customizable by firm
- Equity segments can be classified by market cap or sector
- N-tier model architecture (model of models)

**Key Features:**
- Advisor/RIA focused
- Performance reporting
- Rebalancing tools
- Integration with Schwab custody

**Limitations:**
- Less suited for complex ownership structures
- Limited partnership accounting
- Advisor-centric, not family office-centric

**Sources:** [Black Diamond Data Hierarchy](https://www.blackdiamondwealthplatform.com/bd_data_hierarchy), [Black Diamond Platform](https://blackdiamond.advent.com/platform/portfolio-management-reporting/)

---

### 1.9 FIS Investran (Private Capital Suite)

**Architecture Type:** Private Equity Fund Administration

**Entity Hierarchy:**
```
Fund
├── GP Vehicle
│   └── GP (General Partner)
├── LP Vehicle
│   └── LP (Limited Partner)
│       └── Capital Account
├── Portfolio
│   ├── Direct Deal (single issuer)
│   │   └── Security
│   └── Fund Deal (multiple issuers)
│       └── Securities
└── General Ledger
    └── Multi-currency
```

**Core Data Model:**

| Module | Entities | Key Attributes |
|--------|----------|----------------|
| **Security Master** | Issuer, Security, Income Security | Independent of portfolio, company-level data |
| **Fund** | GP Vehicle, LP Vehicle | Terms, Fee Structure, Carried Interest |
| **Investor** | GP, LP | Commitment, Assignment to Vehicle |
| **Deal** | Direct Deal, Fund Deal | Name, Currency, Fund Size |
| **Position** | Holdings | Cost, Fair Value, Income |

**Deal Types:**
- **Direct Deal**: Investing in single issuer (portfolio company)
- **Fund Deal**: Investing in multiple issuers (fund-of-funds)

**Fund Terms Captured:**
- Minimum/maximum investment
- Management fee
- Carried interest
- GP commitment percentage

**Key Features:**
- Automated waterfall calculations
- Management fee calculations
- Multi-currency ledger
- On-demand financial and performance reporting
- SQL-style custom report writer

**Sources:** [FIS Private Capital Suite](https://www.fisglobal.com/products/fis-private-capital-suite), [Investran Training](https://www.koenig-solutions.com/investran-training-course)

---

### 1.10 Allvue Systems

**Architecture Type:** GP/LP Partnership-Centric

**Entity Hierarchy:**
```
Fund
├── General Partner (GP)
│   └── Capital Account
├── Limited Partner (LP)
│   ├── Capital Account
│   │   ├── Capital Call
│   │   └── Distribution
│   └── Investor Class
├── Investment
│   └── Position
└── Waterfall
    └── Distribution Tiers
```

**Core Data Model:**

| Concept | Description | Key Attributes |
|---------|-------------|----------------|
| **Fund** | Investment vehicle | Structure, Vintage, Strategy |
| **Partner** | GP or LP | Commitment, Ownership %, Class |
| **Capital Account** | Partner's equity stake | Calls, Distributions, Allocations |
| **LPA** | Limited Partnership Agreement | Fee terms, Distribution policy |
| **Investment** | Portfolio holding | Security, Cost, NAV |
| **Waterfall** | Distribution model | Tiers, Hurdles, Carried Interest |

**Capital Activity Model:**
- **Inflows (LP → GP):** Capital calls, management fees
- **Outflows (GP → LP):** Cash distributions, stock distributions

**Waterfall Module:**
- Models complex LPAs
- Handles varied investor commitments and preferences
- Subsequent closing support for new investors
- Equity method accounting for lower-tier entities

**Technical Architecture:**
- Microsoft Dynamics 365 Business Central
- Microsoft Azure with multi-layered security
- Integration with Investment Accounting for private debt

**Sources:** [Allvue Fund Accounting](https://www.allvuesystems.com/solutions/fund-accounting/), [Allvue General Partners](https://www.allvuesystems.com/industries/general-partners/)

---

### 1.11 Juniper Square

**Architecture Type:** GP-LP Collaboration Platform

**Entity Hierarchy:**
```
Fund
├── GP Workspace
│   ├── Fund Structure
│   ├── Investor (LP)
│   │   └── LP Account
│   └── Capital Activity
└── LP Portal
    └── Shared View
```

**Core Data Model:**

| Concept | Description | Key Attributes |
|---------|-------------|----------------|
| **Fund** | Investment vehicle | 40,000+ funds on platform |
| **LP Account** | Investor relationship | 650,000+ LP accounts |
| **Capital Activity** | Calls/distributions | Transaction, Amount, Date |
| **Workspace** | GP management area | Permissions, Settings |
| **Portal** | LP viewing area | Reports, Documents |

**Scale:**
- 40,000+ funds
- 650,000+ LP accounts
- $1 trillion in LP capital managed

**Key Features:**
- Single source of truth for GP-LP collaboration
- Institutional-grade controls
- Robust permissioning
- API integrations and CSV uploads
- AI assistant (JunieAI)

**Focus:**
- Fundraising
- Investor operations
- Fund administration
- GP-LP communication

**Sources:** [Juniper Square](https://www.junipersquare.com/), [Juniper Square Platform](https://www.junipersquare.com/platform)

---

### 1.12 LemonEdge

**Architecture Type:** Low-Code Financial Services Platform

**Entity Hierarchy:**
```
Family Office / Fund Administrator
├── Family / Fund
│   ├── Entity (hierarchical)
│   │   ├── Child Entity
│   │   │   └── Account
│   │   └── Account
│   └── Direct Account
├── General Ledger
│   └── Multi-GAAP (IFRS, Local GAAP)
└── Waterfall Engine
    └── Lot-level calculations
```

**Core Data Model:**

| Concept | Description | Key Attributes |
|---------|-------------|----------------|
| **Entity** | Any legal structure | Hierarchical parent-child |
| **Account** | Custodial account | Holdings, Transactions |
| **Position** | Security holding | Cost, Value, Lots |
| **Allocation** | Distribution rules | Paths, Mappings, Rules |
| **Algorithm** | Custom waterfall logic | Programmable |

**Key Architectural Features:**
- **Open Architecture**: API-first design
- **Enterprise Data Tools**: Advanced modeling, reporting, workflow
- **Financial Services Engine**: GL, allocations, consolidations
- **Low-Code Platform**: Custom solutions 10x faster

**Asset Class Support:**
- Public securities
- Private equity, real estate, infrastructure, credit
- Personal assets (property, art, yachts, jewellery)
- Closed-ended and open-ended structures

**Consolidation Engine:**
- Multi-level structure consolidation
- Automated eliminations
- Multiple parallel charts of accounts (IFRS + local GAAP)

**Data Isolation:**
- "Data safes" for multi-family office providers
- Complete dataset isolation across clients

**Sources:** [LemonEdge Family Office](https://www.lemonedge.com/family-office-software), [LemonEdge Technical Architecture](https://www.lemonedge.com/technical-architecture)

---

### 1.13 Asora

**Architecture Type:** Hierarchical with Look-Through Visualization

**Entity Hierarchy:**
```
Family
├── Generation
│   ├── Individual
│   │   ├── Trust (beneficiary link)
│   │   └── Direct Account
│   └── Entity (LLC, Holding Co, SPV)
│       └── Account
└── Entity Tree
    └── Look-through calculations
```

**Core Data Model:**

| Concept | Description | Key Attributes |
|---------|-------------|----------------|
| **Family** | Top-level grouping | Generations, Members |
| **Entity** | Legal structure | Type, Ownership links |
| **Account** | Custodial account | Custodian, Holdings |
| **Holding** | Position | Security, Quantity, Value |
| **Relationship** | Ownership edge | Owner, Owned, Percentage |

**Look-Through Features:**
- "Wealth Map" visualization
- No double-counting when entities own entities
- Roll-up at any level (family, generation, entity, individual)
- Entity tree modeling (living, not hard-coded)

**Document-Data Linking:**
- Documents linked to entities, assets, accounts
- Creates secure vault mirroring data model

**Target Market:**
- Single and multi-family offices
- $100M–$1B+ AUM
- 5–50 entities

**Sources:** [Asora](https://asora.com/), [Asora vs Masttro](https://asora.com/blog/asora-vs-masttro)

---

### 1.14 Canoe Intelligence

**Architecture Type:** Document Intelligence + Data Extraction

**Data Model Focus:** Alternative investment document processing

**Document Types Processed:**
- Capital call notices
- Distribution notices
- Account statements
- K-1s
- Quarterly financials
- Performance estimates
- Manager letters

**Data Extraction Model:**
```
Document
├── Fund (identified from 42K+ fund database)
├── Extracted Fields
│   ├── Amounts
│   ├── Dates
│   ├── Securities
│   └── Classifications
└── Validation
    └── Output to downstream systems
```

**Technology:**
- NLP (Natural Language Processing)
- Text anchoring
- Spatial/coordinate recognition
- Machine learning pattern generation
- Table detection
- LLM-based contextual understanding

**Integration:**
- Flat file exports
- Open API
- Compatible with dozens of reporting/accounting providers
- 500+ connected GP portals

**Shared Intelligence:**
- Cross-client learning
- 42K+ fund database
- Pattern recognition improvements

**Sources:** [Canoe Intelligence](https://canoeintelligence.com/), [Canoe Data Extraction](https://canoeintelligence.com/the-canoe-optimized-workflow-step-3-data-extraction-2/)

---

## Part 2: Comparative Analysis

### 2.1 Entity Hierarchy Comparison

| Platform | Top Level | Person Level | Entity Level | Account Level | Investment Level |
|----------|-----------|--------------|--------------|---------------|------------------|
| **Addepar** | Household | Client | Legal Entity | Account | Investment |
| **Archway** | Family Office | Individual | Trust/LLC/LP | Account | Holding |
| **Asset Vantage** | Family | - | Entity | Account | Holding + Lot |
| **Masttro** | Estate/Family | Individual | Company/Trust | Account | Asset |
| **AtlasFive** | Family Office | Client | Entity | Account | Position |
| **Sage Intacct** | Organization | - | Entity | - | - |
| **FundCount** | Fund | Partner | - | - | Investment |
| **Black Diamond** | Firm | Client Relationship | Portfolio | Account | Position |
| **Investran** | Fund | GP/LP | Vehicle | - | Deal/Security |
| **Allvue** | Fund | GP/LP | - | - | Investment |
| **Juniper Square** | Fund | LP | - | LP Account | - |
| **LemonEdge** | Family Office | - | Entity (hierarchical) | Account | Position |
| **Asora** | Family | Individual | Entity | Account | Holding |

### 2.2 Ownership Model Comparison

| Platform | Ownership Model | Joint Ownership | Fractional % | Look-Through |
|----------|----------------|-----------------|--------------|--------------|
| **Addepar** | Graph (edges with %) | Yes | Yes | Yes |
| **Archway** | Hierarchical + allocation | Yes | Yes | Yes |
| **Asset Vantage** | Hierarchical | Limited | Yes | Yes |
| **Masttro** | Graph (Wealth Map) | Yes | Yes | Yes |
| **AtlasFive** | Knowledge Graph | Yes | Yes | Yes |
| **Sage Intacct** | Consolidation rules | No | Yes | Yes (financial) |
| **FundCount** | Partnership allocation | No | Yes | Yes |
| **Black Diamond** | Portfolio grouping | No | No | Limited |
| **Investran** | GP/LP assignment | No | Yes | Fund-level |
| **Allvue** | Capital account | No | Yes | Fund-level |
| **LemonEdge** | Hierarchical + rules | Yes | Yes | Yes |
| **Asora** | Tree + look-through | Yes | Yes | Yes |

### 2.3 Accounting Integration Comparison

| Platform | General Ledger | Partnership Accounting | Tax Lot Tracking | Waterfall Calc |
|----------|---------------|----------------------|------------------|----------------|
| **Addepar** | No | Limited | Yes | No |
| **Archway** | Yes (core) | Yes | Yes | Yes |
| **Asset Vantage** | Yes | Yes | Yes | Limited |
| **Masttro** | No | Limited | Limited | No |
| **AtlasFive** | Yes | Yes | Yes | Yes |
| **Sage Intacct** | Yes (core) | No | No | No |
| **FundCount** | Yes | Yes (core) | Yes | Yes |
| **Black Diamond** | No | No | Limited | No |
| **Investran** | Yes | Yes (core) | Yes | Yes |
| **Allvue** | Yes | Yes (core) | Yes | Yes |
| **LemonEdge** | Yes | Yes | Yes | Yes |
| **Asora** | No | Limited | Limited | No |

### 2.4 Data Model Sophistication Ranking

| Rank | Platform | Score | Rationale |
|------|----------|-------|-----------|
| 1 | **Addepar** | 95 | True graph model, documented API, flexible ownership |
| 2 | **LemonEdge** | 90 | Low-code platform, multi-GAAP, full hierarchy |
| 3 | **Archway** | 88 | Deep partnership + GL integration, look-through |
| 4 | **AtlasFive** | 85 | Knowledge graph, CRM integration, single database |
| 5 | **FundCount** | 83 | Integrated partnership + portfolio + GL |
| 6 | **Investran** | 82 | PE-focused, comprehensive fund accounting |
| 7 | **Allvue** | 80 | Strong GP/LP model, waterfall support |
| 8 | **Asset Vantage** | 78 | Accounting-first, good entity support |
| 9 | **Masttro** | 75 | Strong visualization, less accounting depth |
| 10 | **Asora** | 72 | Good look-through, limited GL |
| 11 | **Sage Intacct** | 70 | Excellent GL, no investment-specific features |
| 12 | **Black Diamond** | 65 | Portfolio-focused, limited entity model |
| 13 | **Juniper Square** | 60 | GP-LP focused, less data model depth |
| 14 | **Canoe** | N/A | Document extraction, not a data model |

---

## Part 3: Key Architectural Patterns

### 3.1 Pattern: Graph-Based Ownership

**Used by:** Addepar, Masttro, AtlasFive (Knowledge Graph)

**Concept:**
```
Entities = Nodes
Ownership = Edges (with percentage, value, inception date)
```

**Advantages:**
- Any ownership structure can be modeled
- Joint ownership is natural (multiple edges)
- Look-through calculations traverse edges
- Supports fractional beneficial ownership

**Implementation:**
```json
// Addepar-style Position (Edge)
{
  "owner_entity_id": "client_123",
  "owned_entity_id": "trust_456",
  "ownership_percentage": 50.0,
  "value": 500000,
  "inception_date": "2020-01-01"
}
```

### 3.2 Pattern: Hierarchical Tree with Consolidation

**Used by:** Archway, Sage Intacct, Asset Vantage

**Concept:**
```
Parent Entity
└── Child Entity (100% owned assumed unless specified)
    └── Account
        └── Holding
```

**Advantages:**
- Simpler to understand
- Natural for accounting consolidation
- Clear parent-child relationships

**Limitations:**
- Joint ownership requires workarounds
- Cross-ownership (A owns B, B owns C, C owns A) is problematic

### 3.3 Pattern: Partnership Capital Accounts

**Used by:** FundCount, Investran, Allvue, Archway

**Concept:**
```
Fund
├── Partner (GP or LP)
│   └── Capital Account
│       ├── Beginning Balance
│       ├── + Contributions
│       ├── + Income Allocations
│       ├── - Distributions
│       ├── +/- Gain/Loss Allocations
│       └── = Ending Balance
└── Waterfall (distribution rules)
```

**Advantages:**
- Accurate partner equity tracking
- Supports complex allocation rules
- Tax reporting (K-1) friendly

**Waterfall Tiers (typical):**
1. Return of Capital (ROC)
2. Preferred Return (hurdle rate, typically 8%)
3. GP Catch-up
4. Carried Interest Split (typically 80/20)

### 3.4 Pattern: Dimensional Tagging

**Used by:** Sage Intacct, Asset Vantage

**Concept:**
Every transaction tagged with multiple dimensions instead of hard-coded account segments.

```
Transaction: $10,000
├── Account: Revenue
├── Dimension: Location = NYC
├── Dimension: Department = Sales
├── Dimension: Entity = Trust A
└── Dimension: Custom = Project X
```

**Advantages:**
- Flexible reporting
- No combinatorial explosion of account codes
- Easy to add new dimensions

---

## Part 4: Recommendations for Your Application

### 4.1 Recommended Data Model Architecture

Based on this analysis, I recommend adopting **Addepar's Financial Graph model** with enhancements:

```
RECOMMENDED HIERARCHY
═════════════════════

Household (top-level family grouping)
│
├── Client (beneficial owner - natural person)
│   │   • SSN/Tax ID
│   │   • Tax Filing Status
│   │
│   ├── [Direct] Account
│   │   └── Holding → Lot → Transaction
│   │
│   └── [Through Entity] ──% ownership──> Legal Entity
│
├── Legal Entity (Trust, LLC, Partnership, etc.)
│   │   • EIN
│   │   • Entity Type
│   │   • Tax Treatment (pass-through, C-corp, exempt)
│   │   • Ownership: List of (Client/Entity, %)
│   │
│   ├── Account
│   │   └── Holding → Lot → Transaction
│   │
│   └── [Nested] ──% ownership──> Child Legal Entity
│
└── Joint Ownership
    │   • Owners: List of (Client, %)
    │
    └── Account
        └── Holding → Lot → Transaction
```

### 4.2 Key Data Entities to Implement

| Entity | Key Attributes | Relationships |
|--------|---------------|---------------|
| **Household** | name, primary_contact | → Clients, Entities |
| **Client** | name, ssn, tax_status | → Entities (with %), Accounts |
| **Legal Entity** | name, ein, type, tax_treatment | → Accounts, Child Entities |
| **Ownership Edge** | owner_id, owned_id, percentage, inception_date | Links all above |
| **Account** | institution, account_number, type, cost_basis_method | → Holdings |
| **Holding** | security_id, quantity, current_value | → Lots |
| **Lot** | quantity, acquisition_date, cost_basis, holding_period | → Transactions |
| **Transaction** | type, date, quantity, price, lot_assignment | Atomic event |

### 4.3 Features to Prioritize from Each Platform

| Feature | Source Platform | Priority |
|---------|-----------------|----------|
| Graph-based ownership with % edges | Addepar | **Must-Have** |
| Look-through calculations | Archway, Asora | **Must-Have** |
| Tax lot tracking at transaction level | Archway, Asset Vantage | **Must-Have** |
| Ownership visualization (Wealth Map) | Masttro, Asora | **Should-Have** |
| Partnership capital accounts | FundCount | **Should-Have** |
| Waterfall calculations | FundCount, LemonEdge | **Nice-to-Have** |
| Dimensional tagging | Sage Intacct | **Nice-to-Have** |
| Document extraction | Canoe | **Future** |

### 4.4 Implementation Approach

**Phase 1: Core Ownership Model**
- Household → Client → Entity → Account hierarchy
- Percentage-based ownership edges
- Basic look-through calculations

**Phase 2: Investment Accounting**
- Tax lot tracking
- Cost basis methods (FIFO, LIFO, HIFO, SpecID)
- Transaction reconciliation

**Phase 3: Partnership Features**
- Capital account tracking
- K-1 allocation support
- Basic waterfall calculations

**Phase 4: Advanced Features**
- Multi-currency consolidation
- General ledger integration
- Document processing

---

## Appendix: Sources

### Primary Sources

- [Addepar Developer Portal](https://developers.addepar.com/)
- [Archway Platform](https://www.archwaytechnology.net/)
- [Asset Vantage](https://www.assetvantage.com/)
- [Masttro](https://masttro.com/)
- [Eton Solutions AtlasFive](https://eton-solutions.com/solutions/atlasfive/)
- [Sage Intacct](https://www.sage.com/en-us/sage-business-cloud/intacct/)
- [FundCount](https://fundcount.com/)
- [Black Diamond](https://blackdiamond.advent.com/)
- [FIS Investran](https://www.fisglobal.com/products/fis-private-capital-suite)
- [Allvue Systems](https://www.allvuesystems.com/)
- [Juniper Square](https://www.junipersquare.com/)
- [LemonEdge](https://www.lemonedge.com/)
- [Asora](https://asora.com/)
- [Canoe Intelligence](https://canoeintelligence.com/)

### Industry Reports

- [Family Office Software & Technology Report 2025 - Simple](https://andsimple.co/reports/family-office-software/)
- [Top 6 Accounting Platforms for Modern Family Offices 2025 - Asseta](https://www.asseta.ai/resources/the-top-6-accounting-platforms-for-modern-family-offices-for-2025)
- [Best Family Office Software 2026 - Masttro](https://masttro.com/insights/best-family-office-software)

---

*Report prepared for investment accounting application design. Data gathered January 2026.*
