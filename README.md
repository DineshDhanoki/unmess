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

Phase 0 provides the repository contract, architecture decisions, development tooling, and
local Qdrant/Redis infrastructure. Pipeline and benchmark implementations arrive in later
phases described in [ROADMAP.md](ROADMAP.md).

No accuracy or performance claims are made yet. Future claims must link to a dated report
created by the evaluation harness and identify the exact models used.

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
