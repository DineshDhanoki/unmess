"""Parsing-stage evaluation with a committed test threshold freeze gate."""

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import tomllib
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any, Literal

from eval.baselines.base import ParsedDocument, PipelineAdapter
from eval.baselines.docling_only import DoclingOnly
from eval.baselines.plain_pymupdf import PlainPyMuPDF
from eval.baselines.unmess_parsing import UnmessParsing
from eval.metrics.calibration import score_buckets, spearman
from eval.metrics.latency import latency_per_page
from eval.metrics.ocr_cer import character_error_rate
from eval.metrics.routing_efficiency import cheap_parser_share
from eval.metrics.table_f1 import table_cell_f1
from unmess.config import Settings
from unmess.models import Cell, GroundTruth, Table
from unmess.parsing.base import ParsedPage
from unmess.parsing.vlm_parser import PROMPT_VERSION

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "eval/config/phase2_frozen.toml"
METRICS = (
    "table_f1",
    "ocr_cer",
    "cheap_parser_share",
    "latency_per_page_s",
    "failed_page_rate",
)


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, check=False, capture_output=True, text=True)


def _freeze_commit() -> str | None:
    path = "eval/config/phase2_frozen.toml"
    tracked = _git(["ls-files", "--error-unmatch", path])
    if tracked.returncode:
        return None
    result = _git(["log", "-1", "--format=%H", "--", path])
    return result.stdout.strip() or None


def assert_test_ready() -> str:
    """Refuse test evaluation until thresholds are committed and all tracked files are clean."""
    freeze_commit = _freeze_commit()
    if not freeze_commit:
        raise RuntimeError("test split locked: threshold freeze file is not committed")
    status = _git(["status", "--porcelain"])
    if status.returncode or status.stdout.strip():
        raise RuntimeError("test split locked: working tree must be clean")
    return freeze_commit


def _settings() -> Settings:
    values = tomllib.loads(FROZEN.read_text(encoding="utf-8"))
    return Settings(**values)


def _validate_manifest(dataset: Path) -> tuple[list[GroundTruth], dict[str, Any]]:
    manifest: dict[str, Any] = json.loads((dataset / "MANIFEST.json").read_text())
    truths: list[GroundTruth] = []
    for item in manifest["documents"]:
        pdf = dataset / item["pdf"]
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"PDF hash mismatch: {pdf}")
        truth = GroundTruth.model_validate_json((dataset / item["ground_truth"]).read_text())
        if truth.source_file != item["pdf"] or truth.content_hash != item["sha256"]:
            raise ValueError(f"ground truth/manifest mismatch: {truth.document_id}")
        truths.append(truth)
    return truths, manifest


def _difficulty(truth: GroundTruth) -> str:
    if truth.degradation is None:
        return "not_scan"
    noise = truth.degradation.noise_level
    return "low" if noise <= 0.2 else "medium" if noise <= 0.5 else "high"


def _mean(values: Sequence[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return statistics.mean(present) if present else None


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "documents": len(rows),
        "pages": sum(row["pages"] for row in rows),
        "failed_pages": sum(row["failed_pages"] for row in rows),
        **{key: _mean([row[key] for row in rows]) for key in METRICS},
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, dict[str, list[dict[str, Any]]]] = {
        "by_category": defaultdict(list),
        "by_language": defaultdict(list),
        "by_scan_difficulty": defaultdict(list),
    }
    for row in rows:
        groups["by_category"][row["category"]].append(row)
        groups["by_language"][row["language"]].append(row)
        groups["by_scan_difficulty"][row["scan_difficulty"]].append(row)
    return {
        "overall": _aggregate(rows),
        **{
            group: {key: _aggregate(value) for key, value in sorted(entries.items())}
            for group, entries in groups.items()
        },
    }


def _failed_document(truth: GroundTruth, error: str) -> ParsedDocument:
    pages = [ParsedPage.failed(page.page_number, "unavailable", error) for page in truth.pages]
    return ParsedDocument(
        page_texts=["" for _ in pages],
        chunks=[],
        page_durations_s=[0.0 for _ in pages],
        parsers=["unavailable" for _ in pages],
        page_results=pages,
    )


def _page_cells(tables: list[Table], page_number: int) -> list[Table]:
    result: list[Table] = []
    for table in tables:
        cells: list[Cell] = [cell for cell in table.cells if cell.bbox.page == page_number]
        if cells:
            result.append(
                Table(
                    table_id=table.table_id,
                    page_numbers=[page_number],
                    cells=cells,
                    has_merged_cells=any(c.row_span > 1 or c.col_span > 1 for c in cells),
                )
            )
    return result


def _page_accuracy(truth: GroundTruth, parsed: ParsedDocument, page_index: int) -> float:
    if parsed.page_results and not parsed.page_results[page_index].success:
        return 0.0
    reference = " ".join(truth.pages[page_index].expected_text.split())
    prediction = " ".join(parsed.page_texts[page_index].split())
    text_accuracy = max(0.0, 1.0 - character_error_rate(reference, prediction))
    expected_tables = _page_cells(truth.tables, page_index + 1)
    if not expected_tables:
        return text_accuracy
    predicted_tables = _page_cells(parsed.tables, page_index + 1)
    return (text_accuracy + table_cell_f1(expected_tables, predicted_tables)[2]) / 2


def _document_scores(truth: GroundTruth, parsed: ParsedDocument) -> dict[str, Any]:
    failures = [page for page in parsed.page_results if not page.success]
    cer_values = [
        character_error_rate(page.expected_text, parsed.page_texts[page.page_number - 1])
        for page in truth.pages
        if page.is_ocr_page
    ]
    return {
        "document_id": truth.document_id,
        "category": truth.category,
        "language": "hi" if any(page.language == "hi" for page in truth.pages) else "en",
        "scan_difficulty": _difficulty(truth),
        "pages": len(truth.pages),
        "failed_pages": len(failures),
        "table_f1": table_cell_f1(truth.tables, parsed.tables)[2] if truth.tables else None,
        "ocr_cer": _mean(cer_values),
        "cheap_parser_share": cheap_parser_share(parsed.parsers),
        "latency_per_page_s": (
            latency_per_page(parsed.page_durations_s)
            if any(value > 0 for value in parsed.page_durations_s)
            else None
        ),
        "failed_page_rate": len(failures) / len(truth.pages),
        "page_accuracy": [
            _page_accuracy(truth, parsed, index) for index in range(len(truth.pages))
        ],
        "quality_scores": [page.quality_score for page in parsed.page_results],
        "failures": [
            {
                "page": page.page_number,
                "parser": page.parser_name,
                "error": page.error,
                "attempts": [attempt.__dict__ for attempt in page.attempts],
            }
            for page in failures
        ],
    }


def _run_adapter(
    adapter: PipelineAdapter, truths: list[GroundTruth], dataset: Path, split: str
) -> dict[str, Any]:
    selected = [truth for truth in truths if truth.split == split]
    parsed: dict[str, ParsedDocument] = {}
    for truth in selected:
        try:
            parsed[truth.document_id] = adapter.parse(
                dataset / truth.source_file, truth.document_id
            )
            if len(parsed[truth.document_id].page_texts) != len(truth.pages):
                raise ValueError("adapter returned the wrong number of pages")
            if len(parsed[truth.document_id].page_results) != len(truth.pages):
                raise ValueError("adapter omitted page outcomes")
        except Exception as exc:
            parsed[truth.document_id] = _failed_document(truth, f"{type(exc).__name__}: {exc}")
    rows = [_document_scores(truth, parsed[truth.document_id]) for truth in selected]
    failures = [
        {"document_id": row["document_id"], **failure}
        for row in rows
        for failure in row["failures"]
    ]
    return {
        "status": "ok" if not failures else "partial_failure",
        "summary": _summarize(rows),
        "documents": rows,
        "failures": failures,
    }


def _calibration(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [score for row in rows for score in row["quality_scores"]]
    accuracy = [value for row in rows for value in row["page_accuracy"]]
    return {
        "pages": len(scores),
        "spearman_rho": spearman(scores, accuracy),
        "score_buckets": score_buckets(scores, accuracy),
        "accuracy_definition": (
            "mean of clipped normalized-text similarity and page table F1 where tables exist"
        ),
    }


def run(dataset: Path, split: Literal["dev", "test"] = "dev") -> dict[str, Any]:
    freeze_commit = assert_test_ready() if split == "test" else _freeze_commit()
    settings = _settings()
    truths, manifest = _validate_manifest(dataset)
    dataset_bytes = sum((dataset / item["pdf"]).stat().st_size for item in manifest["documents"])
    result: dict[str, Any] = {
        "metadata": {
            "run_date_utc": datetime.now(UTC).isoformat(),
            "git_commit": _git(["rev-parse", "HEAD"]).stdout.strip(),
            "freeze_commit": freeze_commit,
            "working_tree_dirty": bool(_git(["status", "--porcelain"]).stdout.strip()),
            "generator_version": manifest["generator_version"],
            "seed": manifest["seed"],
            "dataset_documents": len(truths),
            "dataset_pdf_bytes": dataset_bytes,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "libraries": {
                name: version(name) for name in ("pymupdf", "reportlab", "pillow", "pydantic")
            },
            "models": {"vision": settings.vision_model, "prompt_version": PROMPT_VERSION},
            "frozen_thresholds": tomllib.loads(FROZEN.read_text(encoding="utf-8")),
            "retrieval": "n/a: parsing stage only",
        },
        "systems": {},
        "calibration_dev": None,
    }
    splits = ("dev", "test") if split == "test" else ("dev",)
    adapters: list[PipelineAdapter] = [PlainPyMuPDF(), DoclingOnly(), UnmessParsing(settings)]
    for adapter in adapters:
        result["systems"][adapter.name] = {selected: None for selected in ("dev", "test")}
        for selected in splits:
            part = _run_adapter(adapter, truths, dataset, selected)
            result["systems"][adapter.name][selected] = part
            if adapter.name == UnmessParsing.name and selected == "dev":
                result["calibration_dev"] = _calibration(part["documents"])
    return result


def _format(value: Any) -> str:
    return "n/a" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)


def markdown(result: dict[str, Any]) -> str:
    meta = result["metadata"]
    lines = [
        "# Unmess Phase 2 parsing evaluation",
        "",
        f"Run: {meta['run_date_utc']} | source commit `{meta['git_commit']}` | "
        f"freeze commit `{meta['freeze_commit'] or 'not yet committed'}`",
        f"Working tree dirty: {meta['working_tree_dirty']}; dataset: "
        f"{meta['dataset_documents']} PDFs, {meta['dataset_pdf_bytes']} PDF bytes",
        f"Vision model: `{meta['models']['vision']}`; prompt: `{meta['models']['prompt_version']}`",
        f"Python {meta['python']}; platform {meta['platform']}; libraries: "
        + ", ".join(f"{key} {value}" for key, value in meta["libraries"].items()),
        "Retrieval metrics: n/a until Phase 3. Dev is for tuning; "
        "test is evaluated only after freeze.",
        "",
        "Frozen threshold values: `" + json.dumps(meta["frozen_thresholds"], sort_keys=True) + "`",
    ]
    columns = (*METRICS,)
    for split in ("test", "dev"):
        if all(system[split] is None for system in result["systems"].values()):
            continue
        lines += [
            "",
            f"## {split.title()} results",
            "",
            "| System | Group | Documents | Pages | Failed pages | " + " | ".join(columns) + " |",
            "|---|---|---:|---:|---:|" + "---:|" * len(columns),
        ]
        for name, system in result["systems"].items():
            part = system[split]
            if part is None:
                continue
            summary = part["summary"]
            groups = (
                ("overall", {"overall": summary["overall"]}),
                ("category", summary["by_category"]),
                ("language", summary["by_language"]),
                ("scan", summary["by_scan_difficulty"]),
            )
            for group_type, entries in groups:
                for group, row in entries.items():
                    lines.append(
                        f"| {name} | {group_type}:{group} | {row['documents']} | "
                        f"{row['pages']} | {row['failed_pages']} | "
                        + " | ".join(_format(row[column]) for column in columns)
                        + " |"
                    )
    calibration = result["calibration_dev"]
    if calibration:
        lines += [
            "",
            "## Dev quality calibration",
            "",
            f"Spearman rho: {_format(calibration['spearman_rho'])} "
            f"over {calibration['pages']} pages.",
            f"Page accuracy: {calibration['accuracy_definition']}.",
            "",
            "| Score bucket | Pages | Mean page accuracy |",
            "|---|---:|---:|",
        ]
        for bucket, values in calibration["score_buckets"].items():
            lines.append(
                f"| {bucket} | {values['pages']} | {_format(values['mean_page_accuracy'])} |"
            )
    test_unmess = result["systems"]["unmess_parsing"]["test"]
    test_fast = result["systems"]["pymupdf_fixed"]["test"]
    if test_unmess is not None and test_fast is not None:
        lines += ["", "## Test comparison with PyMuPDF baseline", ""]
        for category, ours in test_unmess["summary"]["by_category"].items():
            baseline = test_fast["summary"]["by_category"][category]
            losses = [
                metric
                for metric, higher_is_better in (("table_f1", True), ("ocr_cer", False))
                if ours[metric] is not None
                and baseline[metric] is not None
                and (
                    ours[metric] < baseline[metric]
                    if higher_is_better
                    else ours[metric] > baseline[metric]
                )
            ]
            if ours["failed_pages"] > baseline["failed_pages"]:
                losses.append("failed pages")
            lines.append(f"- {category}: " + (", ".join(losses) if losses else "no measured loss"))
        vlm_failures = sum(
            any(attempt["parser"] == "vlm" for attempt in failure["attempts"])
            for failure in test_unmess["failures"]
        )
        lines += [
            "",
            f"VLM-dependent test pages that failed: {vlm_failures}. "
            "They remain in every metric denominator; see failure details below.",
        ]
    lines += ["", "## Parser failures", ""]
    failures_found = False
    for split in ("test", "dev"):
        for name, system in result["systems"].items():
            part = system[split]
            if part is None:
                continue
            for failure in part["failures"]:
                failures_found = True
                detail = str(failure["error"] or "unknown error").replace("\n", " ")[:180]
                attempts = ", ".join(
                    f"{item['parser']}: {str(item['error'])[:90]}"
                    for item in failure["attempts"]
                    if item["error"]
                )
                lines.append(
                    f"- {split} / {name} / {failure['document_id']} page {failure['page']}: "
                    f"{failure['parser']}: {detail}"
                    + (f" (attempts: {attempts})" if attempts else "")
                )
    if not failures_found:
        lines.append("None.")
    lines += ["", "See EVAL.md for metric definitions and dataset limits.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--dataset", type=Path, default=ROOT / "eval/datasets")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "eval/results")
    args = parser.parse_args()
    result = run(args.dataset, args.split)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "latest.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output_dir / "latest.md").write_text(markdown(result))
    print(
        f"Evaluated {args.split} split; Unmess parsing failures: "
        f"{result['systems']['unmess_parsing'][args.split]['summary']['overall']['failed_pages']}"
    )


if __name__ == "__main__":
    main()
