"""Show today's local parsing and citation path on a fictional invoice.

Run from the checkout root with ``uv run python -m scripts.demo``.
This intentionally uses a bundled synthetic PDF; it makes no network calls.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

from unmess.chunking.structure_aware import chunk_pages
from unmess.parsing.pymupdf_parser import PyMuPDFParser
from unmess.provenance.citations import source_region
from unmess.store.dedupe import hash_file, hash_page

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "eval/datasets/pdf/synthetic-gst_invoice-00.pdf"


def main() -> None:
    parser = PyMuPDFParser()
    with pymupdf.open(SAMPLE) as document:
        page_count = len(document)
    pages = [parser.parse_page(SAMPLE, number) for number in range(1, page_count + 1)]
    page_hashes = {page.page_number: hash_page(page.text.encode()) for page in pages}
    chunks = chunk_pages(pages, file_hash=hash_file(SAMPLE), page_hashes=page_hashes)
    invoice = next(chunk for chunk in chunks if "Total INR:" in chunk.markdown)
    region = source_region(invoice)
    seller = next(
        line for line in invoice.markdown.splitlines() if line.startswith("Fictional seller:")
    )
    total = next(line for line in invoice.markdown.splitlines() if line.startswith("Total INR:"))

    print("Unmess local demo — fictional invoice; no upload or model required")
    print(f"Input: {SAMPLE.relative_to(ROOT)}")
    print(f"Parser: {parser.name}")
    print(f"Extracted: {seller}; {total}")
    print(f"Citable chunk: {invoice.chunk_id} (page {region.page_numbers[0]})")
    print("Current scope: extraction, chunking, and source provenance. Search and UI are planned.")


if __name__ == "__main__":
    main()
