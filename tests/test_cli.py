"""Tests for CLI module."""

from pathlib import Path

from family_office_ledger.cli import (
    cmd_init,
    cmd_status,
    cmd_version,
    create_app,
    get_default_db_path,
    main,
)
from family_office_ledger.domain.entities import Entity
from family_office_ledger.domain.value_objects import AccountType, EntityType
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
)


class TestGetDefaultDbPath:
    def test_returns_path_in_home_directory(self):
        result = get_default_db_path()

        assert isinstance(result, Path)
        assert ".family_office_ledger" in str(result)
        assert result.name == "ledger.db"


class TestCreateApp:
    def test_creates_database_and_service(self, tmp_path):
        db_path = tmp_path / "test.db"

        db, ledger_service = create_app(db_path)

        assert db is not None
        assert ledger_service is not None
        assert db_path.exists()

    def test_creates_parent_directories(self, tmp_path):
        db_path = tmp_path / "nested" / "dirs" / "test.db"

        db, ledger_service = create_app(db_path)

        assert db_path.exists()


class TestCmdInit:
    def test_creates_new_database(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"

        class Args:
            database = str(db_path)
            force = False

        result = cmd_init(Args())

        assert result == 0
        assert db_path.exists()
        captured = capsys.readouterr()
        assert "Initialized database" in captured.out

    def test_refuses_to_overwrite_existing_without_force(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db_path.touch()

        class Args:
            database = str(db_path)
            force = False

        result = cmd_init(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "already exists" in captured.out

    def test_overwrites_existing_with_force(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db_path.write_text("old data")

        class Args:
            database = str(db_path)
            force = True

        result = cmd_init(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "Initialized database" in captured.out


class TestCmdStatus:
    def test_reports_no_database(self, tmp_path, capsys):
        db_path = tmp_path / "nonexistent.db"

        class Args:
            database = str(db_path)

        result = cmd_status(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "No database found" in captured.out

    def test_reports_empty_database(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        class Args:
            database = str(db_path)

        result = cmd_status(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "Entities: 0" in captured.out

    def test_reports_entities_and_accounts(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        account_repo = SQLiteAccountRepository(db)

        entity = Entity(name="Test LLC", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        from family_office_ledger.domain.entities import Account

        account = Account(
            name="Checking",
            entity_id=entity.id,
            account_type=AccountType.ASSET,
        )
        account_repo.add(account)

        class Args:
            database = str(db_path)

        result = cmd_status(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "Entities: 1" in captured.out
        assert "Test LLC" in captured.out
        assert "1 accounts" in captured.out


class TestCmdVersion:
    def test_prints_version(self, capsys):
        class Args:
            pass

        result = cmd_version(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "v0.1.0" in captured.out


class TestMain:
    def test_no_command_prints_help(self, capsys):
        result = main([])

        assert result == 0
        captured = capsys.readouterr()
        assert (
            "usage:" in captured.out.lower() or "Family Office Ledger" in captured.out
        )

    def test_version_command(self, capsys):
        result = main(["version"])

        assert result == 0
        captured = capsys.readouterr()
        assert "v0.1.0" in captured.out

    def test_init_command(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"

        result = main(["--database", str(db_path), "init"])

        assert result == 0
        assert db_path.exists()

    def test_status_command_no_db(self, tmp_path, capsys):
        db_path = tmp_path / "nonexistent.db"

        result = main(["--database", str(db_path), "status"])

        assert result == 1

    def test_init_then_status(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"

        main(["--database", str(db_path), "init"])
        result = main(["--database", str(db_path), "status"])

        assert result == 0
        captured = capsys.readouterr()
        assert "Entities: 0" in captured.out

    def test_init_force_flag(self, tmp_path):
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = main(["--database", str(db_path), "init", "--force"])

        assert result == 0
