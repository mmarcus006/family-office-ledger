"""Command-line interface for Family Office Ledger."""

import argparse
import sys
from pathlib import Path
from uuid import UUID

from family_office_ledger.domain.reconciliation import ReconciliationMatchStatus
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLitePositionRepository,
    SQLiteReconciliationSessionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
    SQLiteTransactionRepository,
)
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
    """Launch the NiceGUI web interface."""
    try:
        from family_office_ledger.ui.main import run
    except ImportError:
        print("Frontend dependencies are not installed.")
        print("Install with: uv sync --dev --extra frontend")
        return 1

    port = int(args.port)
    api_url = str(args.api_url)
    reload = not bool(args.no_reload)

    run(port=port, api_url=api_url, reload=reload)
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


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
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
    ui_parser = subparsers.add_parser("ui", help="Launch the NiceGUI web interface")
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

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "reconcile" and (
        not hasattr(args, "reconcile_command") or args.reconcile_command is None
    ):
        reconcile_parser.print_help()
        return 0

    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
