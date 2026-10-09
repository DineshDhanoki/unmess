# ADR 0003: Fuse dense and sparse retrieval with RRF

- Status: Accepted
- Date: 2026-10-10

## Context

Semantic embeddings help with paraphrases, while sparse matching remains strong for invoice
numbers, tax identifiers, names, and exact terminology. Messy regional documents need both.

## Decision

Store dense and sparse vectors in Qdrant and retrieve candidates from both. Fuse rankings with
reciprocal rank fusion. Make a local cross-encoder reranker optional and configurable. Every
result includes its text and source citation.

## Consequences

RRF avoids assuming comparable score scales and gives a transparent baseline. Storage and
query logic are more involved; evaluation must expose dense, sparse, fused, and reranked result
quality separately where applicable.
