import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from eval.report_test_v1 import SYSTEM_ORDER, _criteria, generate_report
from eval.run_eval import _bootstrap, _summarize
from eval.run_test_v1 import _begin_attempt, _under_caffeinate, verify_freeze


def _row(*, cer: float, table_f1: float, quality: Sequence[float] = (0.2, 0.9)) -> dict[str, Any]:
    return {
        "document_id": "synthetic-test-01",
        "category": "synthetic",
        "cohort": "original",
        "language": "en",
        "scan_difficulty": "not_scan",
        "pages": 2,
        "table_pages": 1,
        "ocr_pages": 1,
        "page_durations_s": [0.1, 0.1],
        "failed_pages": 0,
        "table_f1": table_f1,
        "ocr_cer": cer,
        "text_cer": cer,
        "text_wer": cer,
        "cheap_parser_share": 0.5,
        "latency_per_page_s": 0.1,
        "failed_page_rate": 0.0,
        "page_accuracy": [0.5, 1.0],
        "page_success": [True, True],
        "quality_scores": list(quality),
        "quality_signals": [{}, {}],
        "source_features": [{}, {}],
        "review_flags": [True, False],
        "page_texts": ["synthetic", "synthetic"],
        "expected_page_texts": ["synthetic", "synthetic"],
        "escalated_pages": 0,
        "escalation_improved_pages": 0,
        "escalation_accuracy_deltas": [],
        "vlm_attempted_pages": 0,
        "vlm_time_s": 0.0,
        "vlm_uncached_pages": 0,
        "vlm_uncached_time_s": 0.0,
        "table_failures": [],
        "failures": [],
    }


def _system(name: str, *, cer: float, table_f1: float, seconds: float) -> dict[str, Any]:
    rows = [_row(cer=cer, table_f1=table_f1)]
    return {
        "system": name,
        "configuration": {},
        "status": "ok",
        "wall_time_s": seconds,
        "seconds_per_page": seconds / 2,
        "cache_hits": 0,
        "cold_valid": True,
        "summary": _summarize(rows),
        "bootstrap_95_ci": _bootstrap(rows),
        "documents": rows,
        "failures": [],
        "table_failures": [],
    }


def test_verify_freeze_compares_tagged_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frozen = tmp_path / "frozen.txt"
    frozen.write_text("fixed", encoding="utf-8")

    def fake_git(args: list[str], *, binary: bool = False) -> subprocess.CompletedProcess[Any]:
        if args[0] == "rev-parse":
            output: Any = "abc\n"
        elif args[0] in {"merge-base", "status"}:
            output = ""
        elif args[0] in {"ls-tree", "ls-files"}:
            output = "frozen.txt\n"
        elif args[0] == "show":
            output = b"fixed" if binary else "fixed"
        elif args[0] == "diff":
            output = ""
        else:
            raise AssertionError(args)
        return subprocess.CompletedProcess(args, 0, output, b"" if binary else "")

    monkeypatch.setattr("eval.run_test_v1.ROOT", tmp_path)
    monkeypatch.setattr("eval.run_test_v1._git", fake_git)
    config = {
        "freeze": {
            "tag": "freeze-v1",
            "frozen_paths": ["frozen.txt"],
            "allowed_docs": ["docs"],
        }
    }
    assert verify_freeze(config) == "abc"
    frozen.write_text("changed", encoding="utf-8")
    with pytest.raises(RuntimeError, match="hash differs"):
        verify_freeze(config)


def test_run_state_allows_only_one_infrastructure_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result_root = tmp_path / "results"
    cache_root = tmp_path / "cache"
    state_path = result_root / "run-state.json"
    monkeypatch.setattr("eval.run_test_v1.RESULT_ROOT", result_root)
    monkeypatch.setattr("eval.run_test_v1.CACHE_ROOT", cache_root)
    monkeypatch.setattr("eval.run_test_v1.STATE_PATH", state_path)
    identity: dict[str, object] = {"freeze_commit": "abc"}

    attempt, state = _begin_attempt(identity)
    assert attempt == 1
    state.update({"status": "infrastructure_failure", "reason": "ollama_unavailable"})
    state_path.write_text(json.dumps(state), encoding="utf-8")
    assert _begin_attempt(identity)[0] == 2
    second = json.loads(state_path.read_text(encoding="utf-8"))
    second["status"] = "infrastructure_failure"
    state_path.write_text(json.dumps(second), encoding="utf-8")
    with pytest.raises(RuntimeError, match="already been used"):
        _begin_attempt(identity)


def test_caffeinate_must_be_in_process_ancestry(monkeypatch: pytest.MonkeyPatch) -> None:
    process_list = "30 20 python\n20 10 make\n10 1 /usr/bin/caffeinate\n1 0 launchd\n"
    monkeypatch.setattr("eval.run_test_v1.os.getpid", lambda: 30)
    monkeypatch.setattr(
        "eval.run_test_v1.subprocess.run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, process_list, ""),
    )
    assert _under_caffeinate()


def test_report_uses_saved_raw_results_and_marks_unstable_gate(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt-1"
    attempt.mkdir()
    metadata = {
        "freeze_tag": "freeze-v1",
        "freeze_commit": "abc",
        "attempt": 1,
        "dataset": {"documents": 1, "pages": 2},
        "hardware": {
            "platform": "synthetic-os",
            "machine": "synthetic-machine",
            "processor": "synthetic-cpu",
            "ollama_version": "0.0-test",
            "vision_model": "synthetic-model",
            "prompt_version": "test-v1",
        },
        "preloads": [
            {"before_system": "unmess_parsing", "seconds": 1.0},
            {"before_system": "vlm_every_page", "seconds": 1.0},
        ],
    }
    (attempt / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    systems = {
        "pymupdf_fixed": _system("pymupdf_fixed", cer=0.4, table_f1=0.2, seconds=1.0),
        "docling_default": _system("docling_default", cer=0.3, table_f1=0.8, seconds=2.0),
        "docling_only": _system("docling_only", cer=0.2, table_f1=0.8, seconds=3.0),
        "unmess_parsing": _system("unmess_parsing", cer=0.1, table_f1=0.8, seconds=4.0),
        "vlm_every_page": _system("vlm_every_page", cer=0.5, table_f1=0.0, seconds=8.0),
    }
    for name in SYSTEM_ORDER:
        (attempt / f"{name}.json").write_text(json.dumps(systems[name]), encoding="utf-8")

    assert all(passed for _label, passed, _detail in _criteria(systems, 2))
    output = tmp_path / "test-v1.md"
    generate_report(attempt, output)
    report = output.read_text(encoding="utf-8")
    assert "Real-document validation is pending." in report
    assert "unstable (fewer than 10 bad pages)" in report
    assert report.count("**PASS**") == 5
