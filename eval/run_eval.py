"""Parsing-stage evaluation with a committed test threshold freeze gate."""

import argparse
import difflib
import hashlib
import json
import platform
import statistics
import subprocess
import tomllib
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

from eval.baselines.base import ParsedDocument, PipelineAdapter
from eval.baselines.docling_only import DoclingOnly
from eval.baselines.plain_pymupdf import PlainPyMuPDF
from eval.baselines.unmess_parsing import UnmessParsing
from eval.baselines.vlm_every_page import VLMEveryPage
from eval.metrics.bootstrap import document_bootstrap_ci
from eval.metrics.calibration import review_metrics, score_buckets, spearman
from eval.metrics.latency import latency_per_page
from eval.metrics.ocr_cer import character_error_rate, word_error_rate
from eval.metrics.routing_efficiency import cheap_parser_share
from eval.metrics.table_f1 import table_cell_f1
from eval.preflight import run_preflight
from unmess.config import Settings
from unmess.models import Cell, GroundTruth, Table
from unmess.parsing.base import ParsedPage
from unmess.parsing.page_features import inspect_page
from unmess.parsing.router import PageRouter
from unmess.parsing.vlm_parser import PROMPT_VERSION

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "eval/config/phase2_frozen.toml"
DEV_CONFIG = ROOT / "eval/config/phase2b_dev.toml"
SUPERSEDED_FREEZE = "caa7f35c2f46777eba1a690e0292dac1ea04fe39"
BAD_PAGE_ACCURACY_CUTOFF = 0.90
BOOTSTRAP_SEED = 20261011
BOOTSTRAP_SAMPLES = 2000
PHASE2C_REPORT = ROOT / "eval/results/phase2c-dev.json"
METRICS = (
    "table_f1",
    "ocr_cer",
    "text_cer",
    "text_wer",
    "cheap_parser_share",
    "latency_per_page_s",
    "failed_page_rate",
)


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, check=False, capture_output=True, text=True)


def _library_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("pymupdf", "reportlab", "pillow", "pydantic", "docling", "torch"):
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = "not installed"
    return versions


def _freeze_commit() -> str | None:
    path = "eval/config/phase2_frozen.toml"
    tracked = _git(["ls-files", "--error-unmatch", path])
    if tracked.returncode:
        return None
    result = _git(["log", "-1", "--format=%H", "--", path])
    return result.stdout.strip() or None


def assert_test_ready(dataset: Path = ROOT / "eval/datasets") -> str:
    """Refuse test evaluation until thresholds are committed and all tracked files are clean."""
    freeze_commit = _freeze_commit()
    if not freeze_commit:
        raise RuntimeError("test split locked: threshold freeze file is not committed")
    if freeze_commit == SUPERSEDED_FREEZE:
        raise RuntimeError("test split locked: old freeze was superseded; approve a new freeze")
    status = _git(["status", "--porcelain"])
    if status.returncode or status.stdout.strip():
        raise RuntimeError("test split locked: working tree must be clean")
    try:
        settings = _settings("test")
        checks = run_preflight(settings)
    except RuntimeError as exc:
        raise RuntimeError(f"test split locked: backend preflight failed: {exc}") from exc
    ready = {
        parser
        for parser, key in (
            ("pymupdf", "pymupdf_parse"),
            ("docling", "docling_parse"),
            ("vlm", "vision_response"),
        )
        if checks.get(key)
    }
    truths, _manifest = _validate_manifest(dataset, "test")
    router = PageRouter(settings)
    for truth in truths:
        if truth.split != "test":
            continue
        pdf = dataset / truth.source_file
        for page in truth.pages:
            parser, _reason = router._first_route(inspect_page(pdf, page.page_number))
            if parser not in ready:
                raise RuntimeError(
                    f"test split locked: {truth.document_id} page {page.page_number} "
                    f"would route to unavailable {parser}"
                )
    return freeze_commit


def _settings(split: Literal["dev", "test"]) -> Settings:
    config_path = DEV_CONFIG if split == "dev" else FROZEN
    values = tomllib.loads(config_path.read_text(encoding="utf-8"))
    return Settings(**values)


def _validate_manifest(
    dataset: Path, split: Literal["dev", "test"]
) -> tuple[list[GroundTruth], dict[str, Any]]:
    manifest: dict[str, Any] = json.loads((dataset / "MANIFEST.json").read_text())
    truths: list[GroundTruth] = []
    for item in manifest["documents"]:
        if item["split"] != split:
            continue
        pdf = dataset / item["pdf"]
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"PDF hash mismatch: {pdf}")
        truth = GroundTruth.model_validate_json((dataset / item["ground_truth"]).read_text())
        if (
            truth.source_file != item["pdf"]
            or truth.content_hash != item["sha256"]
            or truth.split != item["split"]
        ):
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
    counts = (
        "escalated_pages",
        "escalation_improved_pages",
        "vlm_attempted_pages",
        "vlm_uncached_pages",
    )
    totals = {key: sum(row[key] for row in rows) for key in counts}
    vlm_time = sum(row["vlm_time_s"] for row in rows)
    uncached_time = sum(row["vlm_uncached_time_s"] for row in rows)
    metric_counts = {
        key: {
            "documents": sum(row[key] is not None for row in rows),
            "pages": sum(
                row["table_pages"]
                if key == "table_f1"
                else row["ocr_pages"]
                if key == "ocr_cer"
                else row["pages"]
                for row in rows
                if row[key] is not None
            ),
        }
        for key in METRICS
    }
    return {
        "documents": len(rows),
        "pages": sum(row["pages"] for row in rows),
        "failed_pages": sum(row["failed_pages"] for row in rows),
        **{key: _mean([row[key] for row in rows]) for key in METRICS},
        "metric_counts": metric_counts,
        "total_time_s": sum(sum(row["page_durations_s"]) for row in rows),
        "mean_page_accuracy": _mean([score for row in rows for score in row["page_accuracy"]]),
        **totals,
        "vlm_time_s": vlm_time,
        "vlm_pages_per_second": totals["vlm_attempted_pages"] / vlm_time if vlm_time else None,
        "vlm_uncached_time_s": uncached_time,
        "vlm_uncached_pages_per_second": (
            totals["vlm_uncached_pages"] / uncached_time if uncached_time else None
        ),
        "mean_escalation_accuracy_delta": _mean(
            [delta for row in rows for delta in row["escalation_accuracy_deltas"]]
        ),
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, dict[str, list[dict[str, Any]]]] = {
        "by_cohort": defaultdict(list),
        "by_category": defaultdict(list),
        "by_language": defaultdict(list),
        "by_scan_difficulty": defaultdict(list),
    }
    for row in rows:
        groups["by_cohort"][row["cohort"]].append(row)
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


def _parsed_page_accuracy(truth: GroundTruth, page: ParsedPage) -> float:
    if not page.success:
        return 0.0
    page_index = page.page_number - 1
    reference = " ".join(truth.pages[page_index].expected_text.split())
    prediction = " ".join(page.text.split())
    text_accuracy = max(0.0, 1.0 - character_error_rate(reference, prediction))
    expected_tables = _page_cells(truth.tables, page_index + 1)
    if not expected_tables:
        return text_accuracy
    predicted_tables = _page_cells(page.tables, page_index + 1)
    return (text_accuracy + table_cell_f1(expected_tables, predicted_tables)[2]) / 2


def _document_scores(truth: GroundTruth, parsed: ParsedDocument) -> dict[str, Any]:
    failures = [page for page in parsed.page_results if not page.success]
    escalation_deltas = [
        _parsed_page_accuracy(truth, page) - _parsed_page_accuracy(truth, page.previous_attempt)
        for page in parsed.page_results
        if page.previous_attempt is not None
    ]
    routed_vlm_attempts = [
        attempt
        for page in parsed.page_results
        for attempt in page.attempts
        if attempt.parser == "vlm"
    ]
    direct_vlm_pages = [
        page
        for page in parsed.page_results
        if page.parser_name == "vlm" and not page.attempts
    ]
    cer_values = [
        character_error_rate(page.expected_text, parsed.page_texts[page.page_number - 1])
        for page in truth.pages
        if page.is_ocr_page
    ]
    text_cer = [
        character_error_rate(page.expected_text, parsed.page_texts[page.page_number - 1])
        for page in truth.pages
    ]
    text_wer = [
        word_error_rate(page.expected_text, parsed.page_texts[page.page_number - 1])
        for page in truth.pages
    ]
    table_failures = []
    for page in parsed.page_results:
        expected_tables = _page_cells(truth.tables, page.page_number)
        if expected_tables and not _page_cells(page.tables, page.page_number):
            table_failures.append(
                {
                    "page": page.page_number,
                    "parser": page.parser_name,
                    "reason": "reference table present but no structured Table emitted",
                }
            )
    return {
        "document_id": truth.document_id,
        "category": truth.category,
        "cohort": (
            "original"
            if truth.category
            in {
                "clean",
                "scan",
                "receipt",
                "gst_invoice",
                "merged_table",
                "spanning_table",
                "bilingual",
            }
            and int(truth.document_id[-2:]) < 8
            else "expanded"
        ),
        "language": "hi" if any(page.language == "hi" for page in truth.pages) else "en",
        "scan_difficulty": _difficulty(truth),
        "pages": len(truth.pages),
        "table_pages": len({page for table in truth.tables for page in table.page_numbers}),
        "ocr_pages": sum(page.is_ocr_page for page in truth.pages),
        "page_durations_s": parsed.page_durations_s,
        "failed_pages": len(failures),
        "table_f1": table_cell_f1(truth.tables, parsed.tables)[2] if truth.tables else None,
        "ocr_cer": _mean(cer_values),
        "text_cer": _mean(text_cer),
        "text_wer": _mean(text_wer),
        "cheap_parser_share": cheap_parser_share(parsed.parsers),
        "latency_per_page_s": (
            latency_per_page(parsed.page_durations_s)
            if any(value > 0 for value in parsed.page_durations_s)
            else None
        ),
        "failed_page_rate": len(failures) / len(truth.pages),
        "page_accuracy": [_parsed_page_accuracy(truth, page) for page in parsed.page_results],
        "page_success": [page.success for page in parsed.page_results],
        "quality_scores": [page.quality_score for page in parsed.page_results],
        "review_flags": [bool(page.review_reasons) for page in parsed.page_results],
        "page_texts": parsed.page_texts,
        "expected_page_texts": [page.expected_text for page in truth.pages],
        "escalated_pages": len(escalation_deltas),
        "escalation_improved_pages": sum(delta > 0 for delta in escalation_deltas),
        "escalation_accuracy_deltas": escalation_deltas,
        "vlm_attempted_pages": len(routed_vlm_attempts) + len(direct_vlm_pages),
        "vlm_time_s": sum(attempt.duration_s for attempt in routed_vlm_attempts)
        + sum(page.parse_time_s for page in direct_vlm_pages),
        "vlm_uncached_pages": sum(not attempt.cache_hit for attempt in routed_vlm_attempts)
        + sum(not page.cache_hit for page in direct_vlm_pages),
        "vlm_uncached_time_s": sum(
            attempt.duration_s for attempt in routed_vlm_attempts if not attempt.cache_hit
        )
        + sum(page.parse_time_s for page in direct_vlm_pages if not page.cache_hit),
        "table_failures": table_failures,
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
    table_failures = [
        {"document_id": row["document_id"], **failure}
        for row in rows
        for failure in row["table_failures"]
    ]
    return {
        "status": "ok" if not failures else "partial_failure",
        "summary": _summarize(rows),
        "documents": rows,
        "failures": failures,
        "table_failures": table_failures,
    }


def _calibration(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [
        (score, value)
        for row in rows
        for score, value, success in zip(
            row["quality_scores"], row["page_accuracy"], row["page_success"], strict=True
        )
        if success
    ]
    scores = [score for score, _ in successful]
    accuracy = [value for _, value in successful]
    all_scores = [score for row in rows for score in row["quality_scores"]]
    all_accuracy = [value for row in rows for value in row["page_accuracy"]]
    all_flags = [flag for row in rows for flag in row["review_flags"]]
    return {
        "pages": len(scores),
        "failed_pages_excluded": sum(row["failed_pages"] for row in rows),
        "spearman_rho": spearman(scores, accuracy),
        "score_buckets": score_buckets(scores, accuracy),
        "accuracy_definition": (
            "mean of clipped normalized-text similarity and page table F1 where tables exist"
        ),
        "review_gate": review_metrics(
            all_scores,
            all_accuracy,
            all_flags,
            BAD_PAGE_ACCURACY_CUTOFF,
        ),
    }


def _adapter_configuration(adapter: PipelineAdapter) -> dict[str, object]:
    if isinstance(adapter, PlainPyMuPDF):
        return adapter.configuration()
    if isinstance(adapter, DoclingOnly):
        return adapter.configuration()
    if isinstance(adapter, UnmessParsing):
        return adapter.configuration()
    if isinstance(adapter, VLMEveryPage):
        return adapter.configuration()
    raise TypeError(f"unknown adapter: {type(adapter).__name__}")


def _bootstrap(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int | None]]:
    return {
        metric: document_bootstrap_ci(
            rows,
            metric,
            seed=BOOTSTRAP_SEED,
            samples=BOOTSTRAP_SAMPLES,
        )
        for metric in ("text_cer", "text_wer", "table_f1")
    }


def _cache_state(system_name: str, overall: dict[str, Any]) -> str:
    if system_name == "pymupdf_fixed":
        return "cache-independent (no model/response cache)"
    if system_name == "docling_only":
        return "cold parser process; local model artifacts already on disk"
    attempts = int(overall["vlm_attempted_pages"])
    misses = int(overall["vlm_uncached_pages"])
    if not attempts:
        return "no VLM pages"
    if misses == 0:
        return f"warm VLM response cache ({attempts}/{attempts} hits)"
    hits = attempts - misses
    return f"mixed VLM response cache ({hits}/{attempts} hits; {misses} misses)"


def _phase2c_headlines() -> dict[str, dict[str, Any]] | None:
    if not PHASE2C_REPORT.is_file():
        return None
    previous = json.loads(PHASE2C_REPORT.read_text(encoding="utf-8"))
    return {
        name: system["dev"]["summary"]["overall"]
        for name, system in previous["systems"].items()
        if system["dev"] is not None
    }


def run(
    dataset: Path, split: Literal["dev", "test"] = "dev", *, include_vlm_baseline: bool = True
) -> dict[str, Any]:
    freeze_commit = assert_test_ready(dataset) if split == "test" else None
    settings = _settings(split)
    truths, manifest = _validate_manifest(dataset, split)
    dataset_bytes = sum(
        (dataset / item["pdf"]).stat().st_size
        for item in manifest["documents"]
        if item["split"] == split
    )
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
            "libraries": _library_versions(),
            "models": {"vision": settings.vision_model, "prompt_version": PROMPT_VERSION},
            "thresholds_file": str(DEV_CONFIG if split == "dev" else FROZEN),
            "threshold_values": tomllib.loads(
                (DEV_CONFIG if split == "dev" else FROZEN).read_text(encoding="utf-8")
            ),
            "retrieval": "n/a: parsing stage only",
        },
        "systems": {},
        "calibration_dev": None,
        "baseline_configurations": {},
        "previous_phase2c": _phase2c_headlines() if split == "dev" else None,
    }
    splits = ("dev", "test") if split == "test" else ("dev",)
    adapters: list[PipelineAdapter] = [PlainPyMuPDF(), DoclingOnly(), UnmessParsing(settings)]
    if include_vlm_baseline:
        adapters.append(VLMEveryPage(settings))
    for adapter in adapters:
        result["baseline_configurations"][adapter.name] = _adapter_configuration(adapter)
        result["systems"][adapter.name] = {selected: None for selected in ("dev", "test")}
        for selected in splits:
            part = _run_adapter(adapter, truths, dataset, selected)
            part["bootstrap_95_ci"] = _bootstrap(part["documents"])
            part["timing_cache_state"] = _cache_state(
                adapter.name, part["summary"]["overall"]
            )
            result["systems"][adapter.name][selected] = part
            if adapter.name == UnmessParsing.name and selected == "dev":
                result["calibration_dev"] = _calibration(part["documents"])
    return result


def _format(value: Any) -> str:
    return "n/a" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)


def _hindi_loss_diffs(result: dict[str, Any]) -> list[str]:
    ours_part = result["systems"]["unmess_parsing"]["dev"]
    vlm_part = result["systems"].get("vlm_every_page", {}).get("dev")
    if ours_part is None or vlm_part is None:
        return []
    vlm_documents = {row["document_id"]: row for row in vlm_part["documents"]}
    output: list[str] = []
    for ours in ours_part["documents"]:
        if ours["language"] != "hi" or ours["document_id"] not in vlm_documents:
            continue
        vlm = vlm_documents[ours["document_id"]]
        for index, (ours_accuracy, vlm_accuracy) in enumerate(
            zip(ours["page_accuracy"], vlm["page_accuracy"], strict=True)
        ):
            if ours_accuracy >= vlm_accuracy:
                continue
            expected = ours["expected_page_texts"][index]
            output += [
                f"### {ours['document_id']} page {index + 1}",
                "",
                f"Unmess accuracy {_format(ours_accuracy)}; "
                f"VLM-only accuracy {_format(vlm_accuracy)}.",
                "",
                "Unmess versus expected:",
                "```diff",
                *difflib.unified_diff(
                    expected.splitlines(),
                    ours["page_texts"][index].splitlines(),
                    fromfile="expected",
                    tofile="unmess",
                    lineterm="",
                ),
                "```",
                "VLM-only versus expected:",
                "```diff",
                *difflib.unified_diff(
                    expected.splitlines(),
                    vlm["page_texts"][index].splitlines(),
                    fromfile="expected",
                    tofile="vlm_every_page",
                    lineterm="",
                ),
                "```",
                "",
            ]
    return output


def markdown(result: dict[str, Any]) -> str:
    meta = result["metadata"]
    lines = [
        "# Unmess Phase 2d DEV-only fairness audit",
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
        f"Threshold source: `{meta['thresholds_file']}`",
        "Threshold values: `" + json.dumps(meta["threshold_values"], sort_keys=True) + "`",
        "",
        "## Exact system configurations",
        "",
        "```json",
        json.dumps(result["baseline_configurations"], indent=2, sort_keys=True),
        "```",
        "",
        "Phase 2d fairness changes: PyMuPDF now attempts structured extraction with "
        "`page.find_tables()`; Docling changed from its default RapidOCR path to forced "
        "full-page EasyOCR with explicit English and Hindi; and VLM-only cached Markdown "
        "tables are parsed through the same `Table` contract as routed VLM output. "
        "No VLM model request was made for this audit.",
        "",
        "The merged-heading geometry is generated by `scripts/make_synthetic_docs.py`, not "
        "hand-edited ground truth. DEV and test PDFs were regenerated by that generator, and "
        "the integration test verified their bytes and SHA-256 values against MANIFEST.json "
        "without evaluating test outcomes.",
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
                ("cohort", summary["by_cohort"]),
                ("category", summary["by_category"]),
                ("language", summary["by_language"]),
                ("scan", summary["by_scan_difficulty"]),
            )
            for group_type, entries in groups:
                for group, row in entries.items():
                    lines.append(
                        f"| {name} | {group_type}:{group} | {row['documents']} | "
                        f"{row['pages']} | {row['failed_pages']} | "
                        + " | ".join(
                            f"{_format(row[column])} "
                            f"(d={row['metric_counts'][column]['documents']},"
                            f"p={row['metric_counts'][column]['pages']})"
                            for column in columns
                        )
                        + " |"
                    )
    calibration = result["calibration_dev"]
    if calibration:
        gate = calibration["review_gate"]
        lines += [
            "",
            "## DEV quality score and review-gate evaluation",
            "",
            f"Spearman rho: {_format(calibration['spearman_rho'])} "
            f"over {calibration['pages']} successfully parsed pages; "
            f"{calibration['failed_pages_excluded']} failed pages excluded.",
            f"Page accuracy: {calibration['accuracy_definition']}.",
            "Exact composite: after whitespace normalization, text_accuracy = "
            "max(0, 1 - CER); pages without a reference table use text_accuracy, while "
            "table pages use 0.5 * text_accuracy + 0.5 * page table-cell F1.",
            f"Locked bad-page rule: composite accuracy < "
            f"{_format(gate['bad_page_cutoff'])}. Bad pages: {gate['bad_pages']} / "
            f"{gate['pages']}; good pages: {gate['good_pages']} / {gate['pages']}.",
            f"Review detection AUROC: {_format(gate['auroc'])}; precision: "
            f"{_format(gate['precision'])}; recall: {_format(gate['recall'])}.",
            f"Confusion counts: TP={gate['true_positive']}, FP={gate['false_positive']}, "
            f"FN={gate['false_negative']}, TN={gate['true_negative']}.",
            (
                "**UNSTABLE:** fewer than 10 bad pages; AUROC, precision, and recall "
                "have high sampling uncertainty."
                if gate["unstable"]
                else "Stability flag: at least 10 bad pages observed."
            ),
            "",
            "| Score bucket | Pages | Mean page accuracy |",
            "|---|---:|---:|",
        ]
        for bucket, values in calibration["score_buckets"].items():
            lines.append(
                f"| {bucket} | {values['pages']} | {_format(values['mean_page_accuracy'])} |"
            )
    lines += [
        "",
        "## Document-bootstrap 95% confidence intervals",
        "",
        f"Fixed seed `{BOOTSTRAP_SEED}`; {BOOTSTRAP_SAMPLES} document-resampling draws. "
        "Intervals are percentile intervals and may be wide on this small DEV corpus.",
        "",
        "| System | Metric | Estimate | 95% CI | Documents | Applicable pages |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for name, system in result["systems"].items():
        part = system["dev"]
        if part is None:
            continue
        overall = part["summary"]["overall"]
        for metric in ("text_cer", "text_wer", "table_f1"):
            interval = part["bootstrap_95_ci"][metric]
            count = overall["metric_counts"][metric]
            lines.append(
                f"| {name} | {metric} | {_format(overall[metric])} | "
                f"[{_format(interval['lower'])}, {_format(interval['upper'])}] | "
                f"{count['documents']} | {count['pages']} |"
            )
    for selected in ("test", "dev"):
        part = result["systems"]["unmess_parsing"][selected]
        if part is None:
            continue
        overall = part["summary"]["overall"]
        lines += [
            "",
            f"## {selected.title()} VLM cost and escalation",
            "",
            f"VLM attempts: {overall['vlm_attempted_pages']} pages in "
            f"{_format(overall['vlm_time_s'])} s "
            f"({_format(overall['vlm_pages_per_second'])} pages/s).",
            f"Uncached VLM: {overall['vlm_uncached_pages']} pages in "
            f"{_format(overall['vlm_uncached_time_s'])} s "
            f"({_format(overall['vlm_uncached_pages_per_second'])} pages/s).",
            f"Escalated: {overall['escalated_pages']} pages; "
            f"accuracy improved on {overall['escalation_improved_pages']}; "
            f"mean accuracy delta {_format(overall['mean_escalation_accuracy_delta'])}.",
        ]
    lines += ["", "## Timing with cache state", ""]
    lines += [
        "| System | Cache state | DEV pages | Total parser time (s) | s/page |",
        "|---|---|---:|---:|---:|",
    ]
    for name, system in result["systems"].items():
        part = system["dev"]
        if part is None:
            continue
        overall = part["summary"]["overall"]
        lines.append(
            f"| {name} | {part['timing_cache_state']} | {overall['pages']} | "
            f"{_format(overall['total_time_s'])} | "
            f"{_format(overall['total_time_s'] / overall['pages'])} |"
        )
    lines += [
        "",
        "Only cache-independent or genuinely cold-cache measurements may support a timing "
        "comparison. Warm/mixed rows are operational measurements and are not ranked against "
        "cold rows.",
    ]
    previous = result.get("previous_phase2c")
    if previous:
        lines += [
            "",
            "## Numbers moved since Phase 2c",
            "",
            "Positive deltas mean the numeric value increased; for CER/WER an increase is "
            "worse, while for table F1 it is better.",
            "",
            "| System | Metric | Phase 2c | Phase 2d | Delta |",
            "|---|---|---:|---:|---:|",
        ]
        for name, system in result["systems"].items():
            part = system["dev"]
            if part is None or name not in previous:
                continue
            current = part["summary"]["overall"]
            for metric in ("text_cer", "text_wer", "table_f1", "failed_pages"):
                old_value = previous[name].get(metric)
                new_value = current.get(metric)
                if old_value is None or new_value is None:
                    delta = None
                else:
                    delta = float(new_value) - float(old_value)
                lines.append(
                    f"| {name} | {metric} | {_format(old_value)} | "
                    f"{_format(new_value)} | {_format(delta)} |"
                )
    ours_part = result["systems"]["unmess_parsing"]["dev"]
    if ours_part is not None:
        lines += [
            "",
            "## Where Unmess loses on DEV",
            "",
            "Lower CER is better; higher table F1 and page accuracy are better. "
            "Latency and accuracy must be judged together; cache-warmed VLM time "
            "is not a cold-run cost estimate.",
            "",
        ]
        any_loss = False
        for category, ours in ours_part["summary"]["by_category"].items():
            for name, system in result["systems"].items():
                if name == "unmess_parsing" or system["dev"] is None:
                    continue
                baseline = system["dev"]["summary"]["by_category"].get(category)
                if baseline is None:
                    continue
                losses = [
                    metric
                    for metric, higher_is_better in (
                        ("table_f1", True),
                        ("text_cer", False),
                        ("text_wer", False),
                        ("mean_page_accuracy", True),
                    )
                    if ours[metric] is not None
                    and baseline[metric] is not None
                    and (
                        ours[metric] < baseline[metric] - 1e-6
                        if higher_is_better
                        else ours[metric] > baseline[metric] + 1e-6
                    )
                ]
                if losses:
                    any_loss = True
                    lines.append(f"- {category} vs {name}: {', '.join(losses)}.")
        if not any_loss:
            lines.append("No measured accuracy loss by category on this DEV corpus.")
        if "vlm_every_page" in result["systems"]:
            vlm_part = result["systems"]["vlm_every_page"]["dev"]
            if vlm_part is not None:
                ours = ours_part["summary"]["overall"]
                vlm = vlm_part["summary"]["overall"]
                accuracy_relation = (
                    "lower"
                    if ours["mean_page_accuracy"] < vlm["mean_page_accuracy"]
                    else "higher or equal"
                )
                lines.append(
                    f"Unmess overall page accuracy is {accuracy_relation} than VLM-only, "
                    "but no accuracy-vs-cost winner is claimed: Unmess and VLM-only used "
                    "warm/mixed response caches, so their timings are not cold-cache costs."
                )
    hindi_diffs = _hindi_loss_diffs(result)
    lines += [
        "",
        "## Hindi pages where Unmess loses to VLM-only",
        "",
        "The VLM prompt asks for every visible word and preserves the returned Markdown; "
        "cached outputs demonstrate that it can return Devanagari. The loss is therefore "
        "not attributed to a VLM language-configuration error.",
        "",
    ]
    lines += hindi_diffs or ["No Hindi page had lower Unmess composite accuracy.", ""]
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
    lines += ["", "## Structured-table extraction failures", ""]
    table_failures_found = False
    for split in ("test", "dev"):
        for name, system in result["systems"].items():
            part = system[split]
            if part is None:
                continue
            for failure in part["table_failures"]:
                table_failures_found = True
                lines.append(
                    f"- {split} / {name} / {failure['document_id']} page "
                    f"{failure['page']}: {failure['reason']} ({failure['parser']})."
                )
    if not table_failures_found:
        lines.append("None.")
    lines += [
        "",
        "Metric cells show their own document and page denominators. "
        "Means are document-weighted; time is measured end-to-end in each adapter. "
        "Cache state is reported per system above. Warm and mixed measurements are not used "
        "to claim a timing advantage over cold measurements.",
        "See EVAL.md for metric definitions and dataset limits.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--dataset", type=Path, default=ROOT / "eval/datasets")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "eval/results")
    parser.add_argument("--skip-vlm-baseline", action="store_true")
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--archive-dev", action="store_true")
    args = parser.parse_args()
    if args.render_only:
        result = json.loads((args.output_dir / "latest.json").read_text())
        result["metadata"]["libraries"] = _library_versions()
        (args.output_dir / "latest.json").write_text(json.dumps(result, indent=2) + "\n")
        report = markdown(result)
        (args.output_dir / "latest.md").write_text(report)
        if args.archive_dev:
            if result["systems"]["unmess_parsing"]["test"] is not None:
                raise RuntimeError("cannot archive test results as a DEV report")
            (args.output_dir / "phase2d-dev.md").write_text(report)
            (args.output_dir / "phase2d-dev.json").write_text(json.dumps(result, indent=2) + "\n")
        return
    result = run(args.dataset, args.split, include_vlm_baseline=not args.skip_vlm_baseline)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "latest.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output_dir / "latest.md").write_text(markdown(result))
    print(
        f"Evaluated {args.split} split; Unmess parsing failures: "
        f"{result['systems']['unmess_parsing'][args.split]['summary']['overall']['failed_pages']}"
    )


if __name__ == "__main__":
    main()
