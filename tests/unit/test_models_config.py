"""Domain and settings validation at the boundaries."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from unmess.config import Settings
from unmess.models import BBox, Cell, Table


def test_bbox_rejects_invalid_geometry() -> None:
    with pytest.raises(ValidationError):
        BBox(page=1, x0=0.5, y0=0.2, x1=0.4, y1=0.9)


def test_table_requires_page_consistency() -> None:
    cell = Cell(row=0, col=0, text="x", bbox=BBox(page=2, x0=0, y0=0, x1=1, y1=1))
    with pytest.raises(ValidationError):
        Table(table_id="t", page_numbers=[1], cells=[cell])


def test_settings_env_and_threshold_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UNMESS_TEXT_MODEL", "local-alternative")
    assert Settings().text_model == "local-alternative"
    with pytest.raises(ValidationError):
        Settings(parser_text_density_threshold=1.1)
    with pytest.raises(ValidationError):
        Settings(redis_url="https://example.com")
    with pytest.raises(ValidationError):
        Settings(chunk_target_tokens=50, chunk_overlap_tokens=50)


def test_settings_cover_env_example() -> None:
    root = Path(__file__).resolve().parents[2]
    keys = {
        line.split("=", 1)[0].removeprefix("UNMESS_").lower()
        for line in (root / ".env.example").read_text().splitlines()
        if line and not line.startswith("#")
    }
    assert keys == set(Settings.model_fields)
