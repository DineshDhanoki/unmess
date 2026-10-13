"""Privacy-safe local smoke runner for untracked real documents.

This script emits only bounded machine metadata. It never prints extracted text,
filenames, parser exception messages, or model responses.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from time import perf_counter
from typing import Any

from unmess.parsing.base import ParsedPage

ROOT = Path(__file__).resolve().parents[1]
SMOKE_DIR = ROOT / "eval/real_smoke"
DEFAULT_DUMP_DIR = ROOT / "eval/real_smoke_out"
SUPPORTED_IMAGES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
_EXCEPTION_NAME = re.compile(r"^[A-Z][A-Za-z0-9_]*(?:Error|Exception|Unavailable)$")


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


def _error_kind(error: str | None) -> str:
    """Reduce an internal parser error to a safe class name or fixed category."""
    if not error:
        return "parse_error"
    candidate = error.partition(":")[0].strip()
    if _EXCEPTION_NAME.fullmatch(candidate):
        return candidate
    normalized = error.casefold()
    if "timeout" in normalized or "timed out" in normalized:
        return "timeout"
    if any(term in normalized for term in ("connect", "unreachable", "connection refused")):
        return "backend_unreachable"
    return "parse_error"


def _emit_page(
    *,
    filename_hash: str,
    page_number: int,
    parser: str,
    route_reason: str,
    quality_score: float,
    review_flag: bool,
    parse_time_s: float,
    failed: bool,
    error_kind: str | None,
    signals: dict[str, float],
    review_gate_threshold: float,
    document_conversion_time_s: float | None = None,
    from_document_conversion: bool = False,
) -> None:
    record: dict[str, object] = {
        "filename_hash": filename_hash,
        "page": page_number,
        "parser": parser,
        "route_reason": route_reason,
        "quality_score": round(quality_score, 6),
        "review_flag": review_flag,
        "parse_time_s": round(parse_time_s, 6),
        "failed": failed,
        "error_kind": error_kind,
        "signals": {name: round(value, 6) for name, value in sorted(signals.items())},
        "review_gate_threshold": round(review_gate_threshold, 6),
    }
    if document_conversion_time_s is not None:
        record["document_conversion_time_s"] = round(document_conversion_time_s, 6)
    if from_document_conversion:
        record["from_document_conversion"] = True
    print(json.dumps(record, separators=(",", ":")), flush=True)


def _emit_summary(
    *, files: int, pages: int, pages_per_parser: Counter[str], flagged: int, failed: int
) -> None:
    print(
        json.dumps(
            {
                "files": files,
                "pages": pages,
                "pages_per_parser": dict(sorted(pages_per_parser.items())),
                "flagged": flagged,
                "failed": failed,
            },
            separators=(",", ":"),
        ),
        flush=True,
    )


def _ensure_dump_dir_safe(dump_dir: Path) -> None:
    """Reject repository-local dump directories that Git does not ignore."""
    root = ROOT.resolve()
    target = dump_dir.resolve()
    try:
        relative = target.relative_to(root)
    except ValueError:
        return
    probe = relative / ".unmess-ignore-check"
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", str(probe)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError("repository-local dump directory is not ignored")


def _write_markdown(dump_dir: Path, filename_hash: str, page_number: int, text: str) -> None:
    path = dump_dir / f"{filename_hash}-page-{page_number:04d}.md"
    path.write_text(text, encoding="utf-8")


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


def _docling_duration(parsed: ParsedPage) -> float:
    for attempt in parsed.attempts:
        if attempt.parser == "docling":
            return attempt.duration_s
    return parsed.parse_time_s


def _run_smoke(
    smoke_dir: Path,
    dump_dir: Path,
    router: Any,
    pymupdf: Any,
    review_gate_threshold: float,
) -> int:
    pages = 0
    flagged = 0
    failed = 0
    pages_per_parser: Counter[str] = Counter()
    docling_documents: set[Path] = set()

    if not smoke_dir.is_dir():
        _emit_summary(
            files=0, pages=0, pages_per_parser=pages_per_parser, flagged=0, failed=0
        )
        return 1
    inputs = sorted(
        path
        for path in smoke_dir.iterdir()
        if path.is_file()
        and (path.suffix.casefold() == ".pdf" or path.suffix.casefold() in SUPPORTED_IMAGES)
    )
    if not inputs:
        _emit_summary(
            files=0, pages=0, pages_per_parser=pages_per_parser, flagged=0, failed=0
        )
        return 1
    try:
        _ensure_dump_dir_safe(dump_dir)
    except ValueError:
        _emit_summary(
            files=len(inputs), pages=0, pages_per_parser=pages_per_parser, flagged=0, failed=0
        )
        return 1
    dump_dir.mkdir(parents=True, exist_ok=True)

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
            except Exception as exc:
                pages += 1
                flagged += 1
                failed += 1
                pages_per_parser["none"] += 1
                _write_markdown(dump_dir, token, 1, "")
                _emit_page(
                    filename_hash=token,
                    page_number=1,
                    parser="none",
                    route_reason="input_unreadable",
                    quality_score=0.0,
                    review_flag=True,
                    parse_time_s=0.0,
                    failed=True,
                    error_kind=type(exc).__name__,
                    signals={},
                    review_gate_threshold=review_gate_threshold,
                )
                continue

            for page_number in range(1, page_count + 1):
                started = perf_counter()
                try:
                    with _silence_process_output():
                        parsed = router.parse_page(parse_path, page_number)
                except Exception as exc:
                    parsed = ParsedPage.failed(
                        page_number,
                        "none",
                        type(exc).__name__,
                        parse_time_s=perf_counter() - started,
                    )
                    parsed.route_reason = "parse_failed"
                    parsed.review_reasons = ["parser_failed"]

                elapsed = perf_counter() - started
                page_failed = not parsed.success
                review_flag = bool(parsed.review_reasons) or page_failed
                conversion_time: float | None = None
                from_conversion = False
                if parsed.parser_name == "docling":
                    if parse_path in docling_documents:
                        from_conversion = True
                    else:
                        docling_documents.add(parse_path)
                        conversion_time = _docling_duration(parsed)

                pages += 1
                flagged += int(review_flag)
                failed += int(page_failed)
                pages_per_parser[parsed.parser_name] += 1
                _write_markdown(dump_dir, token, page_number, parsed.text)
                _emit_page(
                    filename_hash=token,
                    page_number=page_number,
                    parser=parsed.parser_name,
                    route_reason=parsed.route_reason or "parse_failed",
                    quality_score=parsed.quality_score,
                    review_flag=review_flag,
                    parse_time_s=max(parsed.parse_time_s, elapsed),
                    failed=page_failed,
                    error_kind=_error_kind(parsed.error) if page_failed else None,
                    signals=parsed.quality_signals,
                    review_gate_threshold=review_gate_threshold,
                    document_conversion_time_s=conversion_time,
                    from_document_conversion=from_conversion,
                )

    _emit_summary(
        files=len(inputs),
        pages=pages,
        pages_per_parser=pages_per_parser,
        flagged=flagged,
        failed=failed,
    )
    return 1 if failed else 0


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump-dir", type=Path, default=DEFAULT_DUMP_DIR)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    with _silence_process_output():
        import pymupdf

        from unmess.config import Settings
        from unmess.parsing.router import PageRouter

        settings = Settings()
        router = PageRouter(settings)
    return _run_smoke(
        SMOKE_DIR,
        args.dump_dir,
        router,
        pymupdf,
        settings.quality_review_threshold,
    )


if __name__ == "__main__":
    raise SystemExit(main())
