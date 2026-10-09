# Evaluation workspace

`datasets/MANIFEST.json` lists 56 committed synthetic PDFs and their validated JSON ground
truth. `metrics/` contains pure scoring functions; `baselines/` contains PyMuPDF, optional
Docling, and the unimplemented Unmess adapter. `run_eval.py` verifies the manifest, evaluates
dev and test separately, and writes `results/latest.md` and `latest.json`.

Run `bash scripts/pull_font.sh`, then `uv run python scripts/make_synthetic_docs.py` to
regenerate the corpus byte-for-byte. Run `make eval` for a report. See `EVAL.md` for definitions,
the relevance rule, and corpus limitations. `results/baseline-phase1.md` is the committed
measured baseline report; Unmess has no measured values in Phase 1.
