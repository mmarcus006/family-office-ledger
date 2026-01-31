"""TDD Tests for auth service TODO references.

These tests verify that TODOs in the codebase have proper issue references.
"""

import re
from pathlib import Path

import pytest


class TestAuthServiceTodoReferences:
    """Test that TODOs in auth service have proper references."""

    def test_todo_at_line_596_has_issue_reference(self) -> None:
        """Test that the TODO at line 596 in auth.py has a proper issue reference."""
        auth_path = Path(
            "/mnt/data/home-miller/projects/family-office-ledger"
            "/src/family_office_ledger/services/auth.py"
        )

        content = auth_path.read_text()
        lines = content.split("\n")

        # Find the line with "TODO" around line 596 (0-indexed: 595)
        # Allow some flexibility in line number due to edits
        todo_pattern = re.compile(r"#\s*TODO:?\s*(.+)", re.IGNORECASE)
        issue_pattern = re.compile(r"(?:issue|ticket|gh|#)\s*\d+|FOL-[\w-]+\d+", re.IGNORECASE)

        found_todo = False
        has_reference = False

        for i, line in enumerate(lines):
            match = todo_pattern.search(line)
            if match and 590 <= i <= 600:  # Around line 596
                found_todo = True
                todo_text = match.group(1)
                if issue_pattern.search(todo_text):
                    has_reference = True
                break

        assert found_todo, "TODO not found around line 596 in auth.py"
        assert has_reference, (
            f"TODO at line ~596 in auth.py should have an issue reference "
            f"(e.g., 'TODO(FOL-123)' or 'TODO: Issue #123')"
        )


class TestAllTodosHaveReferences:
    """Test that all TODOs in the codebase have proper references."""

    @pytest.mark.parametrize(
        "filepath",
        [
            "src/family_office_ledger/services/auth.py",
        ],
    )
    def test_todos_have_issue_references(self, filepath: str) -> None:
        """Test that TODOs have issue/ticket references."""
        base_path = Path("/mnt/data/home-miller/projects/family-office-ledger")
        file_path = base_path / filepath

        if not file_path.exists():
            pytest.skip(f"File {filepath} does not exist")

        content = file_path.read_text()
        lines = content.split("\n")

        todo_pattern = re.compile(r"#\s*TODO:?\s*(.+)", re.IGNORECASE)
        # Acceptable reference patterns
        reference_patterns = [
            re.compile(r"FOL-[\w-]+\d+", re.IGNORECASE),  # Jira-style (FOL-123 or FOL-AUTH-001)
            re.compile(r"#\d+"),  # GitHub issue
            re.compile(r"issue\s*#?\d+", re.IGNORECASE),
            re.compile(r"ticket\s*#?\d+", re.IGNORECASE),
            re.compile(r"gh-\d+", re.IGNORECASE),  # GitHub
            re.compile(r"\(\w+-[\w-]*\d+\)"),  # Any project-123 format
        ]

        todos_without_refs = []

        for i, line in enumerate(lines, 1):
            match = todo_pattern.search(line)
            if match:
                todo_text = match.group(1)
                has_ref = any(p.search(todo_text) or p.search(line) for p in reference_patterns)
                if not has_ref:
                    todos_without_refs.append((i, line.strip()))

        if todos_without_refs:
            msg_lines = [f"TODOs without issue references in {filepath}:"]
            for line_num, text in todos_without_refs:
                msg_lines.append(f"  Line {line_num}: {text}")
            pytest.fail("\n".join(msg_lines))
