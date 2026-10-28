"""Generate the frozen v1 test report from completed per-system raw JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eval.run_eval import _calibration, _route_shares

SYSTEM_ORDER = (
    "pymupdf_fixed",
    "docling_default",
    "docling_only",
    "unmess_parsing",
    "vlm_every_page",
)


def _format(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _interval(system: dict[str, Any], metric: str) -> str:
    interval = system["bootstrap_95_ci"][metric]
    if interval["lower"] is None:
        return "n/a"
    return f"{interval['lower']:.4f}-{interval['upper']:.4f}"


def _overlaps(left: dict[str, Any], right: dict[str, Any]) -> bool:
    values = (left["lower"], left["upper"], right["lower"], right["upper"])
    if any(value is None for value in values):
        return False
    return float(left["lower"]) <= float(right["upper"]) and float(right["lower"]) <= float(
        left["upper"]
    )


def _criteria(
    systems: dict[str, dict[str, Any]], expected_pages: int
) -> list[tuple[str, bool, str]]:
    ours = systems["unmess_parsing"]
    ours_overall = ours["summary"]["overall"]
    baselines = [systems[name] for name in SYSTEM_ORDER if name != "unmess_parsing"]
    cer_pass = all(
        ours_overall["text_cer"] < system["summary"]["overall"]["text_cer"] for system in baselines
    )
    docling = systems["docling_only"]
    ours_table = ours_overall["table_f1"]
    docling_interval = docling["bootstrap_95_ci"]["table_f1"]
    table_pass = (
        ours_table is not None
        and docling_interval["lower"] is not None
        and float(docling_interval["lower"]) <= ours_table <= float(docling_interval["upper"])
    ) or _overlaps(ours["bootstrap_95_ci"]["table_f1"], docling["bootstrap_95_ci"]["table_f1"])
    vlm = systems["vlm_every_page"]
    timing_pass = bool(
        ours["cold_valid"] and vlm["cold_valid"] and ours["wall_time_s"] < vlm["wall_time_s"]
    )
    gate = _calibration(ours["documents"])["review_gate"]
    gate_pass = gate["auroc"] is not None and gate["auroc"] > 0.70
    denominator_pass = all(
        system["summary"]["overall"]["pages"] == expected_pages
        and system["summary"]["overall"]["failed_pages"] == len(system["failures"])
        for system in systems.values()
    )
    return [
        ("1. Overall CER below every baseline", cer_pass, "point estimates"),
        ("2. Table compatibility with forced multilingual Docling", table_pass, "point/CI overlap"),
        ("3. Cold Unmess faster than VLM-only", timing_pass, "both timings must be cold-valid"),
        ("4. Review-gate AUROC above 0.70", gate_pass, f"AUROC {_format(gate['auroc'])}"),
        (
            "5. Failures retained in denominators and listed",
            denominator_pass,
            f"{expected_pages} pages per system",
        ),
    ]


def _breakdown(lines: list[str], systems: dict[str, dict[str, Any]], group: str) -> None:
    title = {
        "by_category": "Category",
        "by_language": "Language",
        "by_scan_difficulty": "Difficulty",
    }[group]
    lines += [
        "",
        f"## {title} breakdown",
        "",
        "| System | Group | Documents | Pages | Failed | CER | WER | Table F1 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in SYSTEM_ORDER:
        for label, values in systems[name]["summary"][group].items():
            lines.append(
                f"| {name} | {label} | {values['documents']} | {values['pages']} | "
                f"{values['failed_pages']} | {_format(values['text_cer'])} | "
                f"{_format(values['text_wer'])} | {_format(values['table_f1'])} |"
            )


def generate_report(attempt_root: Path, output: Path) -> None:
    metadata = json.loads((attempt_root / "metadata.json").read_text(encoding="utf-8"))
    systems = {
        name: json.loads((attempt_root / f"{name}.json").read_text(encoding="utf-8"))
        for name in SYSTEM_ORDER
    }
    expected_pages = int(metadata["dataset"]["pages"])
    criteria = _criteria(systems, expected_pages)
    gate = _calibration(systems["unmess_parsing"]["documents"])["review_gate"]
    routes = _route_shares({"documents": systems["unmess_parsing"]["documents"]})
    stability = "unstable (fewer than 10 bad pages)" if gate["unstable"] else "not flagged unstable"
    lines = [
        "# Frozen v1 test evaluation",
        "",
        f"Freeze: `{metadata['freeze_tag']}` at `{metadata['freeze_commit']}`; "
        f"attempt {metadata['attempt']}.",
        "Real-document validation is pending.",
        "",
        "## Environment",
        "",
        f"Platform: `{metadata['hardware']['platform']}`; machine: "
        f"`{metadata['hardware']['machine']}`; processor: `{metadata['hardware']['processor']}`.",
        f"Ollama `{metadata['hardware']['ollama_version']}`; vision model "
        f"`{metadata['hardware']['vision_model']}`; prompt "
        f"`{metadata['hardware']['prompt_version']}`.",
        "",
        "## Pre-registered criteria",
        "",
    ]
    for label, passed, detail in criteria:
        lines.append(f"- **{'PASS' if passed else 'FAIL'}** — {label} ({detail}).")
    lines += [
        "",
        "## Overall results",
        "",
        "| System | Documents | Pages | Failed | CER (95% CI) | WER (95% CI) | "
        "Table F1 (95% CI) | Cold s | Cache hits | Cold valid |",
        "|---|---:|---:|---:|---|---|---|---:|---:|---|",
    ]
    for name in SYSTEM_ORDER:
        system = systems[name]
        overall = system["summary"]["overall"]
        lines.append(
            f"| {name} | {overall['documents']} | {overall['pages']} | {overall['failed_pages']} | "
            f"{_format(overall['text_cer'])} ({_interval(system, 'text_cer')}) | "
            f"{_format(overall['text_wer'])} ({_interval(system, 'text_wer')}) | "
            f"{_format(overall['table_f1'])} ({_interval(system, 'table_f1')}) | "
            f"{_format(system['wall_time_s'])} | {system['cache_hits']} | {system['cold_valid']} |"
        )
    lines += [
        "",
        "### Metric denominators",
        "",
        "| System | Metric | Documents | Pages |",
        "|---|---|---:|---:|",
    ]
    for name in SYSTEM_ORDER:
        for metric, counts in systems[name]["summary"]["overall"]["metric_counts"].items():
            lines.append(f"| {name} | {metric} | {counts['documents']} | {counts['pages']} |")
    for group in ("by_category", "by_language", "by_scan_difficulty"):
        _breakdown(lines, systems, group)
    lines += [
        "",
        "## Parser routing shares",
        "",
        "| Parser | Pages | Share |",
        "|---|---:|---:|",
        f"| PyMuPDF | {routes['pymupdf_pages']} | {_format(routes['pymupdf_share'])} |",
        f"| Docling | {routes['docling_pages']} | {_format(routes['docling_share'])} |",
        f"| VLM | {routes['vlm_pages']} | {_format(routes['vlm_share'])} |",
        "",
        "## Review gate",
        "",
        f"Bad-page cutoff: `{_format(gate['bad_page_cutoff'])}`; pages: {gate['pages']}; "
        f"bad pages: {gate['bad_pages']}; AUROC: `{_format(gate['auroc'])}`; "
        f"precision: `{_format(gate['precision'])}`; recall: `{_format(gate['recall'])}`.",
        f"Stability: **{stability}**.",
        "",
        "## Vision-model preloads",
        "",
        "Preload and verification time is excluded from every per-system timing.",
        "",
        "| Before system | Seconds |",
        "|---|---:|",
    ]
    for preload in metadata["preloads"]:
        lines.append(f"| {preload['before_system']} | {_format(preload['seconds'])} |")
    lines += ["", "## Failures", ""]
    found = False
    for name in SYSTEM_ORDER:
        for failure in systems[name]["failures"]:
            found = True
            lines.append(
                f"- {name}: document `{failure['document_id']}`, page {failure['page']}, "
                f"parser `{failure['parser']}`, error `{failure['error']}`."
            )
    if not found:
        lines.append("None.")
    lines += [
        "",
        "Raw per-page system results were saved as each system completed; this report was "
        "generated from those files without rerunning parsers.",
        "",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt_root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("eval/results/test-v1.md"))
    args = parser.parse_args()
    generate_report(args.attempt_root, args.output)


if __name__ == "__main__":
    main()
