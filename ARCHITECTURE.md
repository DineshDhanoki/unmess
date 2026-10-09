# Architecture

## Goals and boundaries

Unmess orchestrates existing parsers; it does not rebuild PDF parsing or OCR. Its value is
page-level routing, measurable quality, durable provenance, hybrid retrieval, incremental
processing, and agent access. Document bytes and model calls remain local by default, and no
component may make non-localhost network calls during document processing.

## Data flow

1. FastAPI validates an ingestion request, stores the source safely, enqueues an Arq job, and
   immediately returns a job identifier.
2. A worker hashes the file, detects unchanged work, renders pages when needed, and computes
   page features.
3. The router selects PyMuPDF for clean digital pages, Docling for layout/table complexity,
   and an Ollama vision model for scans or failed/low-confidence parses. It records the parser
   and rationale per page.
4. Quality scoring combines coverage, garbling, table consistency, available OCR confidence,
   and cheap parser disagreement. Gates send weak pages to human review.
5. Structure-aware chunking keeps tables atomic, retains headings/lists/captions, and attaches
   source page and bounding-box provenance.
6. Dense and sparse vectors are stored in Qdrant. Retrieval fuses rankings with reciprocal
   rank fusion (RRF) and may apply a configurable local cross-encoder reranker.
7. API, Streamlit, and MCP surfaces return citations with every retrieval result.

## Components

- `src/unmess/parsing`: parser interfaces, adapters, feature extraction, and routing.
- `src/unmess/quality`: scoring signals and review gates.
- `src/unmess/chunking`: document-aware chunks and table representations.
- `src/unmess/provenance`: citation records and source highlighting.
- `src/unmess/embeddings`, `store`, `retrieval`: vectors, persistence, fusion, and reranking.
- `src/unmess/api`, `workers`: thin request layer and asynchronous CPU/GPU work.
- `src/unmess/mcp_server`, `ui`: agent and human workflows.
- `eval`: synthetic ground truth, baselines, metrics, and reproducible reports.

## Deployment and configuration

Configuration comes from environment variables through `pydantic-settings`. Ollama model
names, routing thresholds, quality gates, chunk sizes, service URLs, and reranking are never
hardcoded. Qdrant and Redis are the only active Phase 0 Compose services; application services
are defined under the `app` profile for later phases.

See the accepted records in `docs/decisions/` for architectural rationale.

## Phase 2 page routing and quality

`Parser.parse_page(pdf, page_number)` returns a `ParsedPage` with source boxes, text, structured
tables, parser name, elapsed time, and an explicit success or failure. The router computes
embedded-text density, image coverage, scan and table likelihood, skew, garbling, dominant
script, and layout complexity. It sends a scan or low-text page to local Ollama vision, a
table-likely or complex page to Docling, and a clean digital page to PyMuPDF. A failed or
below-gate cheap parse gets one vision escalation. Each attempt and the final route reason are
retained. Unavailable parsers become failed attempts and failed pages, not missing records.

The page score is a weighted mean of applicable signals; absent signals are omitted and the
remaining weights renormalized:

| Signal | Weight | Interpretation |
|---|---:|---|
| Text coverage | 0.35 | Parsed non-space characters versus embedded source text, or a small scan-page floor. It never uses evaluation ground truth. |
| Character integrity | 0.25 | One minus the parsed garbled-character ratio. |
| Table consistency | 0.20 | Nonempty, nonoverlapping structured cells when page features predict a table. |
| Parser confidence | 0.10 | Parser-provided value, when available. |
| Parser agreement | 0.10 | Word-set overlap with embedded text only when a cheap second opinion has enough text. |

Failure scores zero. Review reasons include `parser_failed`, `below_quality_threshold`,
`empty_text`, `table_not_recovered`, and `garbled_text`. Thresholds are environment settings;
the evaluation's dev-tuned copy is frozen in `eval/config/phase2_frozen.toml` before the test
split runs. Vision requests use a strict JSON envelope with Markdown text and structured
blocks/tables. Successful responses are cached by page-image hash, model tag, and prompt
version under the ignored local cache directory. Only local Ollama hosts are accepted.
