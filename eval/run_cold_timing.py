"""Controlled, sequential Phase 2e DEV cold-cache timing run."""

import argparse
import contextlib
import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

from eval.baselines.base import ParsedDocument, PipelineAdapter
from eval.baselines.docling_only import DoclingDefault, DoclingOnly
from eval.baselines.plain_pymupdf import PlainPyMuPDF
from eval.baselines.unmess_parsing import UnmessParsing
from eval.baselines.vlm_every_page import VLMEveryPage
from eval.run_eval import (
    ROOT,
    _bootstrap,
    _document_scores,
    _failed_document,
    _settings,
    _summarize,
    _validate_manifest,
)
from unmess.config import Settings
from unmess.models import GroundTruth
from unmess.parsing.vlm_parser import PROMPT_VERSION, VLMParser

SYSTEM_ORDER = (
    "pymupdf_fixed",
    "docling_default",
    "docling_only",
    "unmess_parsing",
    "vlm_every_page",
)


def _command(args: list[str]) -> str:
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    return result.stdout.strip() or result.stderr.strip() or "unavailable"


def _hardware(settings: Settings) -> dict[str, Any]:
    url = str(settings.ollama_url).rstrip("/")
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{url}/api/version")
        response.raise_for_status()
        ollama_version = response.json().get("version", "unknown")
    power = _command(["pmset", "-g", "batt"])
    if "AC Power" not in power:
        raise RuntimeError("cold timing requires AC power")
    return {
        "machine": _command(["sysctl", "-n", "hw.model"]),
        "chip": _command(["sysctl", "-n", "machdep.cpu.brand_string"]),
        "memory_bytes": _command(["sysctl", "-n", "hw.memsize"]),
        "os": platform.platform(),
        "python": platform.python_version(),
        "ollama_version": ollama_version,
        "model_tag": settings.vision_model,
        "power": power,
        "process_snapshot": _command(["ps", "-Ao", "pid,pcpu,comm", "-r"]).splitlines()[:8],
        "thermal_throttling": "not instrumented; retained as a timing limitation",
    }


def _warm_model(settings: Settings, cache_root: Path) -> float:
    warm_settings = settings.model_copy(update={"vision_cache_dir": cache_root / "warmup"})
    started = perf_counter()
    page = VLMParser(warm_settings).parse_page(ROOT / "eval/datasets/pdf/synthetic-clean-00.pdf", 1)
    elapsed = perf_counter() - started
    if not page.success:
        raise RuntimeError(f"vision warm-up failed: {page.error}")
    return elapsed


def _adapter(
    name: str, settings: Settings, cache_root: Path
) -> tuple[PipelineAdapter, Path | None]:
    if name == "pymupdf_fixed":
        return PlainPyMuPDF(), None
    if name == "docling_default":
        return DoclingDefault(), None
    if name == "docling_only":
        return DoclingOnly(), None
    cache = cache_root / name
    cache.mkdir(parents=True, exist_ok=False)
    isolated = settings.model_copy(update={"vision_cache_dir": cache, "vision_cache_reads": False})
    if name == "unmess_parsing":
        return UnmessParsing(isolated), cache
    if name == "vlm_every_page":
        return VLMEveryPage(isolated), cache
    raise ValueError(name)


def _cache_hits(parsed: ParsedDocument) -> int:
    return sum(page.parser_name == "vlm" and page.cache_hit for page in parsed.page_results)


def _run_system(
    adapter: PipelineAdapter,
    truths: list[GroundTruth],
    dataset: Path,
    progress: Any,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    cache_hits = 0
    started = perf_counter()
    for index, truth in enumerate(truths, 1):
        document_started = perf_counter()
        try:
            parsed = adapter.parse(dataset / truth.source_file, truth.document_id)
            if len(parsed.page_results) != len(truth.pages):
                raise ValueError("adapter omitted page outcomes")
        except Exception as exc:
            parsed = _failed_document(truth, f"{type(exc).__name__}: {exc}")
        cache_hits += _cache_hits(parsed)
        row = _document_scores(truth, parsed)
        rows.append(row)
        failures.extend(
            {"document_id": truth.document_id, **failure} for failure in row["failures"]
        )
        progress.write(
            json.dumps(
                {
                    "event": "document_complete",
                    "system": adapter.name,
                    "document": truth.document_id,
                    "index": index,
                    "total": len(truths),
                    "elapsed_s": perf_counter() - document_started,
                    "failures": row["failed_pages"],
                }
            )
            + "\n"
        )
        progress.flush()
    elapsed = perf_counter() - started
    return {
        "wall_time_s": elapsed,
        "seconds_per_page": elapsed / sum(len(truth.pages) for truth in truths),
        "cache_hits": cache_hits,
        "cold_valid": cache_hits == 0,
        "summary": _summarize(rows),
        "bootstrap_95_ci": _bootstrap(rows),
        "failures": failures,
    }


def _markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 2e DEV cold-cache timing",
        "",
        f"Run: {result['run_date_utc']}; order: `{' -> '.join(result['system_order'])}`.",
        f"Vision model `{result['hardware']['model_tag']}`; Ollama "
        f"`{result['hardware']['ollama_version']}`; prompt `{PROMPT_VERSION}`.",
        f"Hardware: {result['hardware']['machine']}; {result['hardware']['chip']}; "
        f"memory {result['hardware']['memory_bytes']} bytes; OS {result['hardware']['os']}.",
        f"Power check: `{result['hardware']['power']}`.",
        f"Vision warm-up/load time, excluded from system timing: "
        f"{result['vision_warmup_s']:.4f} s.",
        "Each VLM-using system had its own newly created empty response-cache directory and "
        "cache reads were disabled. A nonzero cache-hit count invalidates that system's cold "
        "timing. Retry time is included.",
        "",
        "| System | Pages | Total COLD s | COLD s/page | Cache hits | Valid | "
        "Failures | CER | WER | Table F1 | Page accuracy |",
        "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for name in result["system_order"]:
        system = result["systems"][name]
        overall = system["summary"]["overall"]
        table_f1 = "n/a" if overall["table_f1"] is None else f"{overall['table_f1']:.4f}"
        lines.append(
            f"| {name} | {overall['pages']} | {system['wall_time_s']:.4f} | "
            f"{system['seconds_per_page']:.4f} | {system['cache_hits']} | "
            f"{system['cold_valid']} | {overall['failed_pages']} | "
            f"{overall['text_cer']:.4f} | {overall['text_wer']:.4f} | {table_f1} | "
            f"{overall['mean_page_accuracy']:.4f} |"
        )
    lines += [
        "",
        "Only one pass was run because the pre-run estimate for two sequential passes exceeded "
        "45 minutes. No result from one system populated another system's cache.",
        "Each VLM cache started with zero files; post-run file counts are recorded in JSON.",
        f"Thermal limitation: {result['hardware']['thermal_throttling']}.",
        "",
        "## Failures",
        "",
    ]
    found = False
    for name in result["system_order"]:
        for failure in result["systems"][name]["failures"]:
            found = True
            lines.append(
                f"- {name} / {failure['document_id']} page {failure['page']}: "
                f"{str(failure['error']).replace(chr(10), ' ')[:240]}"
            )
    if not found:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--dataset", type=Path, default=ROOT / "eval/datasets")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "eval/results")
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=ROOT / ".cache/unmess/cold" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
    )
    parser.add_argument(
        "--progress-log", type=Path, default=ROOT / ".cache/unmess/phase2e-cold-progress.log"
    )
    args = parser.parse_args()
    if args.render_only:
        rendered_result: dict[str, Any] = json.loads(
            (args.output_dir / "phase2e-cold.json").read_text(encoding="utf-8")
        )
        (args.output_dir / "phase2e-cold.md").write_text(
            _markdown(rendered_result), encoding="utf-8"
        )
        return
    if args.cache_root.exists():
        raise RuntimeError(f"cold cache root already exists: {args.cache_root}")
    args.cache_root.mkdir(parents=True)
    args.progress_log.parent.mkdir(parents=True, exist_ok=True)
    settings = _settings("dev")
    truths, _manifest = _validate_manifest(args.dataset, "dev")
    result: dict[str, Any] = {
        "run_date_utc": datetime.now(UTC).isoformat(),
        "system_order": list(SYSTEM_ORDER),
        "hardware": _hardware(settings),
        "timing_controls": {
            "caffeinate": os.environ.get("UNMESS_CAFFEINATE") == "1",
            "sequential": True,
            "isolated_response_caches": True,
            "response_cache_reads": False,
            "runs": 1,
        },
        "systems": {},
    }
    if not result["timing_controls"]["caffeinate"]:
        raise RuntimeError("run through caffeinate with UNMESS_CAFFEINATE=1")
    with (
        args.progress_log.open("w", encoding="utf-8", buffering=1) as progress,
        contextlib.redirect_stdout(progress),
        contextlib.redirect_stderr(progress),
    ):
        result["vision_warmup_s"] = _warm_model(settings, args.cache_root)
        for name in SYSTEM_ORDER:
            adapter, cache = _adapter(name, settings, args.cache_root)
            progress.write(json.dumps({"event": "system_start", "system": name}) + "\n")
            progress.flush()
            system = _run_system(adapter, truths, args.dataset, progress)
            system["cache_directory"] = str(cache) if cache is not None else None
            system["cache_files_before"] = 0 if cache is not None else None
            system["cache_files_after"] = (
                sum(1 for item in cache.rglob("*") if item.is_file()) if cache is not None else None
            )
            result["systems"][name] = system
            progress.write(
                json.dumps(
                    {
                        "event": "system_complete",
                        "system": name,
                        "wall_time_s": system["wall_time_s"],
                        "cache_hits": system["cache_hits"],
                        "cold_valid": system["cold_valid"],
                    }
                )
                + "\n"
            )
            progress.flush()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "phase2e-cold.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output_dir / "phase2e-cold.md").write_text(_markdown(result))


if __name__ == "__main__":
    main()
