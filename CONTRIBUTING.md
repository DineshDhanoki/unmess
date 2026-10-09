# Contributing

## Setup

Prerequisites are Python 3.11 or 3.12, `uv`, Docker with Compose, and Git.

```bash
make setup
make lint
make format-check
make typecheck
make test
```

Heavy parser/model packages are opt-in:

```bash
uv sync --extra parsers
```

Do not install them merely to run the light CI suite. Start Phase 0 infrastructure with
`make up`; this starts Qdrant and Redis only.

## Change rules

- Work in the roadmap phases and do not cross a phase boundary without approval.
- Add type hints to every function and keep modules focused.
- Program against interfaces for parsers, embedders, and stores.
- Add tests for behavior and configuration thresholds.
- Keep model names and operational thresholds configurable.
- Make no non-localhost network calls from the ingestion pipeline.
- Never commit secrets, `.env`, private documents, or real personal/financial data.
- Use generated synthetic fixtures only.
- Add an ADR for architectural changes and update affected documentation.
- Never state benchmark accuracy or speed without a reproducible evaluation report.

## Definition of done

Ruff lint and format checks are clean, mypy is clean, tests pass, documentation matches the
behavior, and architectural changes have an ADR. Evaluation-affecting changes also regenerate
the relevant report; claims that cannot be supported are removed.
