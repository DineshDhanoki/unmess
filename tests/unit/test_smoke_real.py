import json
from pathlib import Path

import pytest

from scripts.smoke_real import _emit_page, _filename_token


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
    }
    assert path.name not in output
