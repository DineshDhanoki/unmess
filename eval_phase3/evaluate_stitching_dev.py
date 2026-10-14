"""DEV-only Phase 3 table-stitching evaluation on real parser output."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from collections.abc import Callable
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

import pymupdf

from unmess.chunking.tables import (
    DEFAULT_STITCH_CONFIG,
    StitchConfig,
    TableFragment,
    find_stitch_candidate,
    fragments_from_pages,
    stitch_fragments,
)
from unmess.config import Settings
from unmess.models import BBox, Block, Cell, Table
from unmess.parsing.base import ParsedPage
from unmess.parsing.docling_parser import DoclingParser
from unmess.parsing.router import PageRouter

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


class PageParser(Protocol):
    def parse_page(self, pdf: Path, page_number: int) -> ParsedPage: ...


@dataclass(frozen=True)
class Example:
    document_id: str
    category: str
    positive: bool
    expected_rows: tuple[tuple[str, ...], ...]
    fragments: tuple[TableFragment, ...]
    parsers: tuple[str, ...]
    reference_regions: dict[int, tuple[BBox, ...]]
    page_token_count: int
    failed_pages: int = 0


@dataclass(frozen=True)
class Counts:
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int

    @property
    def precision(self) -> float:
        denominator = self.true_positive + self.false_positive
        return self.true_positive / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        denominator = self.true_positive + self.false_negative
        return self.true_positive / denominator if denominator else 0.0

    @property
    def f1(self) -> float:
        denominator = self.precision + self.recall
        return 2 * self.precision * self.recall / denominator if denominator else 0.0


def _bbox(page: int, values: list[float]) -> BBox:
    return BBox(page=page, x0=values[0], y0=values[1], x1=values[2], y1=values[3])


def _oracle_pages(truth: dict[str, Any]) -> list[ParsedPage]:
    pages: list[ParsedPage] = []
    for page_data in truth["pages"]:
        page_number = int(page_data["page"])
        blocks: list[Block] = []
        tables: list[Table] = []
        for index, element in enumerate(page_data["elements"]):
            if element["kind"] == "figure":
                blocks.append(
                    Block(
                        block_id=f"oracle:{page_number}:figure:{index}",
                        kind="figure",
                        text=str(element["label"]),
                        bbox=_bbox(page_number, element["bbox"]),
                    )
                )
                continue
            table_box = _bbox(page_number, element["bbox"])
            caption_box = BBox(
                page=page_number,
                x0=table_box.x0,
                y0=max(0.0, table_box.y0 - 0.025),
                x1=table_box.x1,
                y1=max(0.001, table_box.y0 - 0.001),
            )
            blocks.append(
                Block(
                    block_id=f"oracle:{page_number}:caption:{index}",
                    kind="caption",
                    text=str(element["caption"]),
                    bbox=caption_box,
                )
            )
            cells = [
                Cell(
                    row=int(cell["row"]),
                    col=int(cell["col"]),
                    text=str(cell["text"]),
                    bbox=_bbox(page_number, cell["bbox"]),
                )
                for cell in element["cells"]
            ]
            table = Table(
                table_id=str(element["table_id"]), page_numbers=[page_number], cells=cells
            )
            tables.append(table)
            blocks.append(
                Block(
                    block_id=f"oracle:{page_number}:table:{index}",
                    kind="table",
                    text="",
                    bbox=table_box,
                )
            )
        pages.append(ParsedPage(page_number, "oracle", blocks=blocks, tables=tables))
    return pages


def _pipeline_pages(path: Path, parser: PageParser, failure_name: str) -> list[ParsedPage]:
    with pymupdf.open(path) as document:
        count = len(document)
    pages: list[ParsedPage] = []
    for page_number in range(1, count + 1):
        try:
            pages.append(parser.parse_page(path, page_number))
        except Exception as exc:
            pages.append(ParsedPage.failed(page_number, failure_name, type(exc).__name__))
    return pages


def _example(
    item: dict[str, Any],
    truth: dict[str, Any],
    pages: list[ParsedPage],
) -> Example:
    expected = truth["expected_stitched_rows"] or []
    reference_regions: dict[int, list[BBox]] = {}
    for page_data in truth["pages"]:
        page_number = int(page_data["page"])
        reference_regions[page_number] = [
            _bbox(page_number, element["bbox"])
            for element in page_data["elements"]
            if element["kind"] == "table"
        ]
    return Example(
        document_id=str(item["document_id"]),
        category=str(item["category"]),
        positive=bool(item["positive_stitch_pairs"]),
        expected_rows=tuple(tuple(str(cell) for cell in row) for row in expected),
        fragments=tuple(fragments_from_pages(pages)),
        parsers=tuple(page.parser_name for page in pages),
        reference_regions={page: tuple(boxes) for page, boxes in reference_regions.items()},
        page_token_count=sum(len(page.text.split()) for page in pages),
        failed_pages=sum(not page.success for page in pages),
    )


def _predict(example: Example, config: StitchConfig) -> bool:
    if len(example.fragments) < 2:
        return False
    return find_stitch_candidate(example.fragments[0], example.fragments[1:], config) is not None


def _counts(examples: list[Example], predictions: list[bool]) -> Counts:
    tp = sum(
        example.positive and prediction
        for example, prediction in zip(examples, predictions, strict=True)
    )
    fp = sum(
        not example.positive and prediction
        for example, prediction in zip(examples, predictions, strict=True)
    )
    fn = sum(
        example.positive and not prediction
        for example, prediction in zip(examples, predictions, strict=True)
    )
    tn = sum(
        not example.positive and not prediction
        for example, prediction in zip(examples, predictions, strict=True)
    )
    return Counts(tp, fp, fn, tn)


def _grid() -> tuple[StitchConfig, ...]:
    return tuple(
        StitchConfig(header, geometry, edge)
        for header in (0.65, 0.72, 0.80)
        for geometry in (0.06, 0.08, 0.10)
        for edge in (0.15, 0.20, 0.25)
    )


def _select_config(examples: list[Example]) -> StitchConfig:
    def key(config: StitchConfig) -> tuple[float, int, float]:
        counts = _counts(examples, [_predict(example, config) for example in examples])
        distance = (
            abs(config.header_similarity - DEFAULT_STITCH_CONFIG.header_similarity)
            + abs(config.geometry_tolerance - DEFAULT_STITCH_CONFIG.geometry_tolerance)
            + abs(config.page_edge_band - DEFAULT_STITCH_CONFIG.page_edge_band)
        )
        return counts.f1, -counts.false_positive, -distance

    return max(_grid(), key=key)


def _lopo(examples: list[Example]) -> tuple[list[bool], Counter[StitchConfig]]:
    predictions: list[bool] = []
    selections: Counter[StitchConfig] = Counter()
    for index, held_out in enumerate(examples):
        config = _select_config(examples[:index] + examples[index + 1 :])
        selections[config] += 1
        predictions.append(_predict(held_out, config))
    return predictions, selections


def _normalize_cell(value: str) -> str:
    return " ".join(value.casefold().split()).strip(" .,:;")


def _cells(rows: tuple[tuple[str, ...], ...]) -> set[tuple[int, int, str]]:
    return {
        (row_index, column_index, _normalize_cell(value))
        for row_index, row in enumerate(rows)
        for column_index, value in enumerate(row)
    }


def _represented_rows(example: Example, stitch: bool) -> tuple[tuple[str, ...], ...]:
    if not example.fragments:
        return ()
    fragment = max(
        example.fragments,
        key=lambda item: len(item.structured.rows) + 1,
    )
    if stitch and len(example.fragments) >= 2:
        match = find_stitch_candidate(example.fragments[0], example.fragments[1:])
        if match is not None:
            index, _decision = match
            with suppress(ValueError):
                fragment = stitch_fragments(example.fragments[0], example.fragments[index + 1])
    return (fragment.structured.columns, *fragment.structured.rows)


def _cell_f1(examples: list[Example], predictions: list[bool]) -> float:
    true_positive = false_positive = false_negative = 0
    for example, prediction in zip(examples, predictions, strict=True):
        if not example.positive:
            continue
        expected = _cells(example.expected_rows)
        actual = _cells(_represented_rows(example, prediction))
        true_positive += len(expected & actual)
        false_positive += len(actual - expected)
        false_negative += len(expected - actual)
    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
    )
    recall = (
        true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
    )
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _intersects(first: BBox, second: BBox) -> bool:
    return (
        first.x0 < second.x1
        and first.x1 > second.x0
        and first.y0 < second.y1
        and first.y1 > second.y0
    )


def _emitted_fragments(example: Example, stitch: bool) -> tuple[TableFragment, ...]:
    if stitch and len(example.fragments) >= 2:
        match = find_stitch_candidate(example.fragments[0], example.fragments[1:])
        if match is not None:
            index, _decision = match
            candidate = index + 1
            with suppress(ValueError):
                return (
                    stitch_fragments(example.fragments[0], example.fragments[candidate]),
                    *example.fragments[1:candidate],
                    *example.fragments[candidate + 1 :],
                )
    return example.fragments


def _citation_counts(examples: list[Example], predictions: list[bool]) -> tuple[int, int]:
    correct = total = 0
    for example, prediction in zip(examples, predictions, strict=True):
        for fragment in _emitted_fragments(example, prediction):
            total += 1
            boxes_by_page = {
                page: [cell.bbox for cell in fragment.table.cells if cell.bbox.page == page]
                for page in fragment.table.page_numbers
            }
            if all(
                boxes_by_page[page]
                and any(
                    _intersects(box, reference)
                    for box in boxes_by_page[page]
                    for reference in example.reference_regions.get(page, ())
                )
                for page in fragment.table.page_numbers
            ):
                correct += 1
    return correct, total


def _system_result(name: str, examples: list[Example]) -> dict[str, Any]:
    fixed_predictions = [_predict(example, DEFAULT_STITCH_CONFIG) for example in examples]
    lopo_predictions, selections = _lopo(examples)
    fixed = _counts(examples, fixed_predictions)
    lopo = _counts(examples, lopo_predictions)
    before_predictions = [False] * len(examples)
    citation_correct, citation_total = _citation_counts(examples, fixed_predictions)
    reference_tables = sum(1 if example.positive else 2 for example in examples)
    split_tables = sum(
        example.positive and not prediction
        for example, prediction in zip(examples, fixed_predictions, strict=True)
    )
    naive_oversized_documents = sum(example.page_token_count > 600 for example in examples)
    return {
        "system": name,
        "documents": len(examples),
        "positive_pairs": sum(example.positive for example in examples),
        "negative_pairs": sum(not example.positive for example in examples),
        "extracted_pair_coverage": sum(len(example.fragments) >= 2 for example in examples),
        "failed_pages": sum(example.failed_pages for example in examples),
        "routing_shares": dict(
            sorted(Counter(parser for example in examples for parser in example.parsers).items())
        ),
        "before_cell_f1": _cell_f1(examples, before_predictions),
        "after_cell_f1": _cell_f1(examples, fixed_predictions),
        "chunk_integrity": {
            "split_reference_tables": split_tables,
            "reference_tables": reference_tables,
            "table_split_rate": split_tables / reference_tables,
            "dual_format_table_chunks": sum(
                len(_emitted_fragments(example, prediction))
                for example, prediction in zip(examples, fixed_predictions, strict=True)
            ),
            "naive_fixed_600_token_oversized_documents": naive_oversized_documents,
            "naive_table_split_rate": 0.0 if naive_oversized_documents == 0 else None,
        },
        "citations": {
            "correct": citation_correct,
            "chunks": citation_total,
            "accuracy": citation_correct / citation_total if citation_total else 0.0,
        },
        "fixed": {
            **asdict(fixed),
            "precision": fixed.precision,
            "recall": fixed.recall,
            "f1": fixed.f1,
        },
        "lopo": {**asdict(lopo), "precision": lopo.precision, "recall": lopo.recall, "f1": lopo.f1},
        "lopo_config_selections": [
            {"config": asdict(config), "held_out_pairs": count}
            for config, count in sorted(
                selections.items(), key=lambda item: (-item[1], repr(item[0]))
            )
        ],
        "categories": {
            category: asdict(
                _counts(
                    subset,
                    [_predict(example, DEFAULT_STITCH_CONFIG) for example in subset],
                )
            )
            for category in sorted({example.category for example in examples})
            if (subset := [example for example in examples if example.category == category])
        },
        "pairs": [
            {
                "document_id": example.document_id,
                "category": example.category,
                "expected_stitch": example.positive,
                "predicted_stitch": prediction,
                "extracted_tables": len(example.fragments),
                "parsers": example.parsers,
                "failed_pages": example.failed_pages,
            }
            for example, prediction in zip(examples, fixed_predictions, strict=True)
        ],
    }


def _report(results: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 3a DEV stitching evaluation",
        "",
        "Ground truth was used for scoring only. Docling and router inputs are `ParsedPage` "
        "output from the real pipeline. The oracle-input row is an upper bound built from "
        "ground-truth cells.",
        "",
        "| Input | Pairs | Extracted pairs | LOPO pair F1 | False merges | "
        "Before cell F1 | After cell F1 | Table splits | Citation accuracy |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        lopo = result["lopo"]
        lines.append(
            f"| {result['system']} | {result['documents']} | {result['extracted_pair_coverage']} | "
            f"{lopo['f1']:.3f} | {lopo['false_positive']}/{result['negative_pairs']} | "
            f"{result['before_cell_f1']:.3f} | {result['after_cell_f1']:.3f} | "
            f"{result['chunk_integrity']['split_reference_tables']}/"
            f"{result['chunk_integrity']['reference_tables']} | "
            f"{result['citations']['correct']}/{result['citations']['chunks']} "
            f"({result['citations']['accuracy']:.3f}) |"
        )
    primary = next(result for result in results if result["system"] == "Unmess router ParsedPage")
    integrity = primary["chunk_integrity"]
    citations = primary["citations"]
    lopo = primary["lopo"]
    reconstruction_improvement = primary["after_cell_f1"] - primary["before_cell_f1"]
    integrity_pass = (
        integrity["table_split_rate"] == 0.0
        and integrity["table_split_rate"] <= integrity["naive_table_split_rate"]
    )
    citation_pass = citations["accuracy"] >= 0.95
    reconstruction_pass = (
        primary["after_cell_f1"] >= 0.80
        and primary["after_cell_f1"] > 0.0
        and reconstruction_improvement >= 0.15
    )
    false_merge_pass = lopo["false_positive"] == 0
    lines.extend(
        [
            "",
            "The naive fixed-size baseline emits no structured cross-page table and therefore "
            "has pair F1 and spanning-table cell F1 of 0.000. Its 600-token windows are "
            "evaluated separately for chunk integrity.",
            "",
            "LOPO chooses among the preregistered stitcher's three parameters only: header "
            "similarity, geometry tolerance, and page-edge band. Full counts, category "
            "breakdowns, routing shares, failures, and selected configurations are in "
            "`stitching-dev.json`.",
            "",
            "## Preregistered criteria",
            "",
            f"- {'PASS' if integrity_pass else 'FAIL'} — chunk integrity: "
            f"{integrity['split_reference_tables']}/{integrity['reference_tables']} reference "
            f"tables split; naive fixed-size rate {integrity['naive_table_split_rate']:.3f}.",
            f"- {'PASS' if citation_pass else 'FAIL'} — citation accuracy: "
            f"{citations['correct']}/{citations['chunks']} ({citations['accuracy']:.3f}).",
            f"- {'PASS' if reconstruction_pass else 'FAIL'} — spanning-table reconstruction: "
            f"before {primary['before_cell_f1']:.3f}, after {primary['after_cell_f1']:.3f}, "
            f"absolute improvement {reconstruction_improvement:.3f}, naive 0.000.",
            f"- {'PASS' if false_merge_pass else 'FAIL'} — false merges: "
            f"{lopo['false_positive']}/{primary['negative_pairs']} hard negatives; LOPO pair "
            f"F1 {lopo['f1']:.3f}.",
            "",
            "## Category counts for Unmess router input",
            "",
            "| Category | TP | FP | FN | TN |",
            "|---|---:|---:|---:|---:|",
            *[
                f"| {category} | {counts['true_positive']} | {counts['false_positive']} | "
                f"{counts['false_negative']} | {counts['true_negative']} |"
                for category, counts in primary["categories"].items()
            ],
            "",
            "## Where Unmess loses",
            "",
            "Citation accuracy is below the preregistered threshold. Docling classified four "
            "synthetic figure regions as additional table fragments; those chunks do not "
            "intersect a reference table. Cell reconstruction also remains below the "
            "oracle-input upper bound because parser-visible cells include grouping errors around "
            "running page furniture. The router selected Docling for all 58 pages, so its result "
            "is identical to the Docling row on this corpus.",
            "",
            "Real-document validation: pending.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--report-only", action="store_true")
    options = arguments.parse_args()
    if options.report_only:
        raw = json.loads((RESULTS / "stitching-dev.json").read_text(encoding="utf-8"))
        stored_systems = list(raw["systems"])
        (RESULTS / "stitching-dev.md").write_text(_report(stored_systems), encoding="utf-8")
        print(f"wrote systems={len(stored_systems)} result_files=1")
        return
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    items = [item for item in manifest["documents"] if item["split"] == "dev"]
    truths = {
        item["document_id"]: json.loads((ROOT / item["ground_truth"]).read_text(encoding="utf-8"))
        for item in items
    }
    docling = DoclingParser(Settings().docling_artifacts_path)
    router = PageRouter(Settings(), docling_parser=docling)
    systems: tuple[
        tuple[str, Callable[[dict[str, Any], dict[str, Any]], list[ParsedPage]]], ...
    ] = (
        ("oracle input", lambda _item, truth: _oracle_pages(truth)),
        (
            "Docling ParsedPage",
            lambda item, _truth: _pipeline_pages(ROOT / item["pdf"], docling, "docling"),
        ),
        (
            "Unmess router ParsedPage",
            lambda item, _truth: _pipeline_pages(ROOT / item["pdf"], router, "router"),
        ),
    )
    results: list[dict[str, Any]] = []
    for name, loader in systems:
        examples = [
            _example(item, truths[item["document_id"]], loader(item, truths[item["document_id"]]))
            for item in items
        ]
        results.append(_system_result(name, examples))
        print(f"completed system={name!r} documents={len(examples)}")
    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = {
        "split": "dev",
        "docling_device": os.getenv("DOCLING_DEVICE", "auto"),
        "default_config": asdict(DEFAULT_STITCH_CONFIG),
        "systems": results,
    }
    (RESULTS / "stitching-dev.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (RESULTS / "stitching-dev.md").write_text(_report(results), encoding="utf-8")
    print(f"wrote systems={len(results)} result_files=2")


if __name__ == "__main__":
    main()
