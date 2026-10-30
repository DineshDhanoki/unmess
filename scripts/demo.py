"""Show today's local parsing and citation path on a fictional invoice.

Run from the checkout root with ``uv run python -m scripts.demo``.
This intentionally uses a bundled synthetic PDF; it makes no network calls.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from unmess.demo import ROOT, run_invoice_demo


def main() -> None:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument(
        "--highlight-output",
        type=Path,
        help="optionally save the cited synthetic source page as a highlighted PNG",
    )
    args = argument_parser.parse_args()

    result = run_invoice_demo(highlight=args.highlight_output is not None)

    print("Unmess local demo — fictional invoice; no upload or model required")
    print(f"Input: {result.pdf.relative_to(ROOT)}")
    print(f"Parser: {result.parser_name}")
    print(f"Extracted: {result.seller}; {result.total}")
    print(f"Citable chunk: {result.chunk_id} (page {result.page_number})")
    print("Current scope: extraction, chunking, and source provenance. Search and UI are planned.")
    if args.highlight_output is not None:
        image = result.highlighted_page
        assert image is not None
        args.highlight_output.parent.mkdir(parents=True, exist_ok=True)
        image.save(args.highlight_output, format="PNG")
        print(f"Highlighted synthetic source page: {args.highlight_output}")


if __name__ == "__main__":
    main()
