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
