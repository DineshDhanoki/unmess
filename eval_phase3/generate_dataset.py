"""Generate deterministic synthetic Phase 3 table-stitching fixtures."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0
TABLE_X = 54.0
ROW_HEIGHT = 28.0
HEADERS = ("Item", "Qty", "Amount")
GENERATOR_VERSION = "phase3a-v2"


@dataclass(frozen=True)
class TableSpec:
    table_id: str
    caption: str
    section_path: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    top_y: float
    header_rows: int = 1
    x: float = TABLE_X
    column_widths: tuple[float, ...] | None = None


@dataclass(frozen=True)
class FigureSpec:
    label: str
    x: float
    top_y: float
    width: float
    height: float


@dataclass(frozen=True)
class TextSpec:
    text: str
    x: float
    y: float


@dataclass(frozen=True)
class PageSpec:
    heading: str
    tables: tuple[TableSpec, ...]
    figures: tuple[FigureSpec, ...] = ()
    running_text: tuple[TextSpec, ...] = ()


@dataclass(frozen=True)
class DocumentSpec:
    document_id: str
    split: Literal["dev", "test"]
    category: str
    pages: tuple[PageSpec, ...]
    pair: tuple[str, str]
    should_stitch: bool
    pair_reason: str
    expected_rows: tuple[tuple[str, ...], ...] | None = None


def _bbox(x: float, top_y: float, width: float, height: float) -> list[float]:
    return [
        round(x / PAGE_WIDTH, 6),
        round((PAGE_HEIGHT - top_y) / PAGE_HEIGHT, 6),
        round((x + width) / PAGE_WIDTH, 6),
        round((PAGE_HEIGHT - (top_y - height)) / PAGE_HEIGHT, 6),
    ]


def _draw_table(pdf: canvas.Canvas, spec: TableSpec, page_number: int) -> dict[str, Any]:
    columns = len(spec.rows[0])
    column_widths = spec.column_widths or (
        (270.0, 90.0, 130.0) if columns == 3 else tuple(490.0 / columns for _ in range(columns))
    )
    width = sum(column_widths)
    height = ROW_HEIGHT * len(spec.rows)
    bottom = spec.top_y - height
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(spec.x, spec.top_y + 16, spec.caption)
    pdf.setLineWidth(0.8)
    for row_index in range(len(spec.rows) + 1):
        y = spec.top_y - row_index * ROW_HEIGHT
        pdf.line(spec.x, y, spec.x + width, y)
    x = spec.x
    for column_width in column_widths:
        pdf.line(x, spec.top_y, x, bottom)
        x += column_width
    pdf.line(spec.x + width, spec.top_y, spec.x + width, bottom)

    cells: list[dict[str, Any]] = []
    for row_index, row in enumerate(spec.rows):
        x = spec.x
        for column_index, (text, column_width) in enumerate(zip(row, column_widths, strict=True)):
            pdf.setFont("Helvetica-Bold" if row_index < spec.header_rows else "Helvetica", 9)
            pdf.drawString(x + 5, spec.top_y - row_index * ROW_HEIGHT - 18, text)
            cells.append(
                {
                    "row": row_index,
                    "col": column_index,
                    "text": text,
                    "bbox": _bbox(
                        x,
                        spec.top_y - row_index * ROW_HEIGHT,
                        column_width,
                        ROW_HEIGHT,
                    ),
                }
            )
            x += column_width
    return {
        "kind": "table",
        "table_id": spec.table_id,
        "caption": spec.caption,
        "section_path": list(spec.section_path),
        "page": page_number,
        "bbox": _bbox(spec.x, spec.top_y, width, height),
        "column_count": columns,
        "column_widths_normalized": [round(value / PAGE_WIDTH, 6) for value in column_widths],
        "header_rows": list(range(spec.header_rows)),
        "rows": [list(row) for row in spec.rows],
        "cells": cells,
    }


def _draw_figure(pdf: canvas.Canvas, spec: FigureSpec, page_number: int) -> dict[str, Any]:
    bottom = spec.top_y - spec.height
    pdf.setFillColorRGB(0.92, 0.94, 0.97)
    pdf.rect(spec.x, bottom, spec.width, spec.height, fill=1, stroke=1)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(spec.x + spec.width / 2, bottom + spec.height / 2, spec.label)
    return {
        "kind": "figure",
        "label": spec.label,
        "page": page_number,
        "bbox": _bbox(spec.x, spec.top_y, spec.width, spec.height),
    }


def _variant_rows(index: int) -> tuple[tuple[str, ...], ...]:
    return (
        HEADERS,
        (f"Synthetic item {index}-A", "1", "125"),
        (f"Synthetic item {index}-B", "2", "250"),
        (f"Synthetic item {index}-C", "3", "375"),
        (f"Synthetic item {index}-D", "4", "500"),
    )


def _other_rows(
    index: int, label: str, header: tuple[str, ...] = HEADERS
) -> tuple[tuple[str, ...], ...]:
    return (
        header,
        (f"Synthetic {label} {index}-X", "8", "800"),
        (f"Synthetic {label} {index}-Y", "9", "900"),
    )


def _header_variant(mode: int) -> tuple[str, ...]:
    variants = (
        HEADERS,
        ("item", "qty", "amount"),
        ("Item.", "Qty.", "Amount."),
        ("ltem", "QTY", "Arnount"),
    )
    return variants[mode % len(variants)]


def _table(
    table_id: str,
    caption: str,
    section: str,
    rows: tuple[tuple[str, ...], ...],
    top_y: float,
    *,
    header_rows: int = 1,
    x: float = TABLE_X,
    column_widths: tuple[float, ...] | None = None,
) -> TableSpec:
    return TableSpec(table_id, caption, (section,), rows, top_y, header_rows, x, column_widths)


def _spec(
    category: str,
    split: Literal["dev", "test"],
    variant: int,
    mode: int,
) -> DocumentSpec:
    prefix = f"synthetic-{category}-{variant:02d}"
    rows = _variant_rows(variant)
    first_id, second_id = f"{prefix}-p1", f"{prefix}-p2"
    bottom_top = 146.0
    page_top = 742.0
    if category == "continuation_repeated_header":
        continued_header = _header_variant(mode)
        caption = "Ledger (continued)" if mode % 2 == 0 else "Ledger"
        running = (
            (TextSpec("SYNTHETIC LEDGER RUNNING HEADER", 190.0, 726.0),)
            if mode % 3 == 1
            else (TextSpec(f"Page {variant + 1}", 282.0, 28.0),)
            if mode % 3 == 2
            else ()
        )
        pages = (
            PageSpec(
                "Synthetic continued ledger",
                (_table(first_id, "Ledger (part 1)", "Ledger", rows[:3], bottom_top),),
            ),
            PageSpec(
                "Synthetic continued ledger",
                (_table(second_id, caption, "Ledger", (continued_header, *rows[3:]), page_top),),
                running_text=running,
            ),
        )
        return DocumentSpec(
            prefix,
            split,
            category,
            pages,
            (first_id, second_id),
            True,
            "repeated header and aligned boundary tables",
            rows,
        )
    if category == "continuation_without_header":
        caption = "Register (continued)" if mode % 2 == 0 else "Register"
        running = (
            (TextSpec("SYNTHETIC REGISTER", 230.0, 726.0),)
            if mode % 3 == 1
            else (TextSpec(f"Page {variant + 1}", 282.0, 28.0),)
            if mode % 3 == 2
            else ()
        )
        pages = (
            PageSpec(
                "Synthetic continued register",
                (_table(first_id, "Register (part 1)", "Register", rows[:3], bottom_top),),
            ),
            PageSpec(
                "Synthetic continued register",
                (
                    _table(
                        second_id,
                        caption,
                        "Register",
                        rows[3:],
                        page_top,
                        header_rows=0,
                    ),
                ),
                running_text=running,
            ),
        )
        return DocumentSpec(
            prefix,
            split,
            category,
            pages,
            (first_id, second_id),
            True,
            "explicit continuation without a repeated header",
            rows,
        )
    if category == "continuation_across_figure":
        caption = "Schedule (continued)" if mode % 2 == 0 else "Schedule"
        pages = (
            PageSpec(
                "Synthetic schedule",
                (_table(first_id, "Schedule", "Schedule", rows[:3], bottom_top),),
            ),
            PageSpec(
                "Synthetic schedule",
                (
                    _table(
                        second_id,
                        caption,
                        "Schedule",
                        (_header_variant(mode), *rows[3:]),
                        500.0,
                    ),
                ),
                (FigureSpec("SYNTHETIC FIGURE", 106.0, 720.0, 400.0, 120.0),),
            ),
        )
        return DocumentSpec(
            prefix,
            split,
            category,
            pages,
            (first_id, second_id),
            True,
            "same section and table continue after an intervening figure",
            rows,
        )
    if category == "unrelated_same_columns":
        near_header = _header_variant(mode) if mode % 2 else HEADERS
        other = _other_rows(variant, "asset", near_header)
        pages = (
            PageSpec(
                "Synthetic purchases",
                (_table(first_id, "Purchases", "Purchases", rows[:3], bottom_top),),
            ),
            PageSpec(
                "Synthetic inventory",
                (_table(second_id, "Inventory", "Inventory", other, page_top),),
            ),
        )
        return DocumentSpec(
            prefix,
            split,
            category,
            pages,
            (first_id, second_id),
            False,
            "unrelated sections with the same column count",
        )
    if category == "midpage_then_different":
        other = _other_rows(variant, "credit")
        pages = (
            PageSpec(
                "Synthetic charges", (_table(first_id, "Charges", "Charges", rows[:3], 560.0),)
            ),
            PageSpec(
                "Synthetic credits", (_table(second_id, "Credits", "Credits", other, page_top),)
            ),
        )
        return DocumentSpec(
            prefix,
            split,
            category,
            pages,
            (first_id, second_id),
            False,
            "first table ends mid-page before a different table",
        )
    if category == "continuation_after_figure":
        other = _other_rows(variant, "note", _header_variant(mode))
        pages = (
            PageSpec(
                "Synthetic schedule",
                (_table(first_id, "Schedule", "Schedule", rows[:3], bottom_top),),
            ),
            PageSpec(
                "Synthetic illustrated notes",
                (_table(second_id, "Schedule rows", "Illustrated notes", other, 500.0),),
                (FigureSpec("SYNTHETIC FIGURE", 106.0, 720.0, 400.0, 120.0),),
            ),
        )
        return DocumentSpec(
            prefix,
            split,
            category,
            pages,
            (first_id, second_id),
            False,
            "a figure and section boundary interrupt the apparent continuation",
        )
    if category == "misleading_repeated_header":
        other = _other_rows(variant, "refund", _header_variant(mode))
        pages = (
            PageSpec(
                "Synthetic orders", (_table(first_id, "Orders", "Orders", rows[:3], bottom_top),)
            ),
            PageSpec(
                "Synthetic refunds", (_table(second_id, "Refunds", "Refunds", other, page_top),)
            ),
        )
        return DocumentSpec(
            prefix,
            split,
            category,
            pages,
            (first_id, second_id),
            False,
            "header and geometry repeat but section identity changes",
        )
    if category == "geometry_mismatch":
        other = _other_rows(variant, "offset", _header_variant(mode))
        widths = (210.0, 115.0, 105.0) if mode % 2 == 0 else (300.0, 70.0, 90.0)
        offset = 92.0 if mode % 2 == 0 else 34.0
        pages = (
            PageSpec(
                "Synthetic ledger",
                (_table(first_id, "Ledger", "Ledger", rows[:3], bottom_top),),
            ),
            PageSpec(
                "Synthetic ledger appendix",
                (
                    _table(
                        second_id,
                        "Ledger appendix",
                        "Ledger appendix",
                        other,
                        page_top,
                        x=offset,
                        column_widths=widths,
                    ),
                ),
            ),
        )
        return DocumentSpec(
            prefix,
            split,
            category,
            pages,
            (first_id, second_id),
            False,
            "similar headers but incompatible table width or column offsets",
        )
    raise ValueError(category)


def _specs() -> list[DocumentSpec]:
    cases = (
        ("continuation_repeated_header", 6),
        ("continuation_without_header", 4),
        ("continuation_across_figure", 2),
        ("unrelated_same_columns", 4),
        ("misleading_repeated_header", 4),
        ("geometry_mismatch", 4),
        ("midpage_then_different", 3),
        ("continuation_after_figure", 2),
    )
    splits: tuple[Literal["dev", "test"], ...] = ("dev", "test")
    specs: list[DocumentSpec] = []
    for split_index, split in enumerate(splits):
        variant = split_index * 100
        for category, count in cases:
            for mode in range(count):
                specs.append(_spec(category, split, variant, mode))
                variant += 1
    return specs


def _write_document(spec: DocumentSpec, pdf_path: Path) -> dict[str, Any]:
    pdf = canvas.Canvas(str(pdf_path), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), invariant=1)
    ground_truth_pages: list[dict[str, Any]] = []
    for page_number, page in enumerate(spec.pages, 1):
        pdf.setTitle(spec.document_id)
        pdf.setAuthor("Unmess synthetic fixture generator")
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(54, 770, "SYNTHETIC DOCUMENT - NOT REAL DATA")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(54, 752, page.heading)
        pdf.setFont("Helvetica", 8)
        for running_text in page.running_text:
            pdf.drawString(running_text.x, running_text.y, running_text.text)
        elements: list[dict[str, Any]] = []
        elements.extend(_draw_figure(pdf, figure, page_number) for figure in page.figures)
        elements.extend(_draw_table(pdf, table, page_number) for table in page.tables)
        ground_truth_pages.append({"page": page_number, "elements": elements})
        pdf.showPage()
    pdf.save()
    pdf_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    return {
        "version": 1,
        "generator_version": GENERATOR_VERSION,
        "document_id": spec.document_id,
        "split": spec.split,
        "category": spec.category,
        "source_file": f"pdf/{pdf_path.name}",
        "file_sha256": pdf_hash,
        "page_size": {"width": PAGE_WIDTH, "height": PAGE_HEIGHT},
        "pages": ground_truth_pages,
        "stitch_pair": {
            "table_ids": list(spec.pair),
            "should_stitch": spec.should_stitch,
            "reason": spec.pair_reason,
        },
        "expected_stitched_rows": (
            [list(row) for row in spec.expected_rows] if spec.expected_rows is not None else None
        ),
    }


def generate(output: Path = ROOT) -> dict[str, Any]:
    pdf_dir = output / "pdf"
    truth_dir = output / "ground_truth"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    for old_path in (*pdf_dir.glob("synthetic-*.pdf"), *truth_dir.glob("synthetic-*.json")):
        old_path.unlink()
    documents: list[dict[str, Any]] = []
    for spec in _specs():
        pdf_path = pdf_dir / f"{spec.document_id}.pdf"
        truth_path = truth_dir / f"{spec.document_id}.json"
        truth = _write_document(spec, pdf_path)
        truth_path.write_text(json.dumps(truth, indent=2) + "\n", encoding="utf-8")
        documents.append(
            {
                "document_id": spec.document_id,
                "split": spec.split,
                "category": spec.category,
                "pages": len(spec.pages),
                "pdf": f"pdf/{pdf_path.name}",
                "ground_truth": f"ground_truth/{truth_path.name}",
                "pdf_sha256": truth["file_sha256"],
                "ground_truth_sha256": hashlib.sha256(truth_path.read_bytes()).hexdigest(),
                "positive_stitch_pairs": int(spec.should_stitch),
                "negative_stitch_pairs": int(not spec.should_stitch),
            }
        )
    manifest = {
        "generator_version": GENERATOR_VERSION,
        "synthetic_only": True,
        "documents": documents,
    }
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    manifest = generate()
    dev = sum(item["split"] == "dev" for item in manifest["documents"])
    test = sum(item["split"] == "test" for item in manifest["documents"])
    print(f"Generated synthetic Phase 3 dataset: dev={dev}, test={test}")


if __name__ == "__main__":
    main()
