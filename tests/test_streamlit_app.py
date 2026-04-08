"""AppTest coverage for Phase 5 Streamlit control-room shell.

Tests the landing view, shared composer behavior, and demo-card-to-composer flow
using Streamlit's built-in AppTest framework without requiring a browser.
"""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit", reason="streamlit not installed")

from streamlit.testing.v1 import AppTest  # noqa: E402


APP_PATH = "app/streamlit_app.py"


def _get_app() -> AppTest:
    """Create an AppTest instance for the control-room shell."""
    return AppTest.from_file(APP_PATH, default_timeout=30)


def test_dashboard_landing_view_shows_composer_and_demo_cards() -> None:
    """Landing view must show a complaint composer text area and demo scenario cards."""
    at = _get_app()
    at.run()

    # at.exception is an ElementList; falsy when empty (no exceptions raised)
    assert not at.exception, f"App raised exception on load: {at.exception}"

    # Composer should be visible - either a text_area or form with text input
    has_composer = len(at.text_area) > 0 or len(at.text_input) > 0
    assert has_composer, "Landing view must show a complaint composer (text_area or text_input)"

    # Scenario cards should be visible - rendered as buttons or expanders
    # Five demos should create at least 5 interactive elements (buttons, etc.)
    total_interactive = len(at.button) + len(at.expander)
    assert total_interactive >= 5, (
        f"Landing view must show at least 5 scenario card controls, got {total_interactive} "
        f"(buttons={len(at.button)}, expanders={len(at.expander)})"
    )


def test_landing_view_has_no_exceptions() -> None:
    """App should load without raising any exceptions."""
    at = _get_app()
    at.run()
    # at.exception is an ElementList; falsy when empty (no exceptions)
    assert not at.exception, f"App raised exception: {at.exception}"


def test_demo_cards_appear_on_landing() -> None:
    """All five golden demo scenario cards must appear on the landing view."""
    at = _get_app()
    at.run()

    # Scenario card buttons let the operator load a demo into the composer
    # We expect at least 5 load-demo buttons (one per scenario)
    # Plus possibly a submit button, so total buttons >= 5
    assert len(at.button) >= 5, (
        f"Expected at least 5 demo card buttons, got {len(at.button)}"
    )


def test_composer_is_editable_on_landing() -> None:
    """The complaint composer must be editable (text_area input) on landing."""
    at = _get_app()
    at.run()

    # Landing view should have at least one text_area for the complaint composer
    assert len(at.text_area) >= 1, "Landing view must have an editable complaint text area"

    # The text area should start empty (blank composer on load)
    composer = at.text_area[0]
    assert composer.value == "", f"Composer should start blank, got: '{composer.value}'"


def test_loading_demo_populates_composer() -> None:
    """Clicking a demo button should load its complaint text into the shared composer."""
    at = _get_app()
    at.run()

    # Click the first demo load button
    assert len(at.button) >= 1, "Must have at least one demo button to click"
    at.button[0].click().run()

    # at.exception is an ElementList; falsy when empty (no exceptions raised)
    assert not at.exception, f"Exception after clicking demo button: {at.exception}"

    # After clicking, the composer should be populated with demo text
    assert len(at.text_area) >= 1, "Composer text_area must still be present after demo load"
    composer = at.text_area[0]
    assert len(composer.value) > 0, "Composer should be populated after loading a demo"


def test_app_has_form_for_complaint_submission() -> None:
    """The control-room shell must include an st.form for complaint submission."""
    at = _get_app()
    at.run()

    # st.form submit buttons appear in at.button in AppTest.
    # With 5 demo load buttons + at least 1 form submit button (Run Pipeline),
    # there should be more than 5 buttons total.
    assert len(at.button) >= 6, (
        f"App must have demo load buttons plus a form submit button, got {len(at.button)} buttons"
    )


def test_page_title_or_header_is_visible() -> None:
    """The control-room shell must display a visible title or header."""
    at = _get_app()
    at.run()

    has_title = len(at.title) > 0 or len(at.header) > 0 or len(at.subheader) > 0
    assert has_title, "App must display a page title, header, or subheader"
