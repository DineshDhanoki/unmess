# Unmess

Unmess (codename **DocuForge**) is a local-first ingestion layer that turns messy,
real-world documents into structured, citable, retrieval-ready chunks—and measures how
trustworthy that output is.

Unmess is not another PDF-to-Markdown parser. It wraps mature tools such as Docling and
PyMuPDF, routes each page to the least expensive suitable parser, falls back to a local vision
model for difficult pages, scores output quality, preserves provenance, and evaluates the
whole pipeline against reproducible baselines.

The initial focus is messy, region-specific material: Indian invoices, GST-style filings,
scanned receipts, and bilingual English/Hindi documents. An HTTP API, Streamlit review UI,
and MCP server will expose ingestion and retrieval without sending documents outside the
local environment.

## Status

Phase 2 adds page routing, parser adapters, quality scoring, and parsing evaluation. Docling is
optional and the complete Unmess retrieval pipeline arrives in later phases
described in [ROADMAP.md](ROADMAP.md).

The Phase 1 synthetic corpus and baseline harness are available. Its measured baseline report
is in [eval/results/baseline-phase1.md](eval/results/baseline-phase1.md). It contains no Unmess
pipeline score; that pipeline is not implemented yet. Future performance claims must link to a
dated harness report and identify the models used.

The [Phase 2b dev report](eval/results/phase2b-dev.md) records measured page-level
results, including failed pages when optional backends are unavailable. Retrieval remains a
later phase.

The [Phase 2c DEV-only report](eval/results/phase2c-dev.md) expands the synthetic corpus,
corrects a merged-table scoring artifact, and compares routed parsing with Docling-only and
VLM-on-every-page. Its numbers are DEV measurements, not test-set claims; the expanded test
split remains locked pending a new threshold freeze.

## Quick start

Install Python 3.11 or 3.12, Docker, and
[uv](https://docs.astral.sh/uv/), then run:

```bash
make setup
make lint
make typecheck
make test
make up
```

`make up` currently starts only Qdrant and Redis. The API, worker, and UI are reserved behind
the Compose `app` profile until their implementation phases. Heavy parser/model packages are
not installed by default; later, use `uv sync --extra parsers` when those integrations are
needed.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system design, [EVAL.md](EVAL.md) for the
measurement contract, and [CONTRIBUTING.md](CONTRIBUTING.md) before contributing.

## License

Apache License 2.0. See [LICENSE](LICENSE).
