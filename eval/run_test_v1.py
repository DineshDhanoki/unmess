"""One-shot, frozen Phase 2 test runner with resumable raw artifacts."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import signal
import subprocess
import time
import tomllib
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
import pymupdf

from eval.baselines.base import ParsedDocument, PipelineAdapter
from eval.baselines.docling_only import DoclingDefault, DoclingOnly
from eval.baselines.plain_pymupdf import PlainPyMuPDF
from eval.baselines.unmess_parsing import UnmessParsing
from eval.baselines.vlm_every_page import VLMEveryPage
from eval.report_test_v1 import generate_report
from eval.run_eval import (
    BAD_PAGE_ACCURACY_CUTOFF,
    BOOTSTRAP_SAMPLES,
    BOOTSTRAP_SEED,
    ROOT,
    _adapter_configuration,
    _bootstrap,
    _document_scores,
    _failed_document,
    _summarize,
    _validate_manifest,
)
from unmess.config import Settings
from unmess.models import GroundTruth
from unmess.parsing.vlm_parser import PROMPT_VERSION

FREEZE_TAG = "freeze-v1"
FROZEN_CONFIG = ROOT / "eval/config/test_v1_frozen.toml"
DATASET = ROOT / "eval/datasets"
RESULT_ROOT = ROOT / "eval/results/test-v1"
STATE_PATH = RESULT_ROOT / "run-state.json"
PROGRESS_LOG = ROOT / ".cache/unmess/test-v1-progress.log"
CACHE_ROOT = ROOT / ".cache/unmess/test-v1"
SYSTEM_ORDER = (
    "pymupdf_fixed",
    "docling_default",
    "docling_only",
    "unmess_parsing",
    "vlm_every_page",
)


class InfrastructureFailure(RuntimeError):
    """A fixed-category failure that permits at most one identical rerun."""


def _git(args: list[str], *, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=not binary,
    )


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_config(path: Path = FROZEN_CONFIG) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _tracked_files_at_tag(tag: str, frozen_paths: list[str]) -> set[str]:
    result = _git(["ls-tree", "-r", "--name-only", tag, "--", *frozen_paths])
    if result.returncode:
        raise RuntimeError("freeze tag cannot enumerate frozen files")
    return {line for line in result.stdout.splitlines() if line}


def _tracked_files_now(frozen_paths: list[str]) -> set[str]:
    result = _git(["ls-files", "--", *frozen_paths])
    if result.returncode:
        raise RuntimeError("working tree cannot enumerate frozen files")
    return {line for line in result.stdout.splitlines() if line}


def verify_freeze(config: dict[str, Any]) -> str:
    """Verify tag ancestry, cleanliness, allowed history, and frozen file hashes."""
    tag = str(config["freeze"]["tag"])
    if tag != FREEZE_TAG:
        raise RuntimeError("frozen config names an unexpected tag")
    resolved = _git(["rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"])
    if resolved.returncode:
        raise RuntimeError("freeze-v1 tag does not exist")
    freeze_commit = str(resolved.stdout).strip()
    ancestor = _git(["merge-base", "--is-ancestor", freeze_commit, "HEAD"])
    if ancestor.returncode:
        raise RuntimeError("HEAD is not at or descended from freeze-v1")
    status = _git(["status", "--porcelain", "--untracked-files=all"])
    if status.returncode or status.stdout.strip():
        raise RuntimeError("working tree must be clean")

    frozen_paths = [str(path) for path in config["freeze"]["frozen_paths"]]
    tagged = _tracked_files_at_tag(tag, frozen_paths)
    current = _tracked_files_now(frozen_paths)
    if tagged != current:
        raise RuntimeError("frozen file set differs from freeze-v1")
    for relative in sorted(tagged):
        tagged_blob = _git(["show", f"{tag}:{relative}"], binary=True)
        if tagged_blob.returncode:
            raise RuntimeError(f"cannot read frozen tagged blob: {relative}")
        working_hash = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        tagged_hash = hashlib.sha256(tagged_blob.stdout).hexdigest()
        if working_hash != tagged_hash:
            raise RuntimeError(f"frozen file hash differs from freeze-v1: {relative}")

    changed = _git(["diff", "--name-only", f"{freeze_commit}..HEAD"])
    if changed.returncode:
        raise RuntimeError("cannot inspect commits after freeze-v1")
    allowed = tuple(str(path).rstrip("/") + "/" for path in config["freeze"]["allowed_docs"])
    allowed_files = {"README.md"}
    for relative in changed.stdout.splitlines():
        if relative in tagged:
            continue
        if relative not in allowed_files and not relative.startswith(allowed):
            raise RuntimeError(f"post-freeze non-documentation change is not allowed: {relative}")
    return freeze_commit


def _settings(config: dict[str, Any], cache: Path) -> Settings:
    values = dict(config["settings"])
    values.update({"vision_cache_dir": cache, "vision_cache_reads": False})
    return Settings(**values)


def _under_caffeinate() -> bool:
    result = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,comm="], check=False, capture_output=True, text=True
    )
    if result.returncode:
        return False
    processes: dict[int, tuple[int, str]] = {}
    for line in result.stdout.splitlines():
        fields = line.split(maxsplit=2)
        if len(fields) == 3:
            processes[int(fields[0])] = (int(fields[1]), fields[2])
    pid = os.getpid()
    while pid in processes:
        parent, command = processes[pid]
        if Path(command).name == "caffeinate":
            return True
        pid = parent
    return False


def _adapter(name: str, settings: Settings) -> PipelineAdapter:
    if name == "pymupdf_fixed":
        return PlainPyMuPDF()
    if name == "docling_default":
        return DoclingDefault()
    if name == "docling_only":
        return DoclingOnly()
    if name == "unmess_parsing":
        return UnmessParsing(settings)
    if name == "vlm_every_page":
        return VLMEveryPage(settings)
    raise ValueError(name)


def _cache_hits(parsed: ParsedDocument) -> int:
    direct = sum(page.parser_name == "vlm" and page.cache_hit for page in parsed.page_results)
    routed = sum(
        attempt.parser == "vlm" and attempt.cache_hit
        for page in parsed.page_results
        for attempt in page.attempts
    )
    return direct + routed


def _ollama_version(settings: Settings) -> str:
    url = str(settings.ollama_url).rstrip("/")
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{url}/api/version")
            response.raise_for_status()
            return str(response.json().get("version", "unknown"))
    except Exception as exc:
        raise InfrastructureFailure("ollama_unavailable") from exc


def _ollama_health_check(settings: Settings) -> Callable[[], None]:
    def check() -> None:
        _ollama_version(settings)

    return check


def _preload_model(settings: Settings) -> float:
    """Load and verify the frozen model, excluding this call from system timings."""
    url = str(settings.ollama_url).rstrip("/")
    started = perf_counter()
    try:
        with pymupdf.open(ROOT / "eval/datasets/pdf/synthetic-clean-00.pdf") as document:
            image = base64.b64encode(document[0].get_pixmap(dpi=72, alpha=False).tobytes("png"))
        with httpx.Client(timeout=settings.vision_timeout_s) as client:
            show = client.post(f"{url}/api/show", json={"model": settings.vision_model})
            show.raise_for_status()
            response = client.post(
                f"{url}/api/generate",
                json={
                    "model": settings.vision_model,
                    "prompt": "Verify vision input and reply with OK.",
                    "images": [image.decode("ascii")],
                    "stream": False,
                    "keep_alive": "1h",
                    "options": {"num_predict": 8, "temperature": 0},
                },
            )
            response.raise_for_status()
            if not str(response.json().get("response", "")).strip():
                raise InfrastructureFailure("vision_model_verification_failed")
    except InfrastructureFailure:
        raise
    except Exception as exc:
        raise InfrastructureFailure("ollama_unavailable") from exc
    return perf_counter() - started


class _SleepGuard:
    def __init__(self) -> None:
        self.wall = time.time()
        self.monotonic = time.monotonic()

    def checkpoint(self) -> None:
        wall_now = time.time()
        monotonic_now = time.monotonic()
        if (wall_now - self.wall) - (monotonic_now - self.monotonic) > 5.0:
            raise InfrastructureFailure("system_sleep_detected")
        self.wall = wall_now
        self.monotonic = monotonic_now


def _run_system(
    adapter: PipelineAdapter,
    truths: list[GroundTruth],
    dataset: Path,
    progress: Callable[[dict[str, object]], None],
    check_ollama: Callable[[], None] | None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    table_failures: list[dict[str, Any]] = []
    cache_hits = 0
    sleep_guard = _SleepGuard()
    started = perf_counter()
    for index, truth in enumerate(truths, 1):
        try:
            parsed = adapter.parse(dataset / truth.source_file, truth.document_id)
            if len(parsed.page_results) != len(truth.pages):
                raise ValueError("adapter omitted page outcomes")
        except Exception as exc:
            parsed = _failed_document(truth, f"{type(exc).__name__}: {exc}")
        cache_hits += _cache_hits(parsed)
        row = _document_scores(truth, parsed)
        row["raw_pages"] = [
            {
                "page": page.page_number,
                "parser": page.parser_name,
                "success": page.success,
                "error": page.error,
                "duration_s": parsed.page_durations_s[page.page_number - 1],
                "extracted_text": parsed.page_texts[page.page_number - 1],
                "expected_text": truth.pages[page.page_number - 1].expected_text,
                "quality_score": page.quality_score,
                "quality_signals": page.quality_signals,
                "review_reasons": page.review_reasons,
                "cache_hit": page.cache_hit,
                "attempts": [attempt.__dict__ for attempt in page.attempts],
            }
            for page in parsed.page_results
        ]
        rows.append(row)
        failures.extend({"document_id": truth.document_id, **item} for item in row["failures"])
        table_failures.extend(
            {"document_id": truth.document_id, **item} for item in row["table_failures"]
        )
        if check_ollama is not None:
            check_ollama()
        sleep_guard.checkpoint()
        progress(
            {
                "event": "document_complete",
                "system": adapter.name,
                "index": index,
                "total": len(truths),
                "failed_pages": row["failed_pages"],
            }
        )
    elapsed = perf_counter() - started
    pages = sum(len(truth.pages) for truth in truths)
    return {
        "system": adapter.name,
        "configuration": _adapter_configuration(adapter),
        "status": "ok" if not failures else "partial_failure",
        "wall_time_s": elapsed,
        "seconds_per_page": elapsed / pages,
        "cache_hits": cache_hits,
        "cold_valid": cache_hits == 0,
        "summary": _summarize(rows),
        "bootstrap_95_ci": _bootstrap(rows),
        "documents": rows,
        "failures": failures,
        "table_failures": table_failures,
    }


def _versions() -> dict[str, str]:
    result: dict[str, str] = {}
    for package in ("pymupdf", "docling", "torch", "pydantic"):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = "not installed"
    return result


def _hardware(settings: Settings) -> dict[str, object]:
    return {
        "machine": platform.machine(),
        "processor": platform.processor(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "ollama_version": _ollama_version(settings),
        "vision_model": settings.vision_model,
        "prompt_version": PROMPT_VERSION,
        "libraries": _versions(),
    }


def _identity(
    config: dict[str, Any], freeze_commit: str, config_path: Path = FROZEN_CONFIG
) -> dict[str, object]:
    return {
        "freeze_tag": FREEZE_TAG,
        "freeze_commit": freeze_commit,
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "system_order": list(config["freeze"]["system_order"]),
    }


def _begin_attempt(identity: dict[str, object]) -> tuple[int, dict[str, Any]]:
    previous: dict[str, Any] | None = None
    if STATE_PATH.is_file():
        previous = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if previous["identity"] != identity:
            raise RuntimeError("existing test-v1 state has a different frozen configuration")
        if previous["status"] == "running":
            previous["status"] = "infrastructure_failure"
            previous["reason"] = "unclean_process_exit"
            _atomic_json(STATE_PATH, previous)
        if previous["status"] != "infrastructure_failure":
            raise RuntimeError("test-v1 already ran; only infrastructure failure permits rerun")
        if int(previous["attempt"]) != 1:
            raise RuntimeError("the single infrastructure rerun has already been used")
        attempt = 2
    else:
        attempt = 1
    if (RESULT_ROOT / f"attempt-{attempt}").exists() or (
        CACHE_ROOT / f"attempt-{attempt}"
    ).exists():
        raise RuntimeError("attempt output or cache directory already exists")
    state = {
        "identity": identity,
        "attempt": attempt,
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "previous": previous,
    }
    _atomic_json(STATE_PATH, state)
    return attempt, state


def _failure_reason(exc: BaseException) -> str:
    if isinstance(exc, KeyboardInterrupt):
        return "user_interrupt"
    if isinstance(exc, InfrastructureFailure):
        return str(exc)
    if isinstance(exc, SystemExit):
        return "process_exit"
    return f"runner_exception_{type(exc).__name__}"


def _install_signal_handler() -> None:
    def interrupted(signum: int, _frame: object) -> None:
        name = signal.Signals(signum).name.casefold()
        raise InfrastructureFailure(f"signal_{name}")

    signal.signal(signal.SIGTERM, interrupted)


def run_once(config_path: Path = FROZEN_CONFIG) -> int:
    config = _load_config(config_path)
    if tuple(config["freeze"]["system_order"]) != SYSTEM_ORDER:
        raise RuntimeError("frozen system order does not match the runner")
    if float(config["evaluation"]["bad_page_accuracy_cutoff"]) != BAD_PAGE_ACCURACY_CUTOFF:
        raise RuntimeError("frozen bad-page cutoff does not match evaluation code")
    if int(config["evaluation"]["bootstrap_seed"]) != BOOTSTRAP_SEED:
        raise RuntimeError("frozen bootstrap seed does not match evaluation code")
    if int(config["evaluation"]["bootstrap_samples"]) != BOOTSTRAP_SAMPLES:
        raise RuntimeError("frozen bootstrap samples do not match evaluation code")
    if str(config["models"]["prompt_version"]) != PROMPT_VERSION:
        raise RuntimeError("frozen prompt version does not match parser code")
    freeze_commit = verify_freeze(config)
    if not _under_caffeinate():
        raise RuntimeError("test-v1 must run under caffeinate")
    identity = _identity(config, freeze_commit, config_path)
    attempt, state = _begin_attempt(identity)
    attempt_root = RESULT_ROOT / f"attempt-{attempt}"
    cache_root = CACHE_ROOT / f"attempt-{attempt}"
    attempt_root.mkdir(parents=True)
    cache_root.mkdir(parents=True)
    PROGRESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    os.environ["OLLAMA_KEEP_ALIVE"] = "1h"
    os.environ["UNMESS_DOCLING_ARTIFACTS_PATH"] = str(config["settings"]["docling_artifacts_path"])
    settings = _settings(config, cache_root / "initial")
    metadata: dict[str, Any] = {
        **identity,
        "attempt": attempt,
        "run_date_utc": datetime.now(UTC).isoformat(),
        "hardware": _hardware(settings),
        "ollama_keep_alive": os.environ["OLLAMA_KEEP_ALIVE"],
        "caffeinate_verified": True,
        "preloads": [],
        "systems": [],
    }
    _atomic_json(attempt_root / "metadata.json", metadata)

    def progress(event: dict[str, object]) -> None:
        with PROGRESS_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"attempt": attempt, **event}, separators=(",", ":")) + "\n")

    progress({"event": "attempt_start"})
    try:
        truths, manifest = _validate_manifest(DATASET, "test")
        expected_pages = sum(len(truth.pages) for truth in truths)
        metadata["dataset"] = {
            "documents": len(truths),
            "pages": expected_pages,
            "generator_version": manifest["generator_version"],
            "seed": manifest["seed"],
        }
        for name in SYSTEM_ORDER:
            system_cache = cache_root / name
            system_cache.mkdir()
            system_settings = _settings(config, system_cache)
            if name in {"unmess_parsing", "vlm_every_page"}:
                progress({"event": "model_preload_start", "before_system": name})
                preload_s = _preload_model(system_settings)
                metadata["preloads"].append({"before_system": name, "seconds": preload_s})
                _atomic_json(attempt_root / "metadata.json", metadata)
                progress(
                    {
                        "event": "model_preload_complete",
                        "before_system": name,
                        "seconds": preload_s,
                    }
                )
            adapter = _adapter(name, system_settings)
            progress({"event": "system_start", "system": name})
            health_check: Callable[[], None] | None = None
            if name in {"unmess_parsing", "vlm_every_page"}:
                health_check = _ollama_health_check(system_settings)
            result = _run_system(adapter, truths, DATASET, progress, health_check)
            result["cache_directory"] = str(system_cache)
            result["cache_files_before"] = 0
            result["cache_files_after"] = sum(item.is_file() for item in system_cache.rglob("*"))
            _atomic_json(attempt_root / f"{name}.json", result)
            metadata["systems"].append(name)
            _atomic_json(attempt_root / "metadata.json", metadata)
            progress(
                {
                    "event": "system_complete",
                    "system": name,
                    "cache_hits": result["cache_hits"],
                    "cold_valid": result["cold_valid"],
                }
            )
        generate_report(attempt_root, ROOT / "eval/results/test-v1.md")
        state.update({"status": "completed", "completed_at": datetime.now(UTC).isoformat()})
        _atomic_json(STATE_PATH, state)
        progress({"event": "attempt_complete"})
        return 0
    except BaseException as exc:
        reason = _failure_reason(exc)
        state.update(
            {
                "status": "infrastructure_failure",
                "reason": reason,
                "failed_at": datetime.now(UTC).isoformat(),
            }
        )
        _atomic_json(STATE_PATH, state)
        progress({"event": "infrastructure_failure", "reason": reason})
        return 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=FROZEN_CONFIG)
    args = parser.parse_args()
    _install_signal_handler()
    raise SystemExit(run_once(args.config))


if __name__ == "__main__":
    main()
