"""Small, synthetic-only document demo shared by the CLI and public web page."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PIL import Image

from unmess.chunking.structure_aware import chunk_pages
from unmess.parsing.pymupdf_parser import PyMuPDFParser
from unmess.provenance.citations import render_highlight, source_region
from unmess.store.dedupe import hash_file, hash_page

ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_INVOICES = {
    code: ROOT / f"eval/datasets/pdf/synthetic-gst_invoice-{code}.pdf"
    for code in ("00", "01", "02")
}


@dataclass(frozen=True)
class InvoiceDemoResult:
    pdf: Path
    parser_name: str
    seller: str
    total: str
    chunk_id: str
    page_number: int
    highlighted_page: Image.Image | None


def run_invoice_demo(code: str = "00", *, highlight: bool = False) -> InvoiceDemoResult:
    """Run the real extraction and citation path on an allowlisted fictional invoice."""
    try:
        pdf = SYNTHETIC_INVOICES[code]
    except KeyError as exc:
        raise ValueError("choose one of the bundled synthetic invoices") from exc

    parser = PyMuPDFParser()
    with pymupdf.open(pdf) as document:
        page_count = len(document)
    pages = [parser.parse_page(pdf, number) for number in range(1, page_count + 1)]
    page_hashes = {page.page_number: hash_page(page.text.encode()) for page in pages}
    chunks = chunk_pages(pages, file_hash=hash_file(pdf), page_hashes=page_hashes)
    invoice = next(chunk for chunk in chunks if "Total INR:" in chunk.markdown)
    region = source_region(invoice)
    seller = next(
        line for line in invoice.markdown.splitlines() if line.startswith("Fictional seller:")
    )
    total = next(line for line in invoice.markdown.splitlines() if line.startswith("Total INR:"))
    page_number = region.page_numbers[0]
    highlighted_page = render_highlight(pdf, region, page_number) if highlight else None

    return InvoiceDemoResult(
        pdf=pdf,
        parser_name=parser.name,
        seller=seller,
        total=total,
        chunk_id=invoice.chunk_id,
        page_number=page_number,
        highlighted_page=highlighted_page,
    )
