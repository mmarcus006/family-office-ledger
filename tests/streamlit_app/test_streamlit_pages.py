"""Tests for Streamlit pages - verifies pages can be imported."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_streamlit_env():
    """Mock all streamlit dependencies for import testing."""
    mock_st = MagicMock()
    mock_st.session_state = {}
    mock_st.cache_data = lambda ttl=None: lambda f: f
    mock_st.title = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])
    mock_st.sidebar = MagicMock()
    mock_st.tabs = MagicMock(return_value=[MagicMock(), MagicMock(), MagicMock()])
    mock_st.form = MagicMock()
    mock_st.selectbox = MagicMock()
    mock_st.text_input = MagicMock()
    mock_st.number_input = MagicMock()
    mock_st.date_input = MagicMock()
    mock_st.button = MagicMock()
    mock_st.metric = MagicMock()
    mock_st.dataframe = MagicMock()
    mock_st.plotly_chart = MagicMock()
    mock_st.error = MagicMock()
    mock_st.info = MagicMock()
    mock_st.success = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.expander = MagicMock()
    mock_st.json = MagicMock()
    mock_st.download_button = MagicMock()
    mock_st.slider = MagicMock()
    mock_st.multiselect = MagicMock()
    mock_st.stop = MagicMock()
    mock_st.rerun = MagicMock()
    mock_st.form_submit_button = MagicMock()
    mock_st.column_config = MagicMock()

    mock_pd = MagicMock()
    mock_pd.DataFrame = MagicMock(return_value=MagicMock())
    mock_pd.read_csv = MagicMock()

    mock_plotly = MagicMock()
    mock_plotly.Figure = MagicMock()
    mock_plotly.Pie = MagicMock()
    mock_plotly.Bar = MagicMock()
    mock_plotly.Scatter = MagicMock()

    mock_httpx = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "streamlit": mock_st,
            "pandas": mock_pd,
            "plotly": MagicMock(),
            "plotly.graph_objects": mock_plotly,
            "httpx": mock_httpx,
        },
    ):
        yield mock_st


class TestStylesModule:
    """Tests for the styles module."""

    def test_import_styles(self, mock_streamlit_env) -> None:
        """Test that styles module can be imported."""
        from family_office_ledger.streamlit_app.styles import (
            CHART_COLORS,
            COLORS,
            apply_custom_css,
            format_currency,
            get_amount_color,
            get_plotly_layout,
            metric_card,
            section_header,
        )

        assert isinstance(COLORS, dict)
        assert isinstance(CHART_COLORS, list)
        assert callable(apply_custom_css)
        assert callable(format_currency)
        assert callable(get_amount_color)
        assert callable(get_plotly_layout)
        assert callable(metric_card)
        assert callable(section_header)

    def test_format_currency(self, mock_streamlit_env) -> None:
        """Test currency formatting."""
        from family_office_ledger.streamlit_app.styles import format_currency

        assert format_currency(1000) == "$1,000.00"
        assert format_currency(1234.56) == "$1,234.56"
        assert format_currency(-500) == "-$500.00"
        assert format_currency(100, show_sign=True) == "+$100.00"
        assert format_currency("invalid") == "invalid"

    def test_get_amount_color(self, mock_streamlit_env) -> None:
        """Test amount color determination."""
        from family_office_ledger.streamlit_app.styles import COLORS, get_amount_color

        assert get_amount_color(100) == COLORS["positive"]
        assert get_amount_color(-100) == COLORS["negative"]
        assert get_amount_color(0) == COLORS["text"]
        assert get_amount_color("invalid") == COLORS["text"]

    def test_get_plotly_layout(self, mock_streamlit_env) -> None:
        """Test Plotly layout configuration."""
        from family_office_ledger.streamlit_app.styles import get_plotly_layout

        layout = get_plotly_layout()
        assert "paper_bgcolor" in layout
        assert "plot_bgcolor" in layout
        assert "font" in layout

        layout_with_title = get_plotly_layout("Test Title")
        assert "title" in layout_with_title


class TestAPIClientModule:
    """Tests for the API client module structure."""

    def test_import_api_client(self, mock_streamlit_env) -> None:
        """Test that api_client module can be imported."""
        from family_office_ledger.streamlit_app import api_client

        # Check all new functions exist
        assert hasattr(api_client, "list_audit_entries")
        assert hasattr(api_client, "get_audit_entry")
        assert hasattr(api_client, "list_entity_audit_trail")
        assert hasattr(api_client, "get_audit_summary")

        assert hasattr(api_client, "add_exchange_rate")
        assert hasattr(api_client, "list_exchange_rates")
        assert hasattr(api_client, "get_latest_exchange_rate")
        assert hasattr(api_client, "get_exchange_rate")
        assert hasattr(api_client, "delete_exchange_rate")
        assert hasattr(api_client, "convert_currency")

        assert hasattr(api_client, "get_asset_allocation")
        assert hasattr(api_client, "get_concentration_report")
        assert hasattr(api_client, "get_performance_report")
        assert hasattr(api_client, "get_portfolio_summary")

        assert hasattr(api_client, "list_qsbs_securities")
        assert hasattr(api_client, "mark_security_qsbs_eligible")
        assert hasattr(api_client, "remove_security_qsbs_eligibility")
        assert hasattr(api_client, "get_qsbs_summary")

        assert hasattr(api_client, "generate_tax_documents")
        assert hasattr(api_client, "get_tax_summary")
        assert hasattr(api_client, "get_form_8949_csv")
        assert hasattr(api_client, "get_schedule_d")

    def test_api_error_class(self, mock_streamlit_env) -> None:
        """Test APIError class exists and works."""
        from family_office_ledger.streamlit_app.api_client import APIError

        error = APIError(404, "Not found")
        assert error.status_code == 404
        assert error.detail == "Not found"
        assert "404" in str(error)
        assert "Not found" in str(error)


class TestAppModule:
    """Tests for the main app module."""

    def test_import_app(self, mock_streamlit_env) -> None:
        """Test that app module can be imported."""
        from family_office_ledger.streamlit_app.app import init_session_state

        assert callable(init_session_state)


class TestPageModulesExist:
    """Tests that verify all page modules exist and have expected structure."""

    def test_audit_page_exists(self) -> None:
        """Test that 8_Audit.py exists."""
        from pathlib import Path

        page_path = Path("src/family_office_ledger/streamlit_app/pages/8_Audit.py")
        assert page_path.exists(), "8_Audit.py should exist"

    def test_currency_page_exists(self) -> None:
        """Test that 9_Currency.py exists."""
        from pathlib import Path

        page_path = Path("src/family_office_ledger/streamlit_app/pages/9_Currency.py")
        assert page_path.exists(), "9_Currency.py should exist"

    def test_portfolio_page_exists(self) -> None:
        """Test that 10_Portfolio.py exists."""
        from pathlib import Path

        page_path = Path("src/family_office_ledger/streamlit_app/pages/10_Portfolio.py")
        assert page_path.exists(), "10_Portfolio.py should exist"

    def test_qsbs_page_exists(self) -> None:
        """Test that 11_QSBS.py exists."""
        from pathlib import Path

        page_path = Path("src/family_office_ledger/streamlit_app/pages/11_QSBS.py")
        assert page_path.exists(), "11_QSBS.py should exist"

    def test_tax_page_exists(self) -> None:
        """Test that 12_Tax.py exists."""
        from pathlib import Path

        page_path = Path("src/family_office_ledger/streamlit_app/pages/12_Tax.py")
        assert page_path.exists(), "12_Tax.py should exist"

    def test_all_pages_count(self) -> None:
        """Test that all 14 pages exist."""
        from pathlib import Path

        pages_dir = Path("src/family_office_ledger/streamlit_app/pages")
        pages = list(pages_dir.glob("*.py"))
        # Filter out __pycache__ and __init__.py
        pages = [p for p in pages if not p.name.startswith("__")]
        assert len(pages) == 14, (
            f"Expected 14 pages, found {len(pages)}: {[p.name for p in pages]}"
        )


class TestPageContents:
    """Tests that verify page contents have required elements."""

    def test_audit_page_has_required_imports(self) -> None:
        """Test that Audit page has required imports."""
        from pathlib import Path

        content = Path(
            "src/family_office_ledger/streamlit_app/pages/8_Audit.py"
        ).read_text()

        assert "from __future__ import annotations" in content
        assert "apply_custom_css" in content
        assert "api_client" in content
        assert "init_session_state" in content

    def test_currency_page_has_required_imports(self) -> None:
        """Test that Currency page has required imports."""
        from pathlib import Path

        content = Path(
            "src/family_office_ledger/streamlit_app/pages/9_Currency.py"
        ).read_text()

        assert "from __future__ import annotations" in content
        assert "apply_custom_css" in content
        assert "api_client" in content

    def test_portfolio_page_has_required_imports(self) -> None:
        """Test that Portfolio page has required imports."""
        from pathlib import Path

        content = Path(
            "src/family_office_ledger/streamlit_app/pages/10_Portfolio.py"
        ).read_text()

        assert "from __future__ import annotations" in content
        assert "apply_custom_css" in content
        assert "get_plotly_layout" in content

    def test_qsbs_page_has_required_imports(self) -> None:
        """Test that QSBS page has required imports."""
        from pathlib import Path

        content = Path(
            "src/family_office_ledger/streamlit_app/pages/11_QSBS.py"
        ).read_text()

        assert "from __future__ import annotations" in content
        assert "apply_custom_css" in content
        assert "format_currency" in content

    def test_tax_page_has_required_imports(self) -> None:
        """Test that Tax page has required imports."""
        from pathlib import Path

        content = Path(
            "src/family_office_ledger/streamlit_app/pages/12_Tax.py"
        ).read_text()

        assert "from __future__ import annotations" in content
        assert "apply_custom_css" in content
        assert "format_currency" in content

    def test_all_new_pages_use_cache_decorator(self) -> None:
        """Test that all new pages use @st.cache_data decorator."""
        from pathlib import Path

        new_pages = [
            "8_Audit.py",
            "9_Currency.py",
            "10_Portfolio.py",
            "11_QSBS.py",
            "12_Tax.py",
        ]

        pages_dir = Path("src/family_office_ledger/streamlit_app/pages")

        for page_name in new_pages:
            content = (pages_dir / page_name).read_text()
            assert "@st.cache_data" in content, f"{page_name} should use @st.cache_data"
