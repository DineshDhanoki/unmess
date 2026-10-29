"""The newcomer demo must work from a clean checkout without services or model files."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_synthetic_invoice_demo() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.demo"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Fictional seller: Demo Vendor 00" in result.stdout
    assert "Total INR: 10,000" in result.stdout
    assert "page 1" in result.stdout
    assert "Search and UI are planned" in result.stdout
    assert result.stderr == ""


def test_synthetic_invoice_demo_saves_highlight(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = tmp_path / "preview" / "source.png"
    result = subprocess.run(
        [sys.executable, "-m", "scripts.demo", "--highlight-output", str(output)],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Fictional seller: Demo Vendor 00" in result.stdout
    assert f"Highlighted synthetic source page: {output}" in result.stdout
    assert result.stderr == ""
    assert output.is_file()
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
