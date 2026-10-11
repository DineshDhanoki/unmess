# Evaluation workspace

`datasets/MANIFEST.json` lists 86 committed synthetic PDFs and their validated JSON ground
truth. `metrics/` contains pure scoring functions; `baselines/` contains PyMuPDF, optional
Docling, VLM-every-page, and the Unmess parsing adapter. `run_eval.py` verifies the manifest,
evaluates DEV only until a new freeze is approved, and writes `results/latest.md` and
`latest.json`.

Run `bash scripts/pull_font.sh`, then `uv run python scripts/make_synthetic_docs.py` to
regenerate the corpus byte-for-byte. Run `make eval` for a report. See `EVAL.md` for definitions,
the relevance rule, and corpus limitations. `results/baseline-phase1.md` is the committed
measured baseline report; Unmess has no measured values in Phase 1.

For Phase 2b, run `make preflight` first, then `make eval` for dev-only parsing and
successful-page score calibration. The old freeze is superseded. Only after approval of a new
freeze, committing it, reaching a clean working tree, and passing preflight should
`make eval-test` run once. It evaluates
test parsing and includes dev calibration in the generated report. Vision outputs are cached
locally; missing Docling or Ollama is reported as failed pages, not omitted.

Phase 2c compares the original 28 DEV documents, 15 new DEV documents, and their combined
43-document set. It adds all-page CER/WER, VLM-every-page, and metric-specific denominators.
The expanded test ground truth is not read until a new threshold freeze is approved.
