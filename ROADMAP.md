# Roadmap

Each phase ends with relevant checks, a summary, explicit approval, and then one commit. Work
does not proceed into the next phase without approval.

## Phase 0 — foundation

Repository scaffold, project contracts, dependency and Compose configuration, CI, contribution
guidance, and architecture decisions.

## Phase 1 — evaluation first

Typed domain models and configuration; deterministic synthetic documents and ground truth;
all metrics and baselines; an end-to-end evaluation runner and baseline report.

## Phase 2 — parsing and trust

PyMuPDF, Docling, and local VLM adapters; page features and routing; quality scoring and review
gates; routing-threshold and failure-path tests.

## Phase 3 — chunks and retrieval

Structure-aware chunking, atomic table representations, provenance, hashing/deduplication,
dense and sparse embeddings, Qdrant RRF retrieval, and optional local reranking.

## Phase 4 — asynchronous service

FastAPI endpoints, Arq workers, job lifecycle, incremental ingestion, and structured timing
spans. The request process only validates/enqueues parsing work.

## Phase 5 — review UI

Streamlit Upload, Review Queue, and Search Playground pages, including parser/quality details
and cited source-region highlighting.

## Phase 6 — agent access and release proof

Official Python MCP SDK tools, end-to-end integration coverage, full evaluation, README results
drawn only from that run, and clean-clone verification of `make up`.
