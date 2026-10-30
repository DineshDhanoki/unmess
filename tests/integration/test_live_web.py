"""The public web page must run the same live, synthetic pipeline as the CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest


def test_live_page_runs_selected_invoice() -> None:
    entrypoint = Path(__file__).resolve().parents[2] / "ui/live_demo.py"
    app = AppTest.from_file(entrypoint).run(timeout=15)
    assert not app.exception

    app.button[0].click().run(timeout=15)
    assert not app.exception
    assert app.metric[0].value == "10,000"

    app.selectbox[0].set_value("01").run(timeout=15)
    assert not app.metric  # A new choice must not show the previous invoice's answer.
    app.button[0].click().run(timeout=15)
    assert not app.exception
    assert app.metric[0].value == "28,000"
