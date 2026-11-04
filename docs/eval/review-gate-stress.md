# Review gate synthetic DEV stress test

Run `uv run python -m eval.review_gate_stress --output docs/eval/review-gate-stress.json` from the repository root to regenerate this report.

These fixtures inject parser output for six error categories at three document sizes, each paired with a correct control. The content and table regions are synthetic. The current scorer and review gate run on every page. The reference data and constructed inputs are in `eval/review_gate_stress.py`.

Accuracy follows the frozen runner's composite. It uses whitespace-normalized 1 - CER, averaged with table-cell F1 when a reference table exists. A page is bad below 0.90. Every parser output claims confidence 1.0. The fixture source features represent clean scanned pages with no embedded text.

The 95% percentile intervals use the existing document bootstrap with 2,000 draws and seed 20261103. These intervals describe resampling this fixed synthetic set. Undefined-denominator draws are skipped. The JSON records valid draw counts. Paired templates limit diversity. Real-parser and real-document validation requires separate evidence.

| Category | Pages | Bad | TP | FP | FN | TN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Overall | 36 | 18 | 6 | 0 | 12 | 18 | 1.000 | 0.333 |
| ocr_corruption | 6 | 3 | 3 | 0 | 0 | 3 | 1.000 | 1.000 |
| wrong_table_cells | 6 | 3 | 0 | 0 | 3 | 3 | undefined | 0.000 |
| missed_line_items | 6 | 3 | 0 | 0 | 3 | 3 | undefined | 0.000 |
| bilingual_field_errors | 6 | 3 | 0 | 0 | 3 | 3 | undefined | 0.000 |
| empty_parse | 6 | 3 | 3 | 0 | 0 | 3 | 1.000 | 1.000 |
| misleading_confidence | 6 | 3 | 0 | 0 | 3 | 3 | undefined | 0.000 |

## Overall confidence intervals

- Precision [1.0, 1.0]
- Recall [0.125, 0.5625]

## Misclassified cases

- `wrong_table_cells-3-fault` — false negative, accuracy 0.750, quality 1.000, reasons [].
- `missed_line_items-3-fault` — false negative, accuracy 0.545, quality 0.932, reasons [].
- `bilingual_field_errors-3-fault` — false negative, accuracy 0.646, quality 1.000, reasons [].
- `misleading_confidence-3-fault` — false negative, accuracy 0.000, quality 1.000, reasons [].
- `wrong_table_cells-5-fault` — false negative, accuracy 0.750, quality 1.000, reasons [].
- `missed_line_items-5-fault` — false negative, accuracy 0.567, quality 0.983, reasons [].
- `bilingual_field_errors-5-fault` — false negative, accuracy 0.615, quality 1.000, reasons [].
- `misleading_confidence-5-fault` — false negative, accuracy 0.000, quality 1.000, reasons [].
- `wrong_table_cells-8-fault` — false negative, accuracy 0.750, quality 1.000, reasons [].
- `missed_line_items-8-fault` — false negative, accuracy 0.631, quality 1.000, reasons [].
- `bilingual_field_errors-8-fault` — false negative, accuracy 0.596, quality 1.000, reasons [].
- `misleading_confidence-8-fault` — false negative, accuracy 0.000, quality 1.000, reasons [].

## Configuration

```json
{
  "quality_review_threshold": 0.7,
  "quality_visual_noise_threshold": 0.85,
  "parser_table_likelihood_threshold": 0.55,
  "parser_garbled_ratio_threshold": 0.1
}
```

The companion JSON includes every outcome, quality signal and per-category interval.
