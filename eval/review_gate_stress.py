"""DEV-only fault injection into parsed pages, with paired correct controls."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval.metrics.bootstrap import document_bootstrap_ci
from eval.metrics.calibration import review_metrics
from eval.metrics.ocr_cer import character_error_rate
from eval.metrics.table_f1 import table_cell_f1
from unmess.config import Settings
from unmess.models import BBox, Cell, Table
from unmess.parsing.base import ParsedPage
from unmess.parsing.page_features import PageFeatures
from unmess.quality.gates import review_gate
from unmess.quality.scorer import WEIGHTS, score_page

BAD_PAGE_CUTOFF = 0.90
CATEGORIES = (
    "ocr_corruption",
    "wrong_table_cells",
    "missed_line_items",
    "bilingual_field_errors",
    "empty_parse",
    "misleading_confidence",
)


@dataclass
class Case:
    case_id: str
    category: str
    control: bool
    reference_text: str
    reference_tables: list[Table]
    parsed: ParsedPage
    features: PageFeatures


def _table(rows: list[list[str]]) -> Table:
    return Table(
        table_id="synthetic-items",
        page_numbers=[1],
        cells=[
            Cell(
                row=r,
                col=c,
                text=value,
                bbox=BBox(
                    page=1,
                    x0=0.1 + c * 0.4,
                    x1=0.5 + c * 0.4,
                    y0=0.1 + r * 0.7 / len(rows),
                    y1=0.1 + (r + 1) * 0.7 / len(rows),
                ),
            )
            for r, row in enumerate(rows)
            for c, value in enumerate(row)
        ],
    )


def cases() -> list[Case]:
    """Three document sizes for each fault, each with an unmodified counterpart."""
    result = []
    for size in (3, 5, 8):
        rows = [[f"Fictional item {i}", str(100 + i * 17)] for i in range(size)]
        text = "SYNTHETIC ONLY. Example Goods Test Company.\n" + "\n".join(
            " | ".join(row) for row in rows
        )
        for category in CATEGORIES:
            reference = text
            tables = (
                [_table(rows)] if category in ("wrong_table_cells", "missed_line_items") else []
            )
            predicted, predicted_tables = reference, deepcopy(tables)
            if category == "ocr_corruption":
                predicted = "".join("\ufffd" if i % 3 == 0 else c for i, c in enumerate(reference))
            elif category == "wrong_table_cells":
                for cell in predicted_tables[0].cells:
                    if cell.col == 1:
                        cell.text = "999999"
            elif category == "missed_line_items":
                retained = max(1, size // 2)
                predicted_tables[0].cells = [
                    c for c in predicted_tables[0].cells if c.row < retained
                ]
                predicted = "\n".join(text.splitlines()[: retained + 1])
            elif category == "bilingual_field_errors":
                reference = "SYNTHETIC ONLY. काल्पनिक परीक्षण कंपनी।\n" + "\n".join(
                    f"वस्तु {i}: किताब। भुगतान: प्राप्त। शहर: काल्पनिक नगर।" for i in range(size)
                )
                predicted = (
                    reference.replace("किताब", "मेज")
                    .replace("प्राप्त", "बाकी")
                    .replace("काल्पनिक नगर", "परीक्षण ग्राम")
                )
            elif category == "empty_parse":
                predicted = ""
            elif category == "misleading_confidence":
                predicted = "SYNTHETIC ONLY. " + " ".join(
                    "The fictional garden has blue flowers and a winding path." for _ in range(size)
                )
            features = PageFeatures(
                embedded_text="",
                embedded_text_density=0,
                image_coverage=1,
                scan_likelihood=1,
                table_likelihood=0.9 if tables else 0,
                skew_degrees=0,
                garbled_character_ratio=0,
                dominant_script="Devanagari" if category == "bilingual_field_errors" else "Latin",
                layout_complexity=0.5,
            )
            for control in (False, True):
                page = ParsedPage(
                    page_number=1,
                    parser_name="synthetic-parser",
                    text=reference if control else predicted,
                    tables=deepcopy(tables if control else predicted_tables),
                    reported_confidence=1.0,
                )
                result.append(
                    Case(
                        f"{category}-{size}-{'control' if control else 'fault'}",
                        category,
                        control,
                        reference,
                        tables,
                        page,
                        features,
                    )
                )
    return result


def accuracy(case: Case) -> float:
    """Use the frozen runner's whitespace-normalized text/table composite."""
    if not case.parsed.success:
        return 0.0
    text = max(
        0.0,
        1.0
        - character_error_rate(
            " ".join(case.reference_text.split()), " ".join(case.parsed.text.split())
        ),
    )
    if not case.reference_tables:
        return text
    return (text + table_cell_f1(case.reference_tables, case.parsed.tables)[2]) / 2


def summarize(rows: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    metrics: dict[str, Any] = review_metrics(
        [r["quality_score"] for r in rows],
        [r["accuracy"] for r in rows],
        [r["flagged"] for r in rows],
        BAD_PAGE_CUTOFF,
    )
    samples = [
        {
            "precision": float(row["bad"]) if row["flagged"] else None,
            "recall": float(row["flagged"]) if row["bad"] else None,
        }
        for row in rows
    ]
    metrics["ci95"] = {
        name: document_bootstrap_ci(samples, name, seed=seed) for name in ("precision", "recall")
    }
    return metrics


def evaluate(settings: Settings, seed: int = 20261103) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case in cases():
        score = score_page(case.parsed, case.features, settings)
        case.parsed.quality_score = score.score
        decision = review_gate(case.case_id, case.parsed, case.features, settings)
        value = accuracy(case)
        rows.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "control": case.control,
                "page_number": 1,
                "accuracy": value,
                "bad": value < BAD_PAGE_CUTOFF,
                "quality_score": score.score,
                "signals": score.signals,
                "flagged": decision.flagged_for_review,
                "reasons": decision.reasons,
            }
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    keys = (
        "quality_review_threshold",
        "quality_visual_noise_threshold",
        "parser_table_likelihood_threshold",
        "parser_garbled_ratio_threshold",
    )
    return {
        "fixture_version": 1,
        "split": "dev",
        "bootstrap_seed": seed,
        "settings": {key: getattr(settings, key) for key in keys},
        "score_weights": WEIGHTS,
        "overall": summarize(rows, seed),
        "categories": {category: summarize(items, seed) for category, items in grouped.items()},
        "failures": [r["case_id"] for r in rows if r["bad"] != r["flagged"]],
        "cases": rows,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Review gate synthetic DEV stress test",
        "",
        "Run `uv run python -m eval.review_gate_stress --output "
        "docs/eval/review-gate-stress.json` from the repository root to regenerate this report.",
        "",
        "These fixtures inject parser output for six error categories at three document sizes, "
        "each paired with a correct control. The content and table regions are synthetic. "
        "The current scorer and review gate run on every page. "
        "The reference data and constructed inputs are in `eval/review_gate_stress.py`.",
        "",
        "Accuracy follows the frozen runner's composite. It uses whitespace-normalized "
        "1 - CER, averaged with table-cell F1 when a reference table exists. "
        "A page is bad below 0.90. Every parser output claims confidence 1.0. "
        "The fixture source features represent clean scanned pages with no embedded text.",
        "",
        "The 95% percentile intervals use the existing document bootstrap with 2,000 draws "
        f"and seed {report['bootstrap_seed']}. These intervals describe resampling this fixed "
        "synthetic set. Undefined-denominator draws are skipped. "
        "The JSON records valid draw counts. "
        "Paired templates limit diversity. Real-parser and real-document validation "
        "requires separate evidence.",
        "",
        "| Category | Pages | Bad | TP | FP | FN | TN | Precision | Recall |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for category, metrics in [("Overall", report["overall"]), *report["categories"].items()]:
        values = [
            str(metrics[k])
            for k in (
                "pages",
                "bad_pages",
                "true_positive",
                "false_positive",
                "false_negative",
                "true_negative",
            )
        ]
        values.extend(
            "undefined" if metrics[k] is None else f"{metrics[k]:.3f}"
            for k in ("precision", "recall")
        )
        lines.append("| " + " | ".join([category, *values]) + " |")
    lines += ["", "## Overall confidence intervals", ""]
    for name, ci in report["overall"]["ci95"].items():
        lines.append(f"- {name.title()} [{ci['lower']}, {ci['upper']}]")
    lines += ["", "## Misclassified cases", ""]
    for row in report["cases"]:
        if row["case_id"] in report["failures"]:
            kind = "false negative" if row["bad"] else "false positive"
            lines.append(
                f"- `{row['case_id']}` — {kind}, accuracy {row['accuracy']:.3f}, "
                f"quality {row['quality_score']:.3f}, reasons {row['reasons']}."
            )
    lines += [
        "",
        "## Configuration",
        "",
        "```json",
        json.dumps(report["settings"], indent=2),
        "```",
        "",
        "The companion JSON includes every outcome, quality signal and per-category interval.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(Settings())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    args.output.with_suffix(".md").write_text(markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
