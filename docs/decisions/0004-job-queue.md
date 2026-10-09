# ADR 0004: Keep parsing outside the HTTP process

- Status: Accepted
- Date: 2026-10-10

## Context

Parsing and model inference are CPU/GPU-bound, long-running, and failure-prone. Running them in
request handlers risks timeouts, resource contention, and lost status.

## Decision

FastAPI validates ingestion requests, enqueues Arq jobs in Redis, and returns a job identifier.
Workers own parsing, chunking, embedding, storage, retries, and structured timing. Persistent
job state backs status endpoints and the UI.

## Consequences

Redis is required and job transitions need explicit tests. The separation supports retries and
independent scaling while preserving a responsive API.
