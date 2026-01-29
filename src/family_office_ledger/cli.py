"""Command-line interface for Family Office Ledger."""

import argparse
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from family_office_ledger.domain.reconciliation import ReconciliationMatchStatus
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteExchangeRateRepository,
    SQLitePositionRepository,
    SQLiteReconciliationSessionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
    SQLiteTransactionRepository,
    SQLiteVendorRepository,
)
from family_office_ledger.services.expense import ExpenseServiceImpl
from family_office_ledger.domain.vendors import Vendor
from family_office_ledger.services.ingestion import IngestionService
from family_office_ledger.services.ledger import LedgerServiceImpl
from family_office_ledger.services.lot_matching import LotMatchingServiceImpl
from family_office_ledger.services.reconciliation import (
    MatchNotFoundError,
    ReconciliationServiceImpl,
    SessionExistsError,
    SessionNotFoundError,
)
from family_office_ledger.services.transaction_classifier import TransactionClassifier
from family_office_ledger.services.transfer_matching import (
    TransferMatchingService,
    TransferMatchNotFoundError,
    TransferSessionNotFoundError,
)
from family_office_ledger.domain.transfer_matching import TransferMatchStatus
from family_office_ledger.services.qsbs import QSBSService, SecurityNotFoundError
from family_office_ledger.services.tax_documents import TaxDocumentService
from family_office_ledger.services.portfolio_analytics import PortfolioAnalyticsService
from family_office_ledger.services.currency import (
    CurrencyServiceImpl,
    ExchangeRateNotFoundError,
)
from family_office_ledger.domain.exchange_rates import ExchangeRate, ExchangeRateSource


def get_default_db_path() -> Path:
    """Get the default database path in user's home directory."""
    return Path.home() / ".family_office_ledger" / "ledger.db"


def create_app(db_path: Path | None = None) -> tuple[SQLiteDatabase, LedgerServiceImpl]:
    """Create and initialize the application with database and services."""
    if db_path is None:
        db_path = get_default_db_path()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = SQLiteDatabase(str(db_path))
    db.initialize()

    entity_repo = SQLiteEntityRepository(db)
    account_repo = SQLiteAccountRepository(db)
    transaction_repo = SQLiteTransactionRepository(db)

    ledger_service = LedgerServiceImpl(
        transaction_repo=transaction_repo,
        account_repo=account_repo,
        entity_repo=entity_repo,
    )

    return db, ledger_service


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new database."""
    db_path = Path(args.database) if args.database else get_default_db_path()

    if db_path.exists() and not args.force:
        print(f"Database already exists at {db_path}")
        print("Use --force to reinitialize (WARNING: will delete existing data)")
        return 1

    if db_path.exists() and args.force:
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = SQLiteDatabase(str(db_path))
    db.initialize()

    print(f"Initialized database at {db_path}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show database status."""
    db_path = Path(args.database) if args.database else get_default_db_path()

    if not db_path.exists():
        print(f"No database found at {db_path}")
        print("Run 'fol init' to create a new database")
        return 1

    db = SQLiteDatabase(str(db_path))
    entity_repo = SQLiteEntityRepository(db)
    account_repo = SQLiteAccountRepository(db)

    entities = list(entity_repo.list_all())
    print(f"Database: {db_path}")
    print(f"Entities: {len(entities)}")

    for entity in entities:
        accounts = list(account_repo.list_by_entity(entity.id))
        status = "active" if entity.is_active else "inactive"
        print(
            f"  - {entity.name} ({entity.entity_type.value}) [{status}]: {len(accounts)} accounts"
        )

    return 0


def cmd_version(args: argparse.Namespace) -> int:
    """Show version information."""
    print("Family Office Ledger v0.1.0")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Ingest bank transaction file."""
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1

    db_path = Path(args.database) if args.database else get_default_db_path()

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("Run 'fol init' to create a new database")
        return 1

    try:
        # Initialize database and repositories
        db = SQLiteDatabase(str(db_path))
        entity_repo = SQLiteEntityRepository(db)
        account_repo = SQLiteAccountRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        security_repo = SQLiteSecurityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)

        # Initialize services
        ledger_service = LedgerServiceImpl(
            transaction_repo=transaction_repo,
            account_repo=account_repo,
            entity_repo=entity_repo,
        )
        lot_matching_service = LotMatchingServiceImpl(
            position_repo=position_repo,
            tax_lot_repo=tax_lot_repo,
        )
        transaction_classifier = TransactionClassifier()

        # Create ingestion service
        ingestion_service = IngestionService(
            entity_repo=entity_repo,
            account_repo=account_repo,
            security_repo=security_repo,
            position_repo=position_repo,
            tax_lot_repo=tax_lot_repo,
            ledger_service=ledger_service,
            lot_matching_service=lot_matching_service,
            transaction_classifier=transaction_classifier,
        )

        # Ingest the file
        default_entity = args.default_entity if args.default_entity else None
        result = ingestion_service.ingest_file(str(file_path), default_entity)

        # Print results
        print(f"✓ Ingestion complete")
        print(f"  Transactions: {result.transaction_count}")
        print(f"  Entities: {result.entity_count}")
        print(f"  Accounts: {result.account_count}")
        print(f"  Tax lots: {result.tax_lot_count}")

        if result.type_breakdown:
            print(f"  Transaction types:")
            for txn_type, count in sorted(result.type_breakdown.items()):
                print(f"    - {txn_type.value}: {count}")

        if result.errors:
            print(f"\n⚠ {len(result.errors)} error(s) encountered:")
            for error in result.errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(result.errors) > 10:
                print(f"  ... and {len(result.errors) - 10} more")
            return 1

        return 0

    except Exception as e:
        print(f"Error during ingestion: {e}")
        return 1


def cmd_ui(args: argparse.Namespace) -> int:
    """Launch the Streamlit web interface."""
    try:
        import streamlit.web.cli as stcli
    except ImportError:
        print("Frontend dependencies are not installed.")
        print("Install with: uv sync --all-extras")
        return 1

    import os
    from pathlib import Path

    port = int(args.port)
    api_url = str(args.api_url)

    app_path = Path(__file__).parent / "streamlit_app" / "app.py"
    if not app_path.exists():
        print(f"Error: Streamlit app not found at {app_path}")
        return 1

    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    os.environ["FOL_API_URL"] = api_url

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    stcli.main()
    return 0


def cmd_reconcile_create(args: argparse.Namespace) -> int:
    """Create a new reconciliation session."""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1

    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        account_id = UUID(args.account_id)
    except ValueError:
        print(f"Error: Invalid account ID: {args.account_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        session_repo = SQLiteReconciliationSessionRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = ReconciliationServiceImpl(
            transaction_repo, account_repo, session_repo
        )

        file_format = args.format if args.format else "csv"
        session = service.create_session(account_id, str(file_path), file_format)

        print(f"Session created: {session.id}")
        print(f"  Account: {session.account_id}")
        print(f"  File: {session.file_name}")
        print(f"  Matches: {len(session.matches)}")
        return 0

    except SessionExistsError:
        print("Error: A pending session already exists for this account")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_reconcile_list(args: argparse.Namespace) -> int:
    """List matches in a reconciliation session."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        session_id = UUID(args.session_id)
    except ValueError:
        print(f"Error: Invalid session ID: {args.session_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        session_repo = SQLiteReconciliationSessionRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = ReconciliationServiceImpl(
            transaction_repo, account_repo, session_repo
        )

        status_filter = None
        if args.status:
            status_filter = ReconciliationMatchStatus(args.status)

        limit = args.limit if args.limit else 50
        offset = args.offset if args.offset else 0

        matches, total = service.list_matches(session_id, status_filter, limit, offset)

        print(
            f"{'Match ID':<40} {'Status':<12} {'Amount':<12} {'Date':<12} Description"
        )
        print("-" * 100)
        for match in matches:
            amount_str = f"${match.imported_amount}"
            print(
                f"{str(match.id):<40} {match.status.value:<12} {amount_str:<12} "
                f"{match.imported_date} {match.imported_description[:30]}"
            )

        start = offset + 1
        end = min(offset + len(matches), total)
        print(f"Total: {total} matches (showing {start}-{end})")
        return 0

    except SessionNotFoundError:
        print("Error: Session not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_reconcile_confirm(args: argparse.Namespace) -> int:
    """Confirm a match in a reconciliation session."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        session_id = UUID(args.session_id)
        match_id = UUID(args.match_id)
    except ValueError as e:
        print(f"Error: Invalid UUID: {e}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        session_repo = SQLiteReconciliationSessionRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = ReconciliationServiceImpl(
            transaction_repo, account_repo, session_repo
        )

        service.confirm_session_match(session_id, match_id)
        print(f"Match {match_id} confirmed")
        return 0

    except SessionNotFoundError:
        print("Error: Session not found")
        return 1
    except MatchNotFoundError:
        print("Error: Match not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_reconcile_reject(args: argparse.Namespace) -> int:
    """Reject a match in a reconciliation session."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        session_id = UUID(args.session_id)
        match_id = UUID(args.match_id)
    except ValueError as e:
        print(f"Error: Invalid UUID: {e}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        session_repo = SQLiteReconciliationSessionRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = ReconciliationServiceImpl(
            transaction_repo, account_repo, session_repo
        )

        service.reject_session_match(session_id, match_id)
        print(f"Match {match_id} rejected")
        return 0

    except SessionNotFoundError:
        print("Error: Session not found")
        return 1
    except MatchNotFoundError:
        print("Error: Match not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_reconcile_skip(args: argparse.Namespace) -> int:
    """Skip a match in a reconciliation session."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        session_id = UUID(args.session_id)
        match_id = UUID(args.match_id)
    except ValueError as e:
        print(f"Error: Invalid UUID: {e}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        session_repo = SQLiteReconciliationSessionRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = ReconciliationServiceImpl(
            transaction_repo, account_repo, session_repo
        )

        service.skip_session_match(session_id, match_id)
        print(f"Match {match_id} skipped")
        return 0

    except SessionNotFoundError:
        print("Error: Session not found")
        return 1
    except MatchNotFoundError:
        print("Error: Match not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_reconcile_close(args: argparse.Namespace) -> int:
    """Close a reconciliation session."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        session_id = UUID(args.session_id)
    except ValueError:
        print(f"Error: Invalid session ID: {args.session_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        session_repo = SQLiteReconciliationSessionRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = ReconciliationServiceImpl(
            transaction_repo, account_repo, session_repo
        )

        session = service.close_session(session_id)
        print(f"Session {session_id} closed (status: {session.status.value})")
        return 0

    except SessionNotFoundError:
        print("Error: Session not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_reconcile_summary(args: argparse.Namespace) -> int:
    """Show summary statistics for a reconciliation session."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        session_id = UUID(args.session_id)
    except ValueError:
        print(f"Error: Invalid session ID: {args.session_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        session_repo = SQLiteReconciliationSessionRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = ReconciliationServiceImpl(
            transaction_repo, account_repo, session_repo
        )

        summary = service.get_session_summary(session_id)
        print("Session Summary")
        print(f"  Total: {summary.total_imported}")
        print(f"  Confirmed: {summary.confirmed}")
        print(f"  Rejected: {summary.rejected}")
        print(f"  Skipped: {summary.skipped}")
        print(f"  Pending: {summary.pending}")
        print(f"  Match Rate: {summary.match_rate * 100:.1f}%")
        return 0

    except SessionNotFoundError:
        print("Error: Session not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_transfer_create(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        entity_ids = None
        if args.entity_ids:
            entity_ids = [UUID(eid.strip()) for eid in args.entity_ids.split(",")]

        start_date = None
        end_date = None
        if args.start_date:
            from datetime import date as dt_date

            start_date = dt_date.fromisoformat(args.start_date)
        if args.end_date:
            from datetime import date as dt_date

            end_date = dt_date.fromisoformat(args.end_date)

        db = SQLiteDatabase(str(db_path))
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = TransferMatchingService(transaction_repo, account_repo)

        session = service.create_session(
            entity_ids=entity_ids,
            start_date=start_date,
            end_date=end_date,
            date_tolerance_days=args.tolerance,
        )

        print(f"Session created: {session.id}")
        print(f"Found {len(session.matches)} potential transfer matches")
        return 0

    except ValueError as e:
        print(f"Error: Invalid input: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_transfer_list(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        session_id = UUID(args.session_id)
    except ValueError:
        print(f"Error: Invalid session ID: {args.session_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = TransferMatchingService(transaction_repo, account_repo)

        status_filter = None
        if args.status:
            status_filter = TransferMatchStatus(args.status)

        matches = service.list_matches(session_id, status=status_filter)

        print(f"{'Match ID':<40} {'Status':<12} {'Amount':<15} {'Date':<12}")
        print("-" * 85)
        for match in matches:
            amount_str = f"${match.amount}"
            print(
                f"{str(match.id):<40} {match.status.value:<12} "
                f"{amount_str:<15} {match.transfer_date}"
            )

        print(f"Total: {len(matches)} matches")
        return 0

    except TransferSessionNotFoundError:
        print("Error: Session not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_transfer_confirm(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        session_id = UUID(args.session_id)
        match_id = UUID(args.match_id)
    except ValueError as e:
        print(f"Error: Invalid UUID: {e}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = TransferMatchingService(transaction_repo, account_repo)

        service.confirm_match(session_id, match_id)
        print(f"Match {match_id} confirmed")
        return 0

    except TransferSessionNotFoundError:
        print("Error: Session not found")
        return 1
    except TransferMatchNotFoundError:
        print("Error: Match not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_transfer_reject(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        session_id = UUID(args.session_id)
        match_id = UUID(args.match_id)
    except ValueError as e:
        print(f"Error: Invalid UUID: {e}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = TransferMatchingService(transaction_repo, account_repo)

        service.reject_match(session_id, match_id)
        print(f"Match {match_id} rejected")
        return 0

    except TransferSessionNotFoundError:
        print("Error: Session not found")
        return 1
    except TransferMatchNotFoundError:
        print("Error: Match not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_transfer_close(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        session_id = UUID(args.session_id)
    except ValueError:
        print(f"Error: Invalid session ID: {args.session_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = TransferMatchingService(transaction_repo, account_repo)

        session = service.close_session(session_id)
        print(f"Session {session_id} closed (status: {session.status})")
        return 0

    except TransferSessionNotFoundError:
        print("Error: Session not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_transfer_summary(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        session_id = UUID(args.session_id)
    except ValueError:
        print(f"Error: Invalid session ID: {args.session_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        service = TransferMatchingService(transaction_repo, account_repo)

        summary = service.get_summary(session_id)
        print("Transfer Matching Summary")
        print(f"  Total Matches: {summary.total_matches}")
        print(f"  Confirmed: {summary.confirmed_count}")
        print(f"  Rejected: {summary.rejected_count}")
        print(f"  Pending: {summary.pending_count}")
        print(f"  Confirmed Amount: ${summary.total_confirmed_amount}")
        return 0

    except TransferSessionNotFoundError:
        print("Error: Session not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_qsbs_list(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        security_repo = SQLiteSecurityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)
        service = QSBSService(security_repo, position_repo, tax_lot_repo)

        securities = service.list_qsbs_eligible_securities()

        if not securities:
            print("No QSBS-eligible securities found")
            return 0

        print(f"{'Symbol':<12} {'Name':<30} {'Qualification Date':<20} {'Issuer'}")
        print("-" * 85)
        for sec in securities:
            qual_date = (
                sec.qsbs_qualification_date.isoformat()
                if sec.qsbs_qualification_date
                else "N/A"
            )
            issuer = sec.issuer or "N/A"
            print(f"{sec.symbol:<12} {sec.name[:28]:<30} {qual_date:<20} {issuer}")

        print(f"\nTotal: {len(securities)} QSBS-eligible securities")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_qsbs_mark(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        security_id = UUID(args.security_id)
    except ValueError:
        print(f"Error: Invalid security ID: {args.security_id}")
        return 1

    try:
        from datetime import date as dt_date

        qual_date = dt_date.fromisoformat(args.qualification_date)
    except ValueError:
        print(f"Error: Invalid date format: {args.qualification_date}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        security_repo = SQLiteSecurityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)
        service = QSBSService(security_repo, position_repo, tax_lot_repo)

        security = service.mark_security_qsbs_eligible(security_id, qual_date)
        print(f"Marked {security.symbol} ({security.name}) as QSBS-eligible")
        print(f"  Qualification date: {qual_date}")
        return 0

    except SecurityNotFoundError:
        print("Error: Security not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_qsbs_remove(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        security_id = UUID(args.security_id)
    except ValueError:
        print(f"Error: Invalid security ID: {args.security_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        security_repo = SQLiteSecurityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)
        service = QSBSService(security_repo, position_repo, tax_lot_repo)

        security = service.remove_qsbs_eligibility(security_id)
        print(f"Removed QSBS eligibility from {security.symbol} ({security.name})")
        return 0

    except SecurityNotFoundError:
        print("Error: Security not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_qsbs_summary(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        as_of_date = None
        if args.as_of:
            from datetime import date as dt_date

            as_of_date = dt_date.fromisoformat(args.as_of)

        db = SQLiteDatabase(str(db_path))
        security_repo = SQLiteSecurityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)
        service = QSBSService(security_repo, position_repo, tax_lot_repo)

        summary = service.get_qsbs_summary(as_of_date=as_of_date)

        print("QSBS Holdings Summary")
        print(f"  Total Holdings: {summary.total_qsbs_holdings}")
        print(f"  Qualified (5+ years): {summary.qualified_holdings}")
        print(f"  Pending: {summary.pending_holdings}")
        print(f"  Total Cost Basis: ${summary.total_cost_basis:,.2f}")
        print(f"  Potential Exclusion: ${summary.total_potential_exclusion:,.2f}")

        if summary.holdings:
            print(
                f"\n{'Symbol':<12} {'Held (days)':<12} {'Qualified':<10} {'Days Left':<12} {'Potential Exclusion'}"
            )
            print("-" * 70)
            for h in summary.holdings:
                status = "YES" if h.is_qualified else "NO"
                days_left = "-" if h.is_qualified else str(h.days_until_qualified)
                print(
                    f"{h.security_symbol:<12} {h.holding_period_days:<12} {status:<10} "
                    f"{days_left:<12} ${h.potential_exclusion:,.2f}"
                )

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_tax_generate(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        entity_id = UUID(args.entity_id)
    except ValueError:
        print(f"Error: Invalid entity ID: {args.entity_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        entity_repo = SQLiteEntityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)
        security_repo = SQLiteSecurityRepository(db)
        service = TaxDocumentService(
            entity_repo, position_repo, tax_lot_repo, security_repo
        )

        form_8949, schedule_d, summary = service.generate_from_entity(
            entity_id=entity_id,
            tax_year=args.tax_year,
        )

        print(f"Tax Documents for {summary.entity_name} - {summary.tax_year}")
        print("=" * 60)
        print(f"\nForm 8949 Summary:")
        print(f"  Short-term transactions: {summary.short_term_transactions}")
        print(f"  Long-term transactions: {summary.long_term_transactions}")
        print(f"\nSchedule D Summary:")
        print(
            f"  Net Short-term Gain/Loss: ${summary.total_short_term_gain.amount:,.2f}"
        )
        print(f"  Net Long-term Gain/Loss: ${summary.total_long_term_gain.amount:,.2f}")
        print(f"  Combined (Line 16): ${summary.net_capital_gain.amount:,.2f}")

        if summary.wash_sale_adjustments.amount != 0:
            print(
                f"\n  Wash Sale Adjustments: ${summary.wash_sale_adjustments.amount:,.2f}"
            )

        return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_tax_summary(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        entity_id = UUID(args.entity_id)
    except ValueError:
        print(f"Error: Invalid entity ID: {args.entity_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        entity_repo = SQLiteEntityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)
        security_repo = SQLiteSecurityRepository(db)
        service = TaxDocumentService(
            entity_repo, position_repo, tax_lot_repo, security_repo
        )

        summary = service.get_tax_document_summary(
            entity_id=entity_id,
            tax_year=args.tax_year,
        )

        print(f"Tax Summary - {summary.entity_name} - {summary.tax_year}")
        print("=" * 50)
        print(f"\nShort-Term Capital Gains:")
        print(f"  Transactions: {summary.short_term_transactions}")
        print(f"  Proceeds: ${summary.total_short_term_proceeds.amount:,.2f}")
        print(f"  Cost Basis: ${summary.total_short_term_cost_basis.amount:,.2f}")
        print(f"  Gain/Loss: ${summary.total_short_term_gain.amount:,.2f}")

        print(f"\nLong-Term Capital Gains:")
        print(f"  Transactions: {summary.long_term_transactions}")
        print(f"  Proceeds: ${summary.total_long_term_proceeds.amount:,.2f}")
        print(f"  Cost Basis: ${summary.total_long_term_cost_basis.amount:,.2f}")
        print(f"  Gain/Loss: ${summary.total_long_term_gain.amount:,.2f}")

        print(f"\nNet Capital Gain/Loss: ${summary.net_capital_gain.amount:,.2f}")
        return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_tax_export(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        entity_id = UUID(args.entity_id)
    except ValueError:
        print(f"Error: Invalid entity ID: {args.entity_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        entity_repo = SQLiteEntityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)
        security_repo = SQLiteSecurityRepository(db)
        service = TaxDocumentService(
            entity_repo, position_repo, tax_lot_repo, security_repo
        )

        form_8949, _, _ = service.generate_from_entity(
            entity_id=entity_id,
            tax_year=args.tax_year,
        )

        output_path = args.output or f"form_8949_{args.tax_year}.csv"
        service.export_form_8949_csv(form_8949, output_path)
        print(f"Exported Form 8949 to {output_path}")
        return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_portfolio_allocation(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        entity_ids = None
        if args.entity_ids:
            entity_ids = [UUID(eid.strip()) for eid in args.entity_ids.split(",")]

        from datetime import date as dt_date

        as_of_date = dt_date.today()
        if args.as_of:
            as_of_date = dt_date.fromisoformat(args.as_of)

        db = SQLiteDatabase(str(db_path))
        entity_repo = SQLiteEntityRepository(db)
        position_repo = SQLitePositionRepository(db)
        security_repo = SQLiteSecurityRepository(db)
        service = PortfolioAnalyticsService(entity_repo, position_repo, security_repo)

        report = service.asset_allocation_report(entity_ids, as_of_date)

        print(f"Asset Allocation Report - {as_of_date}")
        print("=" * 70)
        print(
            f"\n{'Asset Class':<20} {'Market Value':>15} {'Allocation':>12} {'Positions':>10}"
        )
        print("-" * 60)

        for alloc in report.allocations:
            print(
                f"{alloc.asset_class.value:<20} ${alloc.market_value.amount:>14,.2f} "
                f"{alloc.allocation_percent:>10.2f}% {alloc.position_count:>10}"
            )

        print("-" * 60)
        print(
            f"{'Total':<20} ${report.total_market_value.amount:>14,.2f} {'100.00':>10}%"
        )
        print(f"\nUnrealized Gain/Loss: ${report.total_unrealized_gain.amount:,.2f}")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_portfolio_concentration(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        entity_ids = None
        if args.entity_ids:
            entity_ids = [UUID(eid.strip()) for eid in args.entity_ids.split(",")]

        from datetime import date as dt_date

        as_of_date = dt_date.today()
        if args.as_of:
            as_of_date = dt_date.fromisoformat(args.as_of)

        db = SQLiteDatabase(str(db_path))
        entity_repo = SQLiteEntityRepository(db)
        position_repo = SQLitePositionRepository(db)
        security_repo = SQLiteSecurityRepository(db)
        service = PortfolioAnalyticsService(entity_repo, position_repo, security_repo)

        report = service.concentration_report(entity_ids, as_of_date, top_n=args.top_n)

        print(f"Concentration Report - Top {args.top_n} Holdings")
        print("=" * 80)
        print(
            f"\n{'Symbol':<12} {'Name':<25} {'Market Value':>15} {'Concentration':>12}"
        )
        print("-" * 70)

        for h in report.holdings:
            print(
                f"{h.security_symbol:<12} {h.security_name[:23]:<25} "
                f"${h.market_value.amount:>14,.2f} {h.concentration_percent:>10.2f}%"
            )

        print("-" * 70)
        print(f"\nConcentration Metrics:")
        print(f"  Top 5 Holdings: {report.top_5_concentration:.2f}%")
        print(f"  Top 10 Holdings: {report.top_10_concentration:.2f}%")
        print(f"  Largest Single Holding: {report.largest_single_holding:.2f}%")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_portfolio_summary(args: argparse.Namespace) -> int:
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        entity_ids = None
        if args.entity_ids:
            entity_ids = [UUID(eid.strip()) for eid in args.entity_ids.split(",")]

        from datetime import date as dt_date

        as_of_date = dt_date.today()
        if args.as_of:
            as_of_date = dt_date.fromisoformat(args.as_of)

        db = SQLiteDatabase(str(db_path))
        entity_repo = SQLiteEntityRepository(db)
        position_repo = SQLitePositionRepository(db)
        security_repo = SQLiteSecurityRepository(db)
        service = PortfolioAnalyticsService(entity_repo, position_repo, security_repo)

        summary = service.get_portfolio_summary(entity_ids, as_of_date)

        print(f"Portfolio Summary - {as_of_date}")
        print("=" * 50)
        print(f"\nTotal Market Value: ${Decimal(summary['total_market_value']):,.2f}")
        print(f"Total Cost Basis: ${Decimal(summary['total_cost_basis']):,.2f}")
        print(
            f"Unrealized Gain/Loss: ${Decimal(summary['total_unrealized_gain']):,.2f}"
        )

        if summary["asset_allocation"]:
            print("\nAsset Allocation:")
            for alloc in summary["asset_allocation"]:
                print(f"  {alloc['asset_class']:<20} {alloc['allocation_percent']:>6}%")

        if summary["top_holdings"]:
            print("\nTop 5 Holdings:")
            for h in summary["top_holdings"]:
                print(f"  {h['symbol']:<12} {h['concentration_percent']:>6}%")

        metrics = summary["concentration_metrics"]
        print("\nConcentration Risk:")
        print(f"  Top 5: {metrics['top_5_concentration']}%")
        print(f"  Top 10: {metrics['top_10_concentration']}%")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_currency_rates_add(args: argparse.Namespace) -> int:
    """Add an exchange rate."""
    from datetime import datetime as dt

    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        db.initialize()
        repo = SQLiteExchangeRateRepository(db)
        service = CurrencyServiceImpl(repo)

        effective_date = dt.strptime(args.date, "%Y-%m-%d").date()
        rate = ExchangeRate(
            from_currency=args.from_currency.upper(),
            to_currency=args.to_currency.upper(),
            rate=Decimal(args.rate),
            effective_date=effective_date,
            source=ExchangeRateSource(args.source),
        )
        service.add_rate(rate)
        print(
            f"Added rate: {args.from_currency.upper()}/{args.to_currency.upper()} "
            f"= {args.rate} (effective {args.date})"
        )
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_currency_rates_list(args: argparse.Namespace) -> int:
    """List exchange rates."""
    from datetime import datetime as dt

    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        repo = SQLiteExchangeRateRepository(db)

        start = (
            dt.strptime(args.start_date, "%Y-%m-%d").date() if args.start_date else None
        )
        end = dt.strptime(args.end_date, "%Y-%m-%d").date() if args.end_date else None

        rates = list(
            repo.list_by_currency_pair(
                args.from_currency.upper(),
                args.to_currency.upper(),
                start_date=start,
                end_date=end,
            )
        )

        if not rates:
            print(
                f"No rates found for {args.from_currency.upper()}/{args.to_currency.upper()}"
            )
            return 0

        print(
            f"Exchange rates for {args.from_currency.upper()}/{args.to_currency.upper()}:"
        )
        print("-" * 50)
        for rate in rates:
            print(f"  {rate.effective_date}: {rate.rate} (source: {rate.source.value})")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_currency_rates_latest(args: argparse.Namespace) -> int:
    """Get latest exchange rate."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        repo = SQLiteExchangeRateRepository(db)
        service = CurrencyServiceImpl(repo)

        rate = service.get_latest_rate(
            args.from_currency.upper(), args.to_currency.upper()
        )
        if rate is None:
            print(
                f"No rate found for {args.from_currency.upper()}/{args.to_currency.upper()}"
            )
            return 1
        print(
            f"Latest {args.from_currency.upper()}/{args.to_currency.upper()}: {rate.rate}"
        )
        print(f"  Effective: {rate.effective_date}")
        print(f"  Source: {rate.source.value}")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_currency_convert(args: argparse.Namespace) -> int:
    """Convert amount between currencies."""
    from datetime import datetime as dt
    from family_office_ledger.domain.value_objects import Money

    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        repo = SQLiteExchangeRateRepository(db)
        service = CurrencyServiceImpl(repo)

        as_of_date = dt.strptime(args.date, "%Y-%m-%d").date()
        amount = Money(Decimal(args.amount), args.from_currency.upper())

        converted = service.convert(amount, args.to_currency.upper(), as_of_date)
        print(
            f"{args.amount} {args.from_currency.upper()} = {converted.amount} {args.to_currency.upper()}"
        )
        print(f"  As of: {as_of_date}")
        return 0

    except ExchangeRateNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_expense_categorize(args: argparse.Namespace) -> int:
    """Categorize a transaction with expense category and tags."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        txn_id = UUID(args.txn_id)
    except ValueError:
        print(f"Error: Invalid transaction ID: {args.txn_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        service = ExpenseServiceImpl(transaction_repo, account_repo, vendor_repo)

        tags = args.tags.split(",") if args.tags else None
        txn = service.categorize_transaction(txn_id, category=args.category, tags=tags)
        print(f"Transaction {txn_id} categorized")
        print(f"  Category: {txn.category or 'none'}")
        print(f"  Tags: {', '.join(txn.tags) if txn.tags else 'none'}")
        return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_expense_summary(args: argparse.Namespace) -> int:
    """Show expense summary for entity and date range."""
    from datetime import datetime as dt

    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        entity_ids = None
        if args.entity_id:
            entity_ids = [UUID(args.entity_id)]

        start_date = dt.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = dt.strptime(args.end_date, "%Y-%m-%d").date()

        db = SQLiteDatabase(str(db_path))
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        service = ExpenseServiceImpl(transaction_repo, account_repo, vendor_repo)

        summary = service.get_expense_summary(entity_ids, start_date, end_date)

        print("Expense Summary")
        print("=" * 50)
        print(f"  Date Range: {start_date} to {end_date}")
        print(f"  Total Expenses: ${summary['total_expenses']:,.2f}")
        print(f"  Transaction Count: {summary['transaction_count']}")
        return 0

    except ValueError as e:
        print(f"Error: Invalid input: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_expense_by_category(args: argparse.Namespace) -> int:
    """Show expenses grouped by category."""
    from datetime import datetime as dt

    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        entity_ids = None
        if args.entity_id:
            entity_ids = [UUID(args.entity_id)]

        start_date = dt.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = dt.strptime(args.end_date, "%Y-%m-%d").date()

        db = SQLiteDatabase(str(db_path))
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        service = ExpenseServiceImpl(transaction_repo, account_repo, vendor_repo)

        by_category = service.get_expenses_by_category(entity_ids, start_date, end_date)

        print("Expenses by Category")
        print("=" * 50)
        print(f"  Date Range: {start_date} to {end_date}")
        print(f"\n{'Category':<25} {'Amount':>15}")
        print("-" * 42)

        total = Decimal("0")
        for category, money in sorted(by_category.items()):
            print(f"{category:<25} ${money.amount:>14,.2f}")
            total += money.amount

        print("-" * 42)
        print(f"{'Total':<25} ${total:>14,.2f}")
        return 0

    except ValueError as e:
        print(f"Error: Invalid input: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_expense_by_vendor(args: argparse.Namespace) -> int:
    """Show expenses grouped by vendor."""
    from datetime import datetime as dt

    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        entity_ids = None
        if args.entity_id:
            entity_ids = [UUID(args.entity_id)]

        start_date = dt.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = dt.strptime(args.end_date, "%Y-%m-%d").date()

        db = SQLiteDatabase(str(db_path))
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        service = ExpenseServiceImpl(transaction_repo, account_repo, vendor_repo)

        by_vendor = service.get_expenses_by_vendor(entity_ids, start_date, end_date)

        print("Expenses by Vendor")
        print("=" * 70)
        print(f"  Date Range: {start_date} to {end_date}")
        print(f"\n{'Vendor ID':<40} {'Amount':>15}")
        print("-" * 57)

        total = Decimal("0")
        for vendor_id, money in by_vendor.items():
            vendor = vendor_repo.get(vendor_id)
            name = vendor.name if vendor else str(vendor_id)[:20]
            print(f"{name:<40} ${money.amount:>14,.2f}")
            total += money.amount

        print("-" * 57)
        print(f"{'Total':<40} ${total:>14,.2f}")
        return 0

    except ValueError as e:
        print(f"Error: Invalid input: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_expense_recurring(args: argparse.Namespace) -> int:
    """Detect recurring expenses for an entity."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        entity_id = UUID(args.entity_id)
    except ValueError:
        print(f"Error: Invalid entity ID: {args.entity_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        service = ExpenseServiceImpl(transaction_repo, account_repo, vendor_repo)

        lookback = args.lookback_months if args.lookback_months else 3
        recurring = service.detect_recurring_expenses(entity_id, lookback)

        print("Recurring Expenses")
        print("=" * 80)
        print(f"  Lookback: {lookback} months")
        print(
            f"\n{'Vendor':<30} {'Frequency':<12} {'Avg Amount':>12} {'Occurrences':>12}"
        )
        print("-" * 70)

        for item in recurring:
            vendor = vendor_repo.get(item["vendor_id"])
            name = vendor.name[:28] if vendor else str(item["vendor_id"])[:28]
            print(
                f"{name:<30} {item['frequency']:<12} "
                f"${item['amount'].amount:>11,.2f} {item['occurrence_count']:>12}"
            )

        if not recurring:
            print("  No recurring expenses detected")

        return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_vendor_add(args: argparse.Namespace) -> int:
    """Add a new vendor."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        vendor_repo = SQLiteVendorRepository(db)

        vendor = Vendor(
            name=args.name,
            category=args.category,
            tax_id=args.tax_id,
            is_1099_eligible=args.is_1099,
        )
        vendor_repo.add(vendor)

        print(f"Vendor created: {vendor.id}")
        print(f"  Name: {vendor.name}")
        if vendor.category:
            print(f"  Category: {vendor.category}")
        if vendor.tax_id:
            print(f"  Tax ID: {vendor.tax_id}")
        if vendor.is_1099_eligible:
            print(f"  1099 Eligible: Yes")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_vendor_list(args: argparse.Namespace) -> int:
    """List vendors."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        vendor_repo = SQLiteVendorRepository(db)

        if args.category:
            vendors = list(vendor_repo.list_by_category(args.category))
        else:
            vendors = list(vendor_repo.list_all(include_inactive=args.include_inactive))

        print(f"{'ID':<40} {'Name':<30} {'Category':<15} {'1099':>5}")
        print("-" * 95)

        for vendor in vendors:
            cat = vendor.category or "-"
            is_1099 = "Yes" if vendor.is_1099_eligible else "No"
            status = "" if vendor.is_active else " [inactive]"
            print(
                f"{str(vendor.id):<40} {vendor.name[:28]:<30} {cat:<15} {is_1099:>5}{status}"
            )

        print(f"\nTotal: {len(vendors)} vendor(s)")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_vendor_get(args: argparse.Namespace) -> int:
    """Get vendor details."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        vendor_id = UUID(args.id)
    except ValueError:
        print(f"Error: Invalid vendor ID: {args.id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        vendor_repo = SQLiteVendorRepository(db)

        vendor = vendor_repo.get(vendor_id)
        if vendor is None:
            print("Error: Vendor not found")
            return 1

        print("Vendor Details")
        print("=" * 50)
        print(f"  ID: {vendor.id}")
        print(f"  Name: {vendor.name}")
        print(f"  Category: {vendor.category or 'N/A'}")
        print(f"  Tax ID: {vendor.tax_id or 'N/A'}")
        print(f"  1099 Eligible: {'Yes' if vendor.is_1099_eligible else 'No'}")
        print(f"  Status: {'Active' if vendor.is_active else 'Inactive'}")
        print(f"  Created: {vendor.created_at}")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_vendor_update(args: argparse.Namespace) -> int:
    """Update vendor details."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        vendor_id = UUID(args.id)
    except ValueError:
        print(f"Error: Invalid vendor ID: {args.id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        vendor_repo = SQLiteVendorRepository(db)

        vendor = vendor_repo.get(vendor_id)
        if vendor is None:
            print("Error: Vendor not found")
            return 1

        if args.name:
            vendor.name = args.name
        if args.category:
            vendor.category = args.category
        if args.deactivate:
            vendor.deactivate()

        vendor_repo.update(vendor)
        print(f"Vendor {vendor_id} updated")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_vendor_search(args: argparse.Namespace) -> int:
    """Search vendors by name."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        vendor_repo = SQLiteVendorRepository(db)

        vendors = list(vendor_repo.search_by_name(args.name))

        print(f"{'ID':<40} {'Name':<30} {'Category':<15} {'1099':>5}")
        print("-" * 95)

        for vendor in vendors:
            cat = vendor.category or "-"
            is_1099 = "Yes" if vendor.is_1099_eligible else "No"
            print(f"{str(vendor.id):<40} {vendor.name[:28]:<30} {cat:<15} {is_1099:>5}")

        print(f"\nFound: {len(vendors)} vendor(s)")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fol",
        description="Family Office Ledger - Multi-entity accounting and investment tracking",
    )
    parser.add_argument(
        "--database",
        "-d",
        help="Path to SQLite database file",
        default=None,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize a new database")
    init_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force reinitialization (deletes existing data)",
    )
    init_parser.set_defaults(func=cmd_init)

    # status command
    status_parser = subparsers.add_parser("status", help="Show database status")
    status_parser.set_defaults(func=cmd_status)

    # version command
    version_parser = subparsers.add_parser("version", help="Show version")
    version_parser.set_defaults(func=cmd_version)

    # ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest bank transaction file")
    ingest_parser.add_argument(
        "file",
        help="Bank transaction file to ingest",
    )
    ingest_parser.add_argument(
        "--default-entity",
        "-e",
        help="Default entity for unrecognized accounts",
        default=None,
    )
    ingest_parser.set_defaults(func=cmd_ingest)

    # ui command
    ui_parser = subparsers.add_parser("ui", help="Launch the Streamlit web interface")
    ui_parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port to run frontend (default: 3000)",
    )
    ui_parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend API base URL (default: http://localhost:8000)",
    )
    ui_parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable hot reload",
    )
    ui_parser.set_defaults(func=cmd_ui)

    # reconcile command group
    reconcile_parser = subparsers.add_parser(
        "reconcile", help="Reconciliation commands"
    )
    reconcile_subparsers = reconcile_parser.add_subparsers(
        dest="reconcile_command", help="Reconciliation subcommands"
    )

    # reconcile create
    reconcile_create_parser = reconcile_subparsers.add_parser(
        "create", help="Create a reconciliation session"
    )
    reconcile_create_parser.add_argument(
        "--account-id", required=True, help="Account ID to reconcile"
    )
    reconcile_create_parser.add_argument(
        "--file", required=True, help="Transaction file to import"
    )
    reconcile_create_parser.add_argument(
        "--format", choices=["csv", "ofx"], default="csv", help="File format"
    )
    reconcile_create_parser.set_defaults(func=cmd_reconcile_create)

    # reconcile list
    reconcile_list_parser = reconcile_subparsers.add_parser(
        "list", help="List matches in a session"
    )
    reconcile_list_parser.add_argument("--session-id", required=True, help="Session ID")
    reconcile_list_parser.add_argument(
        "--status",
        choices=["pending", "confirmed", "rejected", "skipped"],
        help="Filter by status",
    )
    reconcile_list_parser.add_argument(
        "--limit", type=int, default=50, help="Max matches to return"
    )
    reconcile_list_parser.add_argument(
        "--offset", type=int, default=0, help="Offset for pagination"
    )
    reconcile_list_parser.set_defaults(func=cmd_reconcile_list)

    # reconcile confirm
    reconcile_confirm_parser = reconcile_subparsers.add_parser(
        "confirm", help="Confirm a match"
    )
    reconcile_confirm_parser.add_argument(
        "--session-id", required=True, help="Session ID"
    )
    reconcile_confirm_parser.add_argument(
        "--match-id", required=True, help="Match ID to confirm"
    )
    reconcile_confirm_parser.set_defaults(func=cmd_reconcile_confirm)

    # reconcile reject
    reconcile_reject_parser = reconcile_subparsers.add_parser(
        "reject", help="Reject a match"
    )
    reconcile_reject_parser.add_argument(
        "--session-id", required=True, help="Session ID"
    )
    reconcile_reject_parser.add_argument(
        "--match-id", required=True, help="Match ID to reject"
    )
    reconcile_reject_parser.set_defaults(func=cmd_reconcile_reject)

    # reconcile skip
    reconcile_skip_parser = reconcile_subparsers.add_parser("skip", help="Skip a match")
    reconcile_skip_parser.add_argument("--session-id", required=True, help="Session ID")
    reconcile_skip_parser.add_argument(
        "--match-id", required=True, help="Match ID to skip"
    )
    reconcile_skip_parser.set_defaults(func=cmd_reconcile_skip)

    # reconcile close
    reconcile_close_parser = reconcile_subparsers.add_parser(
        "close", help="Close a session"
    )
    reconcile_close_parser.add_argument(
        "--session-id", required=True, help="Session ID to close"
    )
    reconcile_close_parser.set_defaults(func=cmd_reconcile_close)

    # reconcile summary
    reconcile_summary_parser = reconcile_subparsers.add_parser(
        "summary", help="Show session summary"
    )
    reconcile_summary_parser.add_argument(
        "--session-id", required=True, help="Session ID"
    )
    reconcile_summary_parser.set_defaults(func=cmd_reconcile_summary)

    # transfer command group
    transfer_parser = subparsers.add_parser(
        "transfer", help="Transfer matching commands"
    )
    transfer_subparsers = transfer_parser.add_subparsers(
        dest="transfer_command", help="Transfer matching subcommands"
    )

    # transfer create
    transfer_create_parser = transfer_subparsers.add_parser(
        "create", help="Create a transfer matching session"
    )
    transfer_create_parser.add_argument(
        "--entity-ids", help="Comma-separated entity IDs (optional)"
    )
    transfer_create_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    transfer_create_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    transfer_create_parser.add_argument(
        "--tolerance", type=int, default=3, help="Date tolerance in days (default: 3)"
    )
    transfer_create_parser.set_defaults(func=cmd_transfer_create)

    # transfer list
    transfer_list_parser = transfer_subparsers.add_parser(
        "list", help="List matches in a session"
    )
    transfer_list_parser.add_argument("--session-id", required=True, help="Session ID")
    transfer_list_parser.add_argument(
        "--status",
        choices=["pending", "confirmed", "rejected"],
        help="Filter by status",
    )
    transfer_list_parser.set_defaults(func=cmd_transfer_list)

    # transfer confirm
    transfer_confirm_parser = transfer_subparsers.add_parser(
        "confirm", help="Confirm a match"
    )
    transfer_confirm_parser.add_argument(
        "--session-id", required=True, help="Session ID"
    )
    transfer_confirm_parser.add_argument(
        "--match-id", required=True, help="Match ID to confirm"
    )
    transfer_confirm_parser.set_defaults(func=cmd_transfer_confirm)

    # transfer reject
    transfer_reject_parser = transfer_subparsers.add_parser(
        "reject", help="Reject a match"
    )
    transfer_reject_parser.add_argument(
        "--session-id", required=True, help="Session ID"
    )
    transfer_reject_parser.add_argument(
        "--match-id", required=True, help="Match ID to reject"
    )
    transfer_reject_parser.set_defaults(func=cmd_transfer_reject)

    # transfer close
    transfer_close_parser = transfer_subparsers.add_parser(
        "close", help="Close a session"
    )
    transfer_close_parser.add_argument(
        "--session-id", required=True, help="Session ID to close"
    )
    transfer_close_parser.set_defaults(func=cmd_transfer_close)

    # transfer summary
    transfer_summary_parser = transfer_subparsers.add_parser(
        "summary", help="Show session summary"
    )
    transfer_summary_parser.add_argument(
        "--session-id", required=True, help="Session ID"
    )
    transfer_summary_parser.set_defaults(func=cmd_transfer_summary)

    # qsbs command group
    qsbs_parser = subparsers.add_parser("qsbs", help="QSBS tracking commands")
    qsbs_subparsers = qsbs_parser.add_subparsers(
        dest="qsbs_command", help="QSBS subcommands"
    )

    # qsbs list
    qsbs_list_parser = qsbs_subparsers.add_parser(
        "list", help="List QSBS-eligible securities"
    )
    qsbs_list_parser.set_defaults(func=cmd_qsbs_list)

    # qsbs mark
    qsbs_mark_parser = qsbs_subparsers.add_parser(
        "mark", help="Mark a security as QSBS-eligible"
    )
    qsbs_mark_parser.add_argument(
        "--security-id", required=True, help="Security ID to mark"
    )
    qsbs_mark_parser.add_argument(
        "--qualification-date",
        required=True,
        help="QSBS qualification date (YYYY-MM-DD)",
    )
    qsbs_mark_parser.set_defaults(func=cmd_qsbs_mark)

    # qsbs remove
    qsbs_remove_parser = qsbs_subparsers.add_parser(
        "remove", help="Remove QSBS eligibility from a security"
    )
    qsbs_remove_parser.add_argument("--security-id", required=True, help="Security ID")
    qsbs_remove_parser.set_defaults(func=cmd_qsbs_remove)

    # qsbs summary
    qsbs_summary_parser = qsbs_subparsers.add_parser(
        "summary", help="Show QSBS holdings summary"
    )
    qsbs_summary_parser.add_argument("--as-of", help="As-of date (YYYY-MM-DD)")
    qsbs_summary_parser.set_defaults(func=cmd_qsbs_summary)

    # tax command group
    tax_parser = subparsers.add_parser("tax", help="Tax document generation commands")
    tax_subparsers = tax_parser.add_subparsers(
        dest="tax_command", help="Tax document subcommands"
    )

    # tax generate
    tax_generate_parser = tax_subparsers.add_parser(
        "generate", help="Generate tax documents for an entity"
    )
    tax_generate_parser.add_argument(
        "--entity-id", required=True, help="Entity ID to generate documents for"
    )
    tax_generate_parser.add_argument(
        "--tax-year", type=int, required=True, help="Tax year (e.g., 2024)"
    )
    tax_generate_parser.set_defaults(func=cmd_tax_generate)

    # tax summary
    tax_summary_parser = tax_subparsers.add_parser(
        "summary", help="Show tax summary for an entity"
    )
    tax_summary_parser.add_argument("--entity-id", required=True, help="Entity ID")
    tax_summary_parser.add_argument(
        "--tax-year", type=int, required=True, help="Tax year (e.g., 2024)"
    )
    tax_summary_parser.set_defaults(func=cmd_tax_summary)

    # tax export
    tax_export_parser = tax_subparsers.add_parser(
        "export", help="Export Form 8949 to CSV"
    )
    tax_export_parser.add_argument("--entity-id", required=True, help="Entity ID")
    tax_export_parser.add_argument(
        "--tax-year", type=int, required=True, help="Tax year (e.g., 2024)"
    )
    tax_export_parser.add_argument(
        "--output", "-o", help="Output file path (default: form_8949_<year>.csv)"
    )
    tax_export_parser.set_defaults(func=cmd_tax_export)

    # portfolio command group
    portfolio_parser = subparsers.add_parser(
        "portfolio", help="Portfolio analytics commands"
    )
    portfolio_subparsers = portfolio_parser.add_subparsers(
        dest="portfolio_command", help="Portfolio analytics subcommands"
    )

    # portfolio allocation
    portfolio_allocation_parser = portfolio_subparsers.add_parser(
        "allocation", help="Show asset allocation breakdown"
    )
    portfolio_allocation_parser.add_argument(
        "--entity-ids", help="Comma-separated entity IDs (optional)"
    )
    portfolio_allocation_parser.add_argument("--as-of", help="As-of date (YYYY-MM-DD)")
    portfolio_allocation_parser.set_defaults(func=cmd_portfolio_allocation)

    # portfolio concentration
    portfolio_concentration_parser = portfolio_subparsers.add_parser(
        "concentration", help="Show top holdings concentration"
    )
    portfolio_concentration_parser.add_argument(
        "--entity-ids", help="Comma-separated entity IDs (optional)"
    )
    portfolio_concentration_parser.add_argument(
        "--as-of", help="As-of date (YYYY-MM-DD)"
    )
    portfolio_concentration_parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Number of top holdings to show (default: 20)",
    )
    portfolio_concentration_parser.set_defaults(func=cmd_portfolio_concentration)

    # portfolio summary
    portfolio_summary_parser = portfolio_subparsers.add_parser(
        "summary", help="Show portfolio summary"
    )
    portfolio_summary_parser.add_argument(
        "--entity-ids", help="Comma-separated entity IDs (optional)"
    )
    portfolio_summary_parser.add_argument("--as-of", help="As-of date (YYYY-MM-DD)")
    portfolio_summary_parser.set_defaults(func=cmd_portfolio_summary)

    # currency command group
    currency_parser = subparsers.add_parser(
        "currency", help="Currency and exchange rate management"
    )
    currency_subparsers = currency_parser.add_subparsers(
        dest="currency_command", help="Currency subcommands"
    )

    # currency rates-add
    rates_add_parser = currency_subparsers.add_parser(
        "rates-add", help="Add an exchange rate"
    )
    rates_add_parser.add_argument(
        "--from",
        dest="from_currency",
        required=True,
        help="Source currency (e.g., USD)",
    )
    rates_add_parser.add_argument(
        "--to", dest="to_currency", required=True, help="Target currency (e.g., EUR)"
    )
    rates_add_parser.add_argument(
        "--rate", required=True, help="Exchange rate (e.g., 0.92)"
    )
    rates_add_parser.add_argument(
        "--date", required=True, help="Effective date (YYYY-MM-DD)"
    )
    rates_add_parser.add_argument(
        "--source", default="manual", help="Rate source (default: manual)"
    )
    rates_add_parser.set_defaults(func=cmd_currency_rates_add)

    # currency rates-list
    rates_list_parser = currency_subparsers.add_parser(
        "rates-list", help="List exchange rates"
    )
    rates_list_parser.add_argument(
        "--from", dest="from_currency", required=True, help="Source currency"
    )
    rates_list_parser.add_argument(
        "--to", dest="to_currency", required=True, help="Target currency"
    )
    rates_list_parser.add_argument(
        "--start-date", help="Start date filter (YYYY-MM-DD)"
    )
    rates_list_parser.add_argument("--end-date", help="End date filter (YYYY-MM-DD)")
    rates_list_parser.set_defaults(func=cmd_currency_rates_list)

    # currency rates-latest
    rates_latest_parser = currency_subparsers.add_parser(
        "rates-latest", help="Get latest exchange rate"
    )
    rates_latest_parser.add_argument(
        "--from", dest="from_currency", required=True, help="Source currency"
    )
    rates_latest_parser.add_argument(
        "--to", dest="to_currency", required=True, help="Target currency"
    )
    rates_latest_parser.set_defaults(func=cmd_currency_rates_latest)

    # currency convert
    convert_parser = currency_subparsers.add_parser(
        "convert", help="Convert an amount between currencies"
    )
    convert_parser.add_argument("--amount", required=True, help="Amount to convert")
    convert_parser.add_argument(
        "--from", dest="from_currency", required=True, help="Source currency"
    )
    convert_parser.add_argument(
        "--to", dest="to_currency", required=True, help="Target currency"
    )
    convert_parser.add_argument(
        "--date", required=True, help="Conversion date (YYYY-MM-DD)"
    )
    convert_parser.set_defaults(func=cmd_currency_convert)

    # expense command group
    expense_parser = subparsers.add_parser(
        "expense", help="Expense management commands"
    )
    expense_subparsers = expense_parser.add_subparsers(
        dest="expense_command", help="Expense subcommands"
    )

    # expense categorize
    expense_categorize_parser = expense_subparsers.add_parser(
        "categorize", help="Categorize a transaction"
    )
    expense_categorize_parser.add_argument(
        "--txn-id", required=True, help="Transaction ID to categorize"
    )
    expense_categorize_parser.add_argument("--category", help="Expense category")
    expense_categorize_parser.add_argument(
        "--tags", help="Comma-separated tags (e.g., 'tax,q1')"
    )
    expense_categorize_parser.set_defaults(func=cmd_expense_categorize)

    # expense summary
    expense_summary_parser = expense_subparsers.add_parser(
        "summary", help="Show expense summary"
    )
    expense_summary_parser.add_argument("--entity-id", help="Entity ID (optional)")
    expense_summary_parser.add_argument(
        "--start-date", required=True, help="Start date (YYYY-MM-DD)"
    )
    expense_summary_parser.add_argument(
        "--end-date", required=True, help="End date (YYYY-MM-DD)"
    )
    expense_summary_parser.set_defaults(func=cmd_expense_summary)

    # expense by-category
    expense_by_category_parser = expense_subparsers.add_parser(
        "by-category", help="Show expenses grouped by category"
    )
    expense_by_category_parser.add_argument("--entity-id", help="Entity ID (optional)")
    expense_by_category_parser.add_argument(
        "--start-date", required=True, help="Start date (YYYY-MM-DD)"
    )
    expense_by_category_parser.add_argument(
        "--end-date", required=True, help="End date (YYYY-MM-DD)"
    )
    expense_by_category_parser.set_defaults(func=cmd_expense_by_category)

    # expense by-vendor
    expense_by_vendor_parser = expense_subparsers.add_parser(
        "by-vendor", help="Show expenses grouped by vendor"
    )
    expense_by_vendor_parser.add_argument("--entity-id", help="Entity ID (optional)")
    expense_by_vendor_parser.add_argument(
        "--start-date", required=True, help="Start date (YYYY-MM-DD)"
    )
    expense_by_vendor_parser.add_argument(
        "--end-date", required=True, help="End date (YYYY-MM-DD)"
    )
    expense_by_vendor_parser.set_defaults(func=cmd_expense_by_vendor)

    # expense recurring
    expense_recurring_parser = expense_subparsers.add_parser(
        "recurring", help="Detect recurring expenses"
    )
    expense_recurring_parser.add_argument(
        "--entity-id", required=True, help="Entity ID"
    )
    expense_recurring_parser.add_argument(
        "--lookback-months", type=int, default=3, help="Lookback period in months"
    )
    expense_recurring_parser.set_defaults(func=cmd_expense_recurring)

    # vendor command group
    vendor_parser = subparsers.add_parser("vendor", help="Vendor management commands")
    vendor_subparsers = vendor_parser.add_subparsers(
        dest="vendor_command", help="Vendor subcommands"
    )

    # vendor add
    vendor_add_parser = vendor_subparsers.add_parser("add", help="Add a new vendor")
    vendor_add_parser.add_argument("--name", required=True, help="Vendor name")
    vendor_add_parser.add_argument("--category", help="Vendor category")
    vendor_add_parser.add_argument("--tax-id", help="Tax ID (e.g., '12-3456789')")
    vendor_add_parser.add_argument(
        "--1099", dest="is_1099", action="store_true", help="Mark as 1099-eligible"
    )
    vendor_add_parser.set_defaults(func=cmd_vendor_add)

    # vendor list
    vendor_list_parser = vendor_subparsers.add_parser("list", help="List vendors")
    vendor_list_parser.add_argument(
        "--include-inactive", action="store_true", help="Include inactive vendors"
    )
    vendor_list_parser.add_argument("--category", help="Filter by category")
    vendor_list_parser.set_defaults(func=cmd_vendor_list)

    # vendor get
    vendor_get_parser = vendor_subparsers.add_parser("get", help="Get vendor details")
    vendor_get_parser.add_argument("--id", required=True, help="Vendor ID")
    vendor_get_parser.set_defaults(func=cmd_vendor_get)

    # vendor update
    vendor_update_parser = vendor_subparsers.add_parser(
        "update", help="Update vendor details"
    )
    vendor_update_parser.add_argument("--id", required=True, help="Vendor ID")
    vendor_update_parser.add_argument("--name", help="New name")
    vendor_update_parser.add_argument("--category", help="New category")
    vendor_update_parser.add_argument(
        "--deactivate", action="store_true", help="Deactivate the vendor"
    )
    vendor_update_parser.set_defaults(func=cmd_vendor_update)

    # vendor search
    vendor_search_parser = vendor_subparsers.add_parser(
        "search", help="Search vendors by name"
    )
    vendor_search_parser.add_argument("--name", required=True, help="Name pattern")
    vendor_search_parser.set_defaults(func=cmd_vendor_search)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "reconcile" and (
        not hasattr(args, "reconcile_command") or args.reconcile_command is None
    ):
        reconcile_parser.print_help()
        return 0

    if args.command == "transfer" and (
        not hasattr(args, "transfer_command") or args.transfer_command is None
    ):
        transfer_parser.print_help()
        return 0

    if args.command == "qsbs" and (
        not hasattr(args, "qsbs_command") or args.qsbs_command is None
    ):
        qsbs_parser.print_help()
        return 0

    if args.command == "tax" and (
        not hasattr(args, "tax_command") or args.tax_command is None
    ):
        tax_parser.print_help()
        return 0

    if args.command == "portfolio" and (
        not hasattr(args, "portfolio_command") or args.portfolio_command is None
    ):
        portfolio_parser.print_help()
        return 0

    if args.command == "currency" and (
        not hasattr(args, "currency_command") or args.currency_command is None
    ):
        currency_parser.print_help()
        return 0

    if args.command == "expense" and (
        not hasattr(args, "expense_command") or args.expense_command is None
    ):
        expense_parser.print_help()
        return 0

    if args.command == "vendor" and (
        not hasattr(args, "vendor_command") or args.vendor_command is None
    ):
        vendor_parser.print_help()
        return 0

    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
