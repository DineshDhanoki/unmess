"""Run the same synthetic corpus through each available baseline."""

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from eval.baselines.base import ParsedDocument, PipelineAdapter
from eval.baselines.bm25 import rank_bm25
from eval.baselines.docling_only import DoclingOnly
from eval.baselines.plain_pymupdf import PlainPyMuPDF
from eval.baselines.unmess_pending import UnmessPending
from eval.metrics.chunk_integrity import table_split_rate
from eval.metrics.citation_accuracy import citation_accuracy, is_relevant
from eval.metrics.latency import latency_per_page
from eval.metrics.ocr_cer import character_error_rate
from eval.metrics.retrieval_recall import recall_at_k, reciprocal_rank
from eval.metrics.routing_efficiency import cheap_parser_share
from eval.metrics.table_f1 import table_cell_f1
from unmess.models import Answer, Chunk, GroundTruth

ROOT = Path(__file__).resolve().parents[1]
METRICS = (
    "table_f1",
    "ocr_cer",
    "recall_at_1",
    "recall_at_3",
    "mrr",
    "table_split_rate",
    "citation_accuracy",
    "cheap_parser_share",
    "latency_per_page_s",
)


def _git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=False, capture_output=True, text=True
    ).stdout.strip()


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
    return {"documents": len(rows), **{key: _mean([row[key] for row in rows]) for key in METRICS}}


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    languages: dict[str, list[dict[str, Any]]] = defaultdict(list)
    difficulties: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        categories[row["category"]].append(row)
        languages[row["language"]].append(row)
        difficulties[row["scan_difficulty"]].append(row)
    return {
        "overall": _aggregate(rows),
        "by_category": {key: _aggregate(value) for key, value in sorted(categories.items())},
        "by_language": {key: _aggregate(value) for key, value in sorted(languages.items())},
        "by_scan_difficulty": {
            key: _aggregate(value) for key, value in sorted(difficulties.items())
        },
    }


def _document_scores(
    truth: GroundTruth, parsed: ParsedDocument, all_chunks: list[Chunk]
) -> dict[str, Any]:
    retrieval: list[tuple[float, float, float, float]] = []
    for question in truth.questions:
        ranked = rank_bm25(question.question, all_chunks)

        def relevant(chunk: Chunk, answer: Answer = question) -> bool:
            return chunk.doc_id == truth.document_id and is_relevant(chunk, answer)

        first = ranked[0] if ranked else None
        citation = (
            citation_accuracy(question, first.page_numbers, first.bboxes)
            if first is not None and first.doc_id == truth.document_id
            else 0.0
        )
        retrieval.append(
            (
                recall_at_k(ranked, relevant, 1),
                recall_at_k(ranked, relevant, 3),
                reciprocal_rank(ranked, relevant),
                citation,
            )
        )
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
        "table_f1": table_cell_f1(truth.tables, parsed.tables)[2] if truth.tables else None,
        "ocr_cer": _mean(cer_values),
        "recall_at_1": _mean([item[0] for item in retrieval]),
        "recall_at_3": _mean([item[1] for item in retrieval]),
        "mrr": _mean([item[2] for item in retrieval]),
        "table_split_rate": table_split_rate(truth.tables, parsed.chunks),
        "citation_accuracy": _mean([item[3] for item in retrieval]),
        "cheap_parser_share": cheap_parser_share(parsed.parsers),
        "latency_per_page_s": latency_per_page(parsed.page_durations_s),
    }


def _run_adapter(
    adapter: PipelineAdapter, truths: list[GroundTruth], dataset: Path
) -> dict[str, Any]:
    parsed: dict[str, ParsedDocument] = {}
    errors: list[dict[str, str]] = []
    for truth in truths:
        try:
            parsed[truth.document_id] = adapter.parse(
                dataset / truth.source_file, truth.document_id
            )
        except Exception as exc:
            errors.append(
                {"document_id": truth.document_id, "error": f"{type(exc).__name__}: {exc}"}
            )
    if not parsed:
        return {"status": "failed", "errors": errors, "dev": None, "test": None}
    output: dict[str, Any] = {"status": "ok" if not errors else "partial", "errors": errors}
    for split in ("dev", "test"):
        selected = [
            truth for truth in truths if truth.split == split and truth.document_id in parsed
        ]
        all_chunks = [chunk for truth in selected for chunk in parsed[truth.document_id].chunks]
        rows = [
            _document_scores(truth, parsed[truth.document_id], all_chunks) for truth in selected
        ]
        output[split] = {"summary": _summarize(rows), "documents": rows}
    return output


def run(dataset: Path) -> dict[str, Any]:
    truths, manifest = _validate_manifest(dataset)
    dataset_bytes = sum((dataset / item["pdf"]).stat().st_size for item in manifest["documents"])
    result: dict[str, Any] = {
        "metadata": {
            "run_date_utc": datetime.now(UTC).isoformat(),
            "git_commit": _git(["rev-parse", "HEAD"]),
            "working_tree_dirty": bool(_git(["status", "--porcelain"])),
            "generator_version": manifest["generator_version"],
            "seed": manifest["seed"],
            "dataset_documents": len(truths),
            "dataset_pdf_bytes": dataset_bytes,
            "font_sha256": manifest["font_sha256"],
            "python": platform.python_version(),
            "platform": platform.platform(),
            "libraries": {
                name: version(name) for name in ("pymupdf", "reportlab", "pillow", "pydantic")
            },
            "models": {"text": "n/a", "vision": "n/a", "embedding": "n/a"},
            "retrieval": "in-memory BM25",
        },
        "systems": {},
    }
    result["systems"][PlainPyMuPDF.name] = _run_adapter(PlainPyMuPDF(), truths, dataset)
    if DoclingOnly.available():
        result["systems"][DoclingOnly.name] = _run_adapter(DoclingOnly(), truths, dataset)
    else:
        result["systems"][DoclingOnly.name] = {
            "status": "skipped: optional dependency not installed",
            "dev": None,
            "test": None,
        }
    result["systems"][UnmessPending.name] = {
        "status": "not implemented yet",
        "dev": None,
        "test": None,
    }
    return result


def _format(value: Any) -> str:
    return "n/a" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)


def markdown(result: dict[str, Any]) -> str:
    meta = result["metadata"]
    lines = [
        "# Unmess evaluation report",
        "",
        f"Run: {meta['run_date_utc']} | Git: `{meta['git_commit']}` "
        f"| dirty: {meta['working_tree_dirty']}",
        f"Dataset: {meta['dataset_documents']} PDFs, {meta['dataset_pdf_bytes']} bytes; "
        f"generator {meta['generator_version']}, seed {meta['seed']}",
        f"Python {meta['python']}; libraries: "
        + ", ".join(f"{k} {v}" for k, v in meta["libraries"].items()),
        f"Platform: {meta['platform']}; font SHA-256: `{meta['font_sha256']}`",
        "Models: none used. Retrieval: in-memory BM25.",
        "",
        "Test is the headline split. Dev is for threshold tuning only.",
    ]
    columns = (
        "table_f1",
        "ocr_cer",
        "recall_at_1",
        "recall_at_3",
        "mrr",
        "table_split_rate",
        "citation_accuracy",
        "cheap_parser_share",
        "latency_per_page_s",
    )
    for split in ("test", "dev"):
        lines += [
            "",
            f"## {split.title()} results",
            "",
            "| System | Group | Documents | " + " | ".join(columns) + " |",
            "|---|---|---:|" + "---:|" * len(columns),
        ]
        for system_name, system in result["systems"].items():
            if system[split] is None:
                lines.append(
                    f"| {system_name} ({system['status']}) | overall | n/a | "
                    + " | ".join("n/a" for _ in columns)
                    + " |"
                )
                continue
            summary = system[split]["summary"]
            for group_name, groups in (
                ("overall", {"overall": summary["overall"]}),
                ("category", summary["by_category"]),
                ("language", summary["by_language"]),
                ("scan", summary["by_scan_difficulty"]),
            ):
                for key, row in groups.items():
                    lines.append(
                        f"| {system_name} | {group_name}:{key} | {row['documents']} | "
                        + " | ".join(_format(row[col]) for col in columns)
                        + " |"
                    )
    lines += ["", "Metric definitions and limitations: see EVAL.md.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT / "eval/datasets")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "eval/results")
    args = parser.parse_args()
    result = run(args.dataset)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "latest.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output_dir / "latest.md").write_text(markdown(result))
    print(markdown(result).split("## Test results")[0].strip())


if __name__ == "__main__":
    main()
