"""Privacy-safe local smoke runner for untracked real documents.

This script intentionally emits only machine metadata. It never prints extracted text,
filenames, parser exceptions, or model responses.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SMOKE_DIR = ROOT / "eval/real_smoke"
SUPPORTED_IMAGES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


@contextlib.contextmanager
def _silence_process_output() -> Iterator[None]:
    """Suppress Python and native-library writes to stdout/stderr."""
    with Path(os.devnull).open("w", encoding="utf-8") as sink:
        sys.stdout.flush()
        sys.stderr.flush()
        saved_stdout = os.dup(1)
        saved_stderr = os.dup(2)
        try:
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(saved_stdout, 1)
            os.dup2(saved_stderr, 2)
            os.close(saved_stdout)
            os.close(saved_stderr)


def _filename_token(path: Path) -> str:
    return hashlib.sha256(path.name.encode("utf-8")).hexdigest()[:12]


def _emit_page(
    *,
    filename_hash: str,
    page_number: int,
    parser: str,
    route_reason: str,
    quality_score: float,
    review_flag: bool,
    parse_time_s: float,
) -> None:
    print(
        json.dumps(
            {
                "filename_hash": filename_hash,
                "page": page_number,
                "parser": parser,
                "route_reason": route_reason,
                "quality_score": round(quality_score, 6),
                "review_flag": review_flag,
                "parse_time_s": round(parse_time_s, 6),
            },
            separators=(",", ":"),
        ),
        flush=True,
    )


def _image_as_pdf(image_path: Path, output_path: Path, pymupdf: Any) -> None:
    image = pymupdf.open(image_path)
    try:
        source = image[0].rect
        document = pymupdf.open()
        try:
            page = document.new_page(width=source.width, height=source.height)
            page.insert_image(page.rect, filename=str(image_path))
            document.save(output_path)
        finally:
            document.close()
    finally:
        image.close()


def main() -> None:
    with _silence_process_output():
        import pymupdf

        from unmess.config import Settings
        from unmess.parsing.router import PageRouter

        settings = Settings()
        router = PageRouter(settings)
        if not SMOKE_DIR.is_dir():
            return
        inputs = sorted(
            path
            for path in SMOKE_DIR.iterdir()
            if path.is_file()
            and (path.suffix.casefold() == ".pdf" or path.suffix.casefold() in SUPPORTED_IMAGES)
        )

    for source in inputs:
        token = _filename_token(source)
        with tempfile.TemporaryDirectory(prefix="unmess-smoke-") as temporary:
            parse_path = source
            try:
                with _silence_process_output():
                    if source.suffix.casefold() in SUPPORTED_IMAGES:
                        parse_path = Path(temporary) / "image.pdf"
                        _image_as_pdf(source, parse_path, pymupdf)
                    with pymupdf.open(parse_path) as document:
                        page_count = len(document)
            except Exception:
                _emit_page(
                    filename_hash=token,
                    page_number=1,
                    parser="none",
                    route_reason="input_unreadable",
                    quality_score=0.0,
                    review_flag=True,
                    parse_time_s=0.0,
                )
                continue

            for page_number in range(1, page_count + 1):
                started = perf_counter()
                with _silence_process_output():
                    parsed = router.parse_page(parse_path, page_number)
                _emit_page(
                    filename_hash=token,
                    page_number=page_number,
                    parser=parsed.parser_name,
                    route_reason=parsed.route_reason or "parse_failed",
                    quality_score=parsed.quality_score,
                    review_flag=bool(parsed.review_reasons),
                    parse_time_s=max(parsed.parse_time_s, perf_counter() - started),
                )


if __name__ == "__main__":
    main()
