"""Reconciliation CLI commands for Family Office Ledger."""

import argparse
from pathlib import Path
from uuid import UUID

from family_office_ledger.cli._main import get_default_db_path
from family_office_ledger.domain.reconciliation import ReconciliationMatchStatus
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteReconciliationSessionRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.reconciliation import (
    MatchNotFoundError,
    ReconciliationServiceImpl,
    SessionExistsError,
    SessionNotFoundError,
)


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


__all__ = [
    "cmd_reconcile_create",
    "cmd_reconcile_list",
    "cmd_reconcile_confirm",
    "cmd_reconcile_reject",
    "cmd_reconcile_skip",
    "cmd_reconcile_close",
    "cmd_reconcile_summary",
]
