# Evaluation workspace

Phase 1 will add the deterministic generator, versioned ground truth, metrics, three comparable
systems, and `eval/run_eval.py`. The intended command is `make eval`; reports will be written as
`eval/results/latest.json` and `eval/results/latest.md`.

Generated datasets and normal run outputs are ignored. A deliberately empty sample report is
committed to document the required metadata and table shape without suggesting measured results.
