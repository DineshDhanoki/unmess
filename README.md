# Unmess

[![CI](https://github.com/DineshDhanoki/unmess/actions/workflows/ci.yml/badge.svg)](https://github.com/DineshDhanoki/unmess/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**A number on a scanned invoice is easy to extract. Knowing whether it is right—and where it came from—is the hard part.**

Imagine asking a document system for a total from a long invoice. The answer looks plausible, but a table continued on the next page. Was that page missed? Did the parser merge two unrelated tables? Can you point a reviewer to the exact source page without uploading the invoice to someone else's server?

Unmess is an open-source, local-first project exploring that problem. It uses existing parsers, keeps source locations attached to extracted chunks, and evaluates failures instead of hiding them behind a polished answer. The longer-term goal is private document search with citations and a review path for uncertain pages. **Search, an API, and a review UI are not available yet.**

## See what works today

This small demo uses a **fictional GST-style invoice already in the repo**. It runs the current PyMuPDF adapter, chunker, and citation code. No Docker, model download, account, or real document is needed.

From a fresh clone, install [uv](https://docs.astral.sh/uv/) and Python 3.11 or 3.12, then run:

```bash
uv sync --dev --locked
uv run python -m scripts.demo
```

You should see output like:

```text
Unmess local demo — fictional invoice; no upload or model required
Input: eval/datasets/pdf/synthetic-gst_invoice-00.pdf
Parser: pymupdf
Extracted: Fictional seller: Demo Vendor 00; Total INR: 10,000
Citable chunk: text-9f029e03df396fd9b1da (page 1)
Current scope: extraction, chunking, and source provenance. Search and UI are planned.
```

The total and page reference come from the parsed PDF, not a hard-coded answer. Try opening the [sample invoice](eval/datasets/pdf/synthetic-gst_invoice-00.pdf) and comparing it with the output. The sample is synthetic; never commit a real invoice, receipt, ID, or customer document.

## The project, honestly

| Available in this repository | Still to build |
| --- | --- |
| PyMuPDF adapter, optional Docling and local vision adapters, page routing and quality signals | A complete ingestion service and background jobs |
| Structure-aware chunks, conservative table stitching, source page and region records | Hybrid retrieval, answer citations, and local reranking |
| Synthetic corpora, evaluation harnesses, and development reports | Review UI, MCP tools, and real-document validation results |

The [roadmap](ROADMAP.md) describes the planned sequence; [architecture](ARCHITECTURE.md) explains the design. Current measurements use synthetic data and have [known limitations](EVAL.md). In particular, no production accuracy or speed claim follows from these development reports. Optional parsers and local models require extra setup; the demo above deliberately avoids them.

## Build it with us

You can help without owning the whole architecture. A useful first contribution might clarify a confusing step, add one synthetic edge case, improve a regression test, or make a citation easier to inspect. Browse the [good first issues](https://github.com/DineshDhanoki/unmess/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) and the [first contribution guide](CONTRIBUTING.md). Comment on an issue if you want to coordinate, or open a focused PR that references it. We review the code and the evidence together.

Have a question or a story about an answer you could not verify? Join the [welcome discussion](https://github.com/DineshDhanoki/unmess/discussions/20).

The project especially needs people interested in document parsing, Python, evaluation, privacy, and bilingual or region-specific documents. You do **not** need to supply real documents. Every shared fixture must be synthetic.

## Deeper setup

The normal contribution checks are `make lint`, `make format-check`, `make typecheck`, and `make test`. The reproducibility tests need a pinned Noto Sans Devanagari font; run `bash scripts/pull_font.sh` first. Docker is only needed for infrastructure work: `make up` starts Qdrant and Redis, **not** a working Unmess app. See [CONTRIBUTING.md](CONTRIBUTING.md) for the exact path and [EVAL.md](EVAL.md) for evaluation rules.

Apache License 2.0. See [LICENSE](LICENSE).
