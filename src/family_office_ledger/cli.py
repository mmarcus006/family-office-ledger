"""Command-line interface for Family Office Ledger."""

import argparse
import sys
from pathlib import Path

from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLitePositionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.ingestion import IngestionService
from family_office_ledger.services.ledger import LedgerServiceImpl
from family_office_ledger.services.lot_matching import LotMatchingServiceImpl
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

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
