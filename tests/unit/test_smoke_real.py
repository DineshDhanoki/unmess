import json
from pathlib import Path
from typing import Any

import pytest

from scripts.smoke_real import _emit_page, _error_kind, _filename_token, _run_smoke
from unmess.parsing.base import ParsedPage, ParserAttempt


class _Document:
    def __init__(self, pages: int) -> None:
        self.pages = pages

    def __enter__(self) -> "_Document":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def __len__(self) -> int:
        return self.pages


class _PyMuPDF:
    def __init__(self, pages: int = 1) -> None:
        self.pages = pages

    def open(self, _path: Path) -> _Document:
        return _Document(self.pages)


def _records(output: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in output.splitlines()]


def test_smoke_output_contains_only_safe_page_metadata(
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = Path("private-invoice.pdf")
    token = _filename_token(path)
    _emit_page(
        filename_hash=token,
        page_number=2,
        parser="vlm",
        route_reason="scan_or_low_text_density",
        quality_score=0.75,
        review_flag=False,
        parse_time_s=1.25,
        failed=False,
        error_kind=None,
        signals={"text_coverage": 0.8},
        review_gate_threshold=0.7,
    )

    output = capsys.readouterr().out
    record = json.loads(output)
    assert record == {
        "filename_hash": token,
        "page": 2,
        "parser": "vlm",
        "route_reason": "scan_or_low_text_density",
        "quality_score": 0.75,
        "review_flag": False,
        "parse_time_s": 1.25,
        "failed": False,
        "error_kind": None,
        "signals": {"text_coverage": 0.8},
        "review_gate_threshold": 0.7,
    }
    assert path.name not in output


def test_smoke_empty_folder_fails_with_zero_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    smoke_dir = tmp_path / "inputs"
    smoke_dir.mkdir()

    result = _run_smoke(smoke_dir, tmp_path / "output", object(), _PyMuPDF(), 0.7)

    assert result == 1
    assert _records(capsys.readouterr().out) == [
        {"files": 0, "pages": 0, "pages_per_parser": {}, "flagged": 0, "failed": 0}
    ]


def test_smoke_normal_case_dumps_markdown_and_marks_docling_conversion(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    smoke_dir = tmp_path / "inputs"
    dump_dir = tmp_path / "output"
    smoke_dir.mkdir()
    source = smoke_dir / "synthetic.pdf"
    source.write_bytes(b"synthetic")

    class Router:
        def parse_page(self, _path: Path, page_number: int) -> ParsedPage:
            return ParsedPage(
                page_number=page_number,
                parser_name="docling",
                text=f"synthetic page {page_number}",
                parse_time_s=0.02,
                quality_score=0.9,
                quality_signals={"text_coverage": 0.8, "character_integrity": 1.0},
                route_reason="complex_layout_or_table",
                attempts=[
                    ParserAttempt(
                        parser="docling",
                        reason="complex_layout_or_table",
                        succeeded=True,
                        quality_score=0.9,
                        duration_s=0.5 if page_number == 1 else 0.02,
                    )
                ],
            )

    result = _run_smoke(smoke_dir, dump_dir, Router(), _PyMuPDF(pages=2), 0.7)

    records = _records(capsys.readouterr().out)
    assert result == 0
    assert records[0]["document_conversion_time_s"] == 0.5
    assert "from_document_conversion" not in records[0]
    assert records[1]["from_document_conversion"] is True
    assert "document_conversion_time_s" not in records[1]
    assert records[2] == {
        "files": 1,
        "pages": 2,
        "pages_per_parser": {"docling": 2},
        "flagged": 0,
        "failed": 0,
    }
    token = _filename_token(source)
    assert (dump_dir / f"{token}-page-0001.md").read_text() == "synthetic page 1"
    assert (dump_dir / f"{token}-page-0002.md").read_text() == "synthetic page 2"


def test_smoke_mocked_backend_failure_is_safe_and_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    smoke_dir = tmp_path / "inputs"
    dump_dir = tmp_path / "output"
    smoke_dir.mkdir()
    (smoke_dir / "synthetic.pdf").write_bytes(b"synthetic")

    class Router:
        def parse_page(self, _path: Path, _page_number: int) -> ParsedPage:
            raise TimeoutError("private document text must not escape")

    result = _run_smoke(smoke_dir, dump_dir, Router(), _PyMuPDF(), 0.7)

    output = capsys.readouterr().out
    records = _records(output)
    assert result == 1
    assert records[0]["failed"] is True
    assert records[0]["error_kind"] == "TimeoutError"
    assert records[0]["signals"] == {}
    assert records[1] == {
        "files": 1,
        "pages": 1,
        "pages_per_parser": {"none": 1},
        "flagged": 1,
        "failed": 1,
    }
    assert "private document text" not in output
    assert _error_kind("private_document_text") == "parse_error"
