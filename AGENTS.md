# Agent guide

## Mission and positioning

Unmess (codename DocuForge) is a local-first ingestion layer that turns messy real-world
documents into structured, citable, retrieval-ready chunks and measures how trustworthy that
output is.

Unmess is **not** another PDF-to-Markdown parser. Mature parsers already exist, including
Docling, Marker, and PyMuPDF. Wrap them; do not reimplement PDF parsing or OCR. Unmess adds:

1. Routing: use a cheap parser for clean pages and a heavy local VLM only for hard pages.
2. Self-scoring: score every page and chunk and flag weak parses for review.
3. Provenance: link every chunk to source file, page, and bounding box.
4. Evaluation: reproducibly measure parsing and retrieval against baselines.
5. Niche coverage: Indian invoices, GST filings, scanned receipts, and bilingual English/Hindi
   documents.
6. Agent access: expose direct ingestion and query through an MCP server.

Do not claim accuracy that the evaluation harness did not produce.

## Commands

- Setup: `make setup` (heavy integrations: `uv sync --extra parsers`)
- Lint/format: `make lint` and `make format-check`
- Typecheck: `make typecheck`
- Test: `make test`
- Evaluate: `make eval` (available from Phase 1)
- Run API: `make run` (available from Phase 4)
- Start infrastructure: `make up`

## Coding rules

- Use type hints everywhere and strict mypy. Prefer small, cohesive modules.
- Define interfaces for parsers, embedders, and stores; integrations depend on contracts.
- Model providers and all thresholds/settings come from environment-backed configuration.
- Make no network calls outside localhost. Keep document content local by default.
- Never put secrets in source, tests, logs, fixtures, or documentation.
- Keep the API thin: CPU/GPU parsing work belongs in Arq workers.
- Preserve page/bounding-box provenance through every transformation.

## Definition of done

Ruff is clean, mypy is clean, tests pass, documentation is updated, and any architectural
change has an ADR. Run checks relevant to the current phase before reporting completion.

## Honesty and data safety

- Never invent benchmark numbers or silently extrapolate from partial results.
- Every README performance claim must cite an evaluation result or be removed.
- Never commit real personal, financial, customer, invoice, receipt, or tax documents.
- Use synthetic data only, with visibly fictional identities and identifiers.

## Working style

Work only in the approved roadmap phase. At its end, run relevant checks, summarize changes and
results, and wait for approval. Make one phase commit only after approval to perform that phase;
never begin the next phase automatically.
