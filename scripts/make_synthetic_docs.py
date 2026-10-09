"""Generate deterministic, wholly fictional PDFs and validated ground truth."""

import argparse
import hashlib
import io
import json
import random
from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from unmess.models import Answer, BBox, Cell, Degradation, GroundTruth, Page, Table

SEED = 20261010
GENERATOR_VERSION = "1.0.0"
CATEGORIES = (
    "clean",
    "scan",
    "receipt",
    "gst_invoice",
    "merged_table",
    "spanning_table",
    "bilingual",
)
PAGE_W, PAGE_H = 612, 792
HINDI = "कुल राशि"


def _bbox(page: int, x0: float, top: float, x1: float, bottom: float) -> BBox:
    return BBox(page=page, x0=x0 / PAGE_W, y0=top / PAGE_H, x1=x1 / PAGE_W, y1=bottom / PAGE_H)


def _draw_line(pdf: canvas.Canvas, text: str, x: float, top: float, size: int = 11) -> None:
    pdf.setFont("Helvetica", size)
    pdf.drawString(x, PAGE_H - top - size, text)


def _hindi_image(font_path: Path) -> Image.Image:
    font = ImageFont.truetype(str(font_path), 29)
    image = Image.new("RGB", (350, 48), "white")
    ImageDraw.Draw(image).text((0, 0), HINDI, font=font, fill="black")
    return image


def _pdf_bytes(
    category: str, index: int, font_path: Path | None, degradation: Degradation | None
) -> tuple[bytes, list[Page], list[Table], list[Answer]]:
    document_id = f"synthetic-{category}-{index:02d}"
    amount = 10000 + index * 18000
    formatted = f"{amount:,}"
    indian = (
        f"{amount:,}"
        if amount < 100000
        else f"{amount // 100000},{amount // 1000 % 100:02d},{amount % 1000:03d}"
    )
    issue_date = f"2026-02-{index + 1:02d}"
    code = f"FAKE-{category.upper()[:3]}-{index:02d}"
    lines = [
        f"SYNTHETIC DOCUMENT - {category.replace('_', ' ').upper()}",
        f"Document code: {code}",
        f"Fictional seller: Demo Vendor {index:02d}",
        f"Issue date: {issue_date}",
        f"Total INR: {formatted}",
        "GSTIN: INVALID-SYNTHETIC-NOT-A-REAL-ID",
    ]
    if category in {"gst_invoice", "merged_table", "spanning_table"}:
        lines[5] = "GSTIN: INVALID-SYNTHETIC-NOT-A-REAL-ID | CGST 9% | SGST 9%"
    page_count = 2 if category == "spanning_table" else 1
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(PAGE_W, PAGE_H), invariant=1, pageCompression=1)
    pdf.setTitle(document_id)
    pdf.setAuthor("Unmess contributors")
    pdf.setCreator(f"Unmess synthetic generator {GENERATOR_VERSION}")
    pdf.setProducer("Unmess synthetic generator")
    tables: list[Table] = []
    cells: list[Cell] = []
    page_text: list[list[str]] = []
    for page_no in range(1, page_count + 1):
        current: list[str] = []
        if page_no == 1:
            if category == "receipt":
                pdf.setDash(3, 3)
                pdf.rect(38, PAGE_H - 290, 390, 246)
                pdf.setDash()
            for line_idx, line in enumerate(lines):
                _draw_line(pdf, line, 48, 65 + 28 * line_idx)
                current.append(line)
            if category == "bilingual":
                if font_path is None:
                    raise ValueError(
                        "Noto Sans Devanagari font is required for bilingual generation"
                    )
                pdf.drawImage(ImageReader(_hindi_image(font_path)), 48, PAGE_H - 320, 175, 24)
                current.append(HINDI)
        else:
            continuation = f"{document_id} - table continuation"
            _draw_line(pdf, continuation, 48, 65)
            current.append(continuation)
        if category in {"gst_invoice", "merged_table", "spanning_table"}:
            start_top = 355 if page_no == 1 else 130
            if category == "merged_table" and page_no == 1:
                label = "Merged line item heading"
                _draw_line(pdf, label, 55, start_top)
                current.append(label)
                cells.append(
                    Cell(
                        row=0,
                        col=0,
                        col_span=3,
                        text=label,
                        bbox=_bbox(1, 50, start_top, 450, start_top + 21),
                    )
                )
                start_top += 30
            header_row = 1 if category == "merged_table" else 0
            headers = ["Item", "Qty", "Amount"]
            pdf.setStrokeColorRGB(0.45, 0.45, 0.45)
            pdf.line(50, PAGE_H - start_top + 5, 505, PAGE_H - start_top + 5)
            for col, header in enumerate(headers):
                x = 55 + col * 150
                _draw_line(pdf, header, x, start_top)
                current.append(header)
                cells.append(
                    Cell(
                        row=header_row,
                        col=col,
                        text=header,
                        bbox=_bbox(page_no, x, start_top, x + 105, start_top + 21),
                    )
                )
            first = 1 if page_no == 1 else 4
            last = 3 if page_no == 1 and page_count == 2 else 6 if page_no == 2 else 4
            for row in range(first, last + 1):
                top = start_top + (row - first + 1) * 30
                pdf.line(50, PAGE_H - top + 5, 505, PAGE_H - top + 5)
                values = [f"Fake item {row}", str(row), str(row * 125)]
                for col, value in enumerate(values):
                    x = 55 + col * 150
                    _draw_line(pdf, value, x, top)
                    current.append(value)
                    cells.append(
                        Cell(
                            row=header_row + row,
                            col=col,
                            text=value,
                            bbox=_bbox(page_no, x, top, x + 105, top + 21),
                        )
                    )
            pdf.line(50, PAGE_H - top - 25, 505, PAGE_H - top - 25)
        page_text.append(current)
        pdf.showPage()
    pdf.save()
    raw = buffer.getvalue()
    if category == "scan" and degradation is not None:
        source = pymupdf.open(stream=raw, filetype="pdf")
        pix = source[0].get_pixmap(dpi=degradation.dpi, alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        image = image.rotate(
            degradation.rotation_deg, resample=Image.Resampling.BICUBIC, fillcolor="white"
        )
        image = image.filter(ImageFilter.GaussianBlur(degradation.blur))
        rng = random.Random(SEED + index)
        pixels = image.load()
        assert pixels is not None
        for _ in range(int(image.width * image.height * degradation.noise_level * 0.08)):
            x, y = rng.randrange(image.width), rng.randrange(image.height)
            pixels[x, y] = (rng.randrange(160),) * 3
        scan_buffer = io.BytesIO()
        scan_pdf = canvas.Canvas(scan_buffer, pagesize=(PAGE_W, PAGE_H), invariant=1)
        scan_pdf.setTitle(document_id)
        scan_pdf.setAuthor("Unmess contributors")
        scan_pdf.setCreator(f"Unmess synthetic generator {GENERATOR_VERSION}")
        scan_pdf.setProducer("Unmess synthetic generator")
        scan_pdf.drawImage(ImageReader(image), 0, 0, PAGE_W, PAGE_H)
        scan_pdf.save()
        raw = scan_buffer.getvalue()
    if cells:
        tables.append(
            Table(
                table_id="line-items",
                page_numbers=list(range(1, page_count + 1)),
                cells=cells,
                has_merged_cells=category == "merged_table",
                spans_pages=page_count > 1,
            )
        )
    pages = [
        Page(
            page_number=number,
            language="hi" if category == "bilingual" else "en",
            expected_text="\n".join(content),
            is_ocr_page=category == "scan",
        )
        for number, content in enumerate(page_text, 1)
    ]
    answers = [
        Answer(
            id="code",
            question=(
                f"What is the document code for Demo Vendor {index:02d} in this {category} record?"
            ),
            answer=code,
            answer_type="text",
            answer_aliases=[code],
            language="en",
            answering_pages=[1],
            answer_bboxes=[_bbox(1, 48, 93, 420, 115)],
        ),
        Answer(
            id="seller",
            question=f"Who is the fictional seller on document {code}?",
            answer=f"Demo Vendor {index:02d}",
            answer_type="text",
            answer_aliases=[f"Demo Vendor {index:02d}"],
            language="en",
            answering_pages=[1],
            answer_bboxes=[_bbox(1, 48, 121, 420, 143)],
        ),
        Answer(
            id="date",
            question=f"What is the issue date on document {code}?",
            answer=issue_date,
            answer_type="date",
            answer_aliases=[issue_date, f"{index + 1:02d}/02/2026"],
            language="en",
            answering_pages=[1],
            answer_bboxes=[_bbox(1, 48, 149, 420, 171)],
        ),
        Answer(
            id="total",
            question=f"What is the total in INR on document {code}?",
            answer=formatted,
            answer_type="currency",
            answer_aliases=[formatted, indian, f"INR {indian}"],
            language="en",
            answering_pages=[1],
            answer_bboxes=[_bbox(1, 48, 177, 420, 199)],
        ),
    ]
    if category == "bilingual":
        answers[3] = Answer(
            id="total",
            question=f"दस्तावेज़ {code} की कुल राशि क्या है?",
            answer=formatted,
            answer_type="currency",
            answer_aliases=[formatted, indian, f"INR {indian}"],
            language="hi",
            answering_pages=[1],
            answer_bboxes=[_bbox(1, 48, 177, 420, 199)],
        )
    if tables:
        item_row = 6 if page_count == 2 else 4
        answer_page = 2 if page_count == 2 else 1
        answer_top = 220 if page_count == 2 else 505 if category == "merged_table" else 475
        answers.append(
            Answer(
                id="item_amount",
                question=f"On document {code}, what is the amount for Fake item {item_row}?",
                answer=str(item_row * 125),
                answer_type="number",
                answer_aliases=[str(item_row * 125)],
                language="en",
                answering_pages=[answer_page],
                answer_bboxes=[_bbox(answer_page, 355, answer_top, 460, answer_top + 21)],
            )
        )
    return raw, pages, tables, answers


def build_document(category: str, index: int, font_path: Path | None) -> tuple[bytes, GroundTruth]:
    degradation = None
    if category == "scan":
        level = (index // 2 + index % 2) % 4
        degradation = Degradation(
            rotation_deg=(-2.0, 0.0, 3.0, 6.0)[level],
            noise_level=(0.1, 0.3, 0.5, 0.7)[level],
            dpi=(130, 110, 90, 75)[level],
            blur=(0.2, 0.5, 0.8, 1.1)[level],
        )
    raw, pages, tables, answers = _pdf_bytes(category, index, font_path, degradation)
    document_id = f"synthetic-{category}-{index:02d}"
    truth = GroundTruth(
        document_id=document_id,
        source_file=f"pdf/{document_id}.pdf",
        category=category,  # type: ignore[arg-type]
        split="dev" if index % 2 == 0 else "test",
        seed=SEED,
        pages=pages,
        tables=tables,
        questions=answers,
        degradation=degradation,
        content_hash=hashlib.sha256(raw).hexdigest(),
    )
    return raw, truth


def generate(output_dir: Path, font_path: Path | None) -> dict[str, Any]:
    pdf_dir = output_dir / "pdf"
    truth_dir = output_dir / "ground_truth"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, str]] = []
    for category in CATEGORIES:
        for index in range(8):
            raw, truth = build_document(category, index, font_path)
            pdf_path = output_dir / truth.source_file
            pdf_path.write_bytes(raw)
            truth_path = truth_dir / f"{truth.document_id}.json"
            truth_path.write_text(truth.model_dump_json(indent=2) + "\n", encoding="utf-8")
            entries.append(
                {
                    "document_id": truth.document_id,
                    "pdf": truth.source_file,
                    "ground_truth": str(truth_path.relative_to(output_dir)),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
    manifest: dict[str, Any] = {
        "generator_version": GENERATOR_VERSION,
        "seed": SEED,
        "pdf_metadata": {
            "creation_date": "2000-01-01T00:00:00Z",
            "producer": "Unmess synthetic generator",
        },
        "font_sha256": hashlib.sha256(font_path.read_bytes()).hexdigest() if font_path else None,
        "documents": entries,
    }
    (output_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("eval/datasets"))
    parser.add_argument(
        "--font", type=Path, default=Path("eval/datasets/.font-cache/NotoSansDevanagari.ttf")
    )
    args = parser.parse_args()
    if not args.font.is_file():
        parser.error("Noto font missing: run scripts/pull_font.sh or pass --font")
    manifest = generate(args.output_dir, args.font)
    print(f"Generated {len(manifest['documents'])} synthetic PDFs")


if __name__ == "__main__":
    main()
