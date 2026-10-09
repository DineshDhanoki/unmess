# Evaluation workspace

`datasets/MANIFEST.json` lists 56 committed synthetic PDFs and their validated JSON ground
truth. `metrics/` contains pure scoring functions; `baselines/` contains PyMuPDF, optional
Docling, and the unimplemented Unmess adapter. `run_eval.py` verifies the manifest, evaluates
dev and test separately, and writes `results/latest.md` and `latest.json`.

Run `bash scripts/pull_font.sh`, then `uv run python scripts/make_synthetic_docs.py` to
regenerate the corpus byte-for-byte. Run `make eval` for a report. See `EVAL.md` for definitions,
the relevance rule, and corpus limitations. `results/baseline-phase1.md` is the committed
measured baseline report; Unmess has no measured values in Phase 1.

For Phase 2, `make eval` evaluates dev parsing and score calibration. After committing the
frozen thresholds and reaching a clean working tree, run `make eval-test` once. It evaluates
test parsing and includes dev calibration in the generated report. Vision outputs are cached
locally; missing Docling or Ollama is reported as failed pages, not omitted.
