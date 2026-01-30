# Project Overview

## Atlas Family Office Ledger

**Version:** 0.1.0  
**License:** MIT  
**Python Version:** 3.12+

## Purpose

Atlas Family Office Ledger is a comprehensive double-entry accounting and investment management system designed specifically for family offices. It enables financial professionals to manage complex multi-entity structures (LLCs, trusts, partnerships, holding companies) with full investment position tracking, tax lot management, and consolidated reporting.

## Problem Solved

Family offices face unique challenges in financial management:
- **Multi-entity complexity**: Managing finances across LLCs, trusts, partnerships, and holding companies
- **Investment tracking**: Position management with multiple cost basis methods (FIFO, LIFO, Specific ID, Average Cost, Min/Max Gain)
- **Tax compliance**: QSBS tracking, Schedule D generation, Form 8949 preparation
- **Reconciliation**: Matching imported bank/broker statements with ledger transactions
- **Consolidated reporting**: Cross-entity financial reports and portfolio analytics

Atlas provides an integrated solution addressing all these needs with a modern Python architecture.

## Target Audience

- **Family office administrators** managing multi-entity wealth structures
- **Financial advisors** requiring comprehensive investment tracking
- **Tax professionals** needing accurate cost basis and tax document generation
- **Developers** building custom family office solutions

## Key Capabilities

| Capability | Description |
|------------|-------------|
| **Multi-Entity Management** | LLCs, trusts, partnerships, holding companies with configurable tax treatments |
| **Double-Entry Accounting** | Immutable transaction journal with full audit trail |
| **Investment Tracking** | Positions, tax lots, corporate actions (splits, spinoffs, mergers) |
| **Reconciliation** | Bank/broker statement import and matching workflow |
| **Multi-Currency** | 19 currencies with exchange rate management |
| **Budgeting** | Budget creation with variance tracking and alerts |
| **Expense Management** | Categorization, vendor tracking, recurring expense detection |
| **Tax Documents** | Schedule D, Form 8949, QSBS qualification tracking |
| **Ownership Graph** | Addepar-style household grouping and look-through net worth |
| **Portfolio Analytics** | Asset allocation, concentration analysis, performance metrics |

## Interfaces

The system provides three interfaces:
1. **CLI** (`fol` command): Full-featured command-line interface
2. **REST API**: FastAPI-based with 80+ endpoints
3. **Streamlit UI**: Production-ready web interface (14 pages)

## Architecture Summary

```
Domain Layer (entities, transactions, value objects)
       ↓
Repository Layer (SQLite/PostgreSQL persistence)
       ↓
Service Layer (business logic, 17 services)
       ↓
Interface Layer (CLI, FastAPI API, Streamlit UI)
```

The application follows a clean layered architecture with clear separation of concerns, interface-based dependency injection, and comprehensive test coverage (1190+ tests).
