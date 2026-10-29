# Architecture

## Goals and boundaries

Unmess orchestrates existing parsers; it does not rebuild PDF parsing or OCR. Its value is
page-level routing, measurable quality, durable provenance, hybrid retrieval, incremental
processing, and agent access. Document bytes and model calls remain local by default, and no
component may make non-localhost network calls during document processing.

## Target data flow

This is the intended end-to-end design, not a description of a running service. The repository
currently contains parsing, routing, quality, chunking, provenance, and evaluation components.
The API, asynchronous ingestion service, retrieval pipeline, UI, and MCP surface remain planned.

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
| Text coverage | 0.25 | Parsed non-space characters versus embedded source text, or a small scan-page floor. It never uses evaluation ground truth. |
| Character integrity | 0.10 | One minus the parsed garbled-character ratio. |
| Character plausibility | 0.20 | Share of long alphabetic tokens with plausible vowels or Devanagari script; no task-specific corruption tokens. |
| Script plausibility | 0.05 | Share of letters in Latin or Devanagari script. |
| Text–ink alignment | 0.15 | Share of embedded word boxes containing rendered ink; PyMuPDF text-layer output only. |
| Table consistency | 0.15 | Nonempty, nonoverlapping structured cells when page features predict a table. |
| Parser confidence | 0.05 | Parser-provided value, when available. |
| Parser agreement | 0.05 | Word-set overlap with embedded text only when that text passes plausibility and ink checks. |
| Visual clarity | 0.30 | One minus normalized rendered-image noise, applied only to image-dominant pages. |
| Cross-page table continuity | 0.40 | Zero when consecutive pages are independently table-likely, because continuation structure is not yet verified. |

Failure scores zero. Review reasons include `parser_failed`, `below_quality_threshold`,
`empty_text`, `table_not_recovered`, `garbled_text`,
`cross_page_table_continuity_unverified`, and `visually_degraded_source`. The continuity signal
is review-only: it does not replace a successful structured parse with VLM output. Routing also
measures rendered ink inside image regions that is not covered by embedded word boxes. This
generic signal detects mixed visible content such as raster text, stamps, and signatures without
checking a language, category, or generator-specific coordinate. Thresholds are environment settings;
Phase 2b tunes only `eval/config/phase2b_dev.toml` until a new freeze is approved. Vision
requests use a strict JSON envelope containing Markdown text. The fallback attaches a
full-page bbox and does not claim cell geometry from the VLM; structured tables come from
Docling when available. Successful vision responses are cached by page-image hash, model tag,
and prompt version under the ignored local cache directory. Cache reads can be disabled for
controlled cold timing while successful responses are still written for audit/resume. Only local Ollama hosts are
accepted. Preflight exercises all three parsers before test-split evaluation; the old freeze
is superseded.
