"""TDD Tests for CLI module structure refactoring.

These tests verify that the CLI has been properly split into domain-specific submodules.
Following TDD methodology: write tests first, then implement.
"""

import pytest


class TestCLIPackageStructure:
    """Test that CLI is properly packaged with submodules."""

    def test_cli_package_exists(self) -> None:
        """Test that cli package can be imported."""
        from family_office_ledger import cli

        assert cli is not None

    def test_cli_main_function_exists(self) -> None:
        """Test that main() is accessible from cli package."""
        from family_office_ledger.cli import main

        assert callable(main)


class TestCLISubmoduleImports:
    """Test that all CLI submodules can be imported from the new locations."""

    def test_reconciliation_commands_import(self) -> None:
        """Test reconciliation commands can be imported from submodule."""
        from family_office_ledger.cli.reconciliation_commands import (
            cmd_reconcile_close,
            cmd_reconcile_confirm,
            cmd_reconcile_create,
            cmd_reconcile_list,
            cmd_reconcile_reject,
            cmd_reconcile_skip,
            cmd_reconcile_summary,
        )

        assert callable(cmd_reconcile_create)
        assert callable(cmd_reconcile_list)
        assert callable(cmd_reconcile_confirm)
        assert callable(cmd_reconcile_reject)
        assert callable(cmd_reconcile_skip)
        assert callable(cmd_reconcile_close)
        assert callable(cmd_reconcile_summary)

    def test_currency_commands_import(self) -> None:
        """Test currency commands can be imported from submodule."""
        from family_office_ledger.cli.currency_commands import (
            cmd_currency_convert,
            cmd_currency_rates_add,
            cmd_currency_rates_latest,
            cmd_currency_rates_list,
        )

        assert callable(cmd_currency_rates_add)
        assert callable(cmd_currency_rates_list)
        assert callable(cmd_currency_rates_latest)
        assert callable(cmd_currency_convert)

    def test_budget_commands_import(self) -> None:
        """Test budget commands can be imported from submodule."""
        from family_office_ledger.cli.budget_commands import (
            cmd_budget_add_line,
            cmd_budget_alerts,
            cmd_budget_create,
            cmd_budget_list,
            cmd_budget_variance,
        )

        assert callable(cmd_budget_create)
        assert callable(cmd_budget_list)
        assert callable(cmd_budget_add_line)
        assert callable(cmd_budget_variance)
        assert callable(cmd_budget_alerts)

    def test_qsbs_commands_import(self) -> None:
        """Test QSBS commands can be imported from submodule."""
        from family_office_ledger.cli.qsbs_commands import (
            cmd_qsbs_list,
            cmd_qsbs_mark,
            cmd_qsbs_summary,
        )

        assert callable(cmd_qsbs_mark)
        assert callable(cmd_qsbs_list)
        assert callable(cmd_qsbs_summary)

    def test_household_commands_import(self) -> None:
        """Test household commands can be imported from submodule."""
        from family_office_ledger.cli.household_commands import (
            cmd_household_add_member,
            cmd_household_create,
            cmd_household_list,
            cmd_household_members,
            cmd_household_net_worth,
        )

        assert callable(cmd_household_list)
        assert callable(cmd_household_create)
        assert callable(cmd_household_add_member)
        assert callable(cmd_household_members)
        assert callable(cmd_household_net_worth)


class TestBackwardCompatibility:
    """Test that old import paths still work for backward compatibility."""

    def test_main_accessible_from_original_path(self) -> None:
        """Ensure main() is still accessible from family_office_ledger.cli."""
        from family_office_ledger.cli import main

        assert callable(main)

    def test_create_app_accessible_from_original_path(self) -> None:
        """Ensure create_app() is still accessible from family_office_ledger.cli."""
        from family_office_ledger.cli import create_app

        assert callable(create_app)

    def test_get_default_db_path_accessible(self) -> None:
        """Ensure get_default_db_path() is still accessible."""
        from family_office_ledger.cli import get_default_db_path

        assert callable(get_default_db_path)


class TestCLIFunctionalIntegration:
    """Test that CLI functions work correctly after refactoring."""

    def test_main_with_version(self, capsys) -> None:
        """Test that version command still works."""
        from family_office_ledger.cli import main

        result = main(["version"])
        assert result == 0

        captured = capsys.readouterr()
        assert "v0.1.0" in captured.out

    def test_main_with_no_args(self, capsys) -> None:
        """Test that no arguments shows help."""
        from family_office_ledger.cli import main

        result = main([])
        assert result == 0

    def test_init_command_works(self, tmp_path) -> None:
        """Test that init command still works."""
        from family_office_ledger.cli import main

        db_path = tmp_path / "test.db"
        result = main(["--database", str(db_path), "init"])

        assert result == 0
        assert db_path.exists()

    def test_status_command_works(self, tmp_path) -> None:
        """Test that status command still works."""
        from family_office_ledger.cli import main

        db_path = tmp_path / "test.db"
        main(["--database", str(db_path), "init"])
        result = main(["--database", str(db_path), "status"])

        assert result == 0
