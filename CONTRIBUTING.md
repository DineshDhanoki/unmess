# Contributing to Unmess

Thanks for helping make document processing easier to inspect and trust. You can start with documentation, a synthetic fixture, or a focused test; you do not need a GPU, Docker, or a private document.

## First ten minutes

Install Git, Python 3.11 or 3.12, and [uv](https://docs.astral.sh/uv/). From the repository root:

```bash
uv sync --dev --locked
uv run python -m scripts.demo
```

The demo reads a fictional invoice bundled in `eval/datasets/pdf/` and prints an extracted total with its source page. It runs locally without Docker or a model download. Compare the output with the [sample invoice](eval/datasets/pdf/synthetic-gst_invoice-00.pdf).

For the full checks, fetch the pinned test font once, then run:

```bash
bash scripts/pull_font.sh
make lint
make format-check
make typecheck
make test
```

The font fetch needs network access during setup. Document processing in Unmess stays local. Heavy parser and model packages are optional (`uv sync --extra parsers`). Docker is needed only for infrastructure work: `make up` starts Qdrant and Redis, not an application server.

## Find a useful task

Look for a [good first issue](https://github.com/DineshDhanoki/unmess/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) or browse all [open issues](https://github.com/DineshDhanoki/unmess/issues). An issue should have a clear outcome and a way to check it. Comment on the issue to coordinate if the scope is unclear. For open questions and ideas, use [Discussions](https://github.com/DineshDhanoki/unmess/discussions/20). A small, focused PR is welcome; reference the issue in its description and explain how you tested the change.

For your first PR, a corrected setup step, a clearer explanation, or a synthetic regression case is valuable. You do not need to take on an entire roadmap phase. For a new architecture or a change to evaluation methodology, discuss the approach in an issue before implementing it.

## Change rules

- Keep type hints on functions and add tests for changed behavior or configuration thresholds.
- Preserve file, page, and bounding-box provenance through transformations.
- Keep model names and operational thresholds configurable.
- Make no non-localhost network calls from the document processing pipeline.
- Never commit secrets, `.env`, private documents, or real personal or financial data. Use generated synthetic fixtures only.
- For an opt-in local trial with real documents, follow the [privacy-safe validation protocol](docs/eval/real-document-validation-protocol.md). Keep inputs, derivatives, consent records, and document-level results out of Git.
- Add an ADR for architectural changes. Never state benchmark accuracy or speed without a reproducible evaluation report.

## When a PR is ready

The CI checks are Ruff lint and format, mypy, and pytest on Python 3.11 and 3.12. Run the relevant checks locally, fill out the PR template, and say what is still untested. Evaluation-affecting changes also need the relevant report regenerated, or unsupported claims removed. A maintainer reviews and merges accepted PRs.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md). For a security concern, use the private channel in [SECURITY.md](SECURITY.md).
