"""Opt-in smoke test; run with `uv run pytest -m integration`."""

from pathlib import Path

import pytest

from unmess.config import Settings
from unmess.parsing.vlm_parser import VLMParser


@pytest.mark.integration
def test_live_local_ollama() -> None:
    pdf = Path("eval/datasets/pdf/synthetic-scan-00.pdf")
    parsed = VLMParser(Settings()).parse_page(pdf, 1)
    assert parsed.success, parsed.error
