<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-29 | Updated: 2026-01-31 -->

# PARSERS LAYER

## OVERVIEW
Bank/broker statement parsing into standardized ParsedTransaction records.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Bank parsers | bank_parsers.py | 762 lines, BankParser ABC + 3 implementations |
| CSV parsing | csv_parser.py | generic CSV |
| OFX/QFX parsing | ofx_parser.py | OFXParser |
| Public exports | __init__.py | curated `__all__` |

## CONVENTIONS
- `BankParser` is ABC; concrete parsers implement `parse()` and `detect()`
- `ParsedTransaction` is shared dataclass across all parsers
- `BankParserFactory.create()` returns appropriate parser based on file content

## BANK PARSERS
| Parser | Format | Notes |
|--------|--------|-------|
| CitiParser | CSV | `=T("...")` account extraction via regex |
| UBSParser | CSV | metadata row skip |
| MorganStanleyParser | Excel | uses openpyxl |

## ParsedTransaction FIELDS
```python
@dataclass
class ParsedTransaction:
    import_id: str
    date: date
    description: str
    amount: Decimal
    account_number: str | None
    account_name: str | None
    other_party: str | None
    symbol: str | None
    cusip: str | None
    quantity: Decimal | None
    price: Decimal | None
    activity_type: str | None
    raw_data: dict[str, Any]
```

## ANTI-PATTERNS (THIS PROJECT)
- bank_parsers.py has deep nesting (14 levels) - extract format-specific logic candidate

## NOTES
- bank_parsers.py handles 7 date formats: %Y-%m-%d, %m/%d/%Y, %m/%d/%y, %d/%m/%Y, %Y/%m/%d, %m-%d-%Y, %d-%m-%Y
- Factory pattern for parser selection based on file content
- Excel support requires openpyxl (optional dependency)
