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

## ANTI-PATTERNS (THIS PROJECT)
- None documented.

## NOTES
- bank_parsers.py handles multiple date formats and currency symbols
- Factory pattern for parser selection based on file content
- Excel support requires openpyxl (optional dependency)
