# Evaluation contract

## Corpus and splits

`scripts/make_synthetic_docs.py` originally generated 56 wholly fictional PDFs: eight each of clean
digital pages, degraded scans, receipts, GST-style invoices, merged-cell tables, tables spanning
two pages, and bilingual English/Hindi pages. Phase 2c expanded the corpus to 86 PDFs: ten
each for merged-cell, spanning-table, and bilingual cases, and eight each of three new
categories: `broken_text_layer`, `fake_text_layer_scan`, and `mixed_pages`. These new categories
are **synthetic approximations** of real-world failures, not samples from actual documents.
Every category remains approximately 50/50 `dev`/`test`. The fixed seed is `20261010`.
The generator records PDF SHA-256 hashes, version,
seed, fixed metadata, and font hash in `eval/datasets/MANIFEST.json`. The committed PDFs total
5,438,587 bytes; the whole committed dataset is 5,925,923 bytes in generator version 1.2.0.
The font is downloaded separately under the SIL
Open Font License and is not committed.

The corpus was expanded **after** the invalid first Phase 2 test run and **before any valid
test run**. The initial 28 DEV documents and the 15 newly added DEV documents are reported
as separate cohorts as well as together; the combined numbers must not be compared directly
with Phase 2b's 28-document results. New test PDFs are generated and hashed, but their ground
truth is not read by the DEV evaluation path. The old freeze remains superseded and test
evaluation is prohibited pending user approval of a new freeze.

Use `dev` to tune routing thresholds, chunk sizes, or other choices. **Never tune on `test`.**
The report presents test first and labels it as the headline split. Dev and test are evaluated
in separate retrieval pools, so documents from one split cannot be retrieved by the other.

Ground truth for each document contains one-based pages with `expected_text`, `language`, and
`is_ocr_page`; tables with `page_numbers`, cells, spans, and normalized page bounding boxes;
3–5 questions with `answer_type`, `answer_aliases`, `language`, answering pages and boxes; and
scan parameters (`rotation_deg`, `noise_level`, `dpi`, `blur`) where applicable. The `split` field
is `dev` or `test`. GSTINs and identities are visibly invalid and fictional.

For tables spanning pages, the visible header repeats on page two. Header cells repeat at row
index zero; data row indices continue from page one. `has_merged_cells` and `spans_pages` flags
must agree with the underlying cells and page count. Box coordinates are normalized to 0–1,
with the origin at the top left. A box must have positive area.

## Systems

- `pymupdf_fixed`: `page.get_text("text", sort=True)`, PyMuPDF's default
  `page.find_tables()` strategies converted to `Table`, and fixed 16-word windows with
  3-word overlap. It performs no OCR. A reference table with no detected table is a measured
  extraction failure, not an unsupported capability.
- `docling_only`: Docling with accurate TableFormer cell matching and forced full-page
  EasyOCR using `en` and `hi`, scale 3, and confidence threshold 0.5. Model downloads are
  disabled during evaluation, so local artifacts must already be present. This replaces the
  Phase 2c default RapidOCR configuration, which did not provide the requested explicit
  English/Hindi baseline.
- `vlm_every_page`: local Ollama vision extraction on every DEV page. Its cached Markdown
  pipe tables are converted into `Table` cell grids using the same response contract as the
  routed VLM parser; merged spans cannot be inferred from ordinary Markdown. Phase 2d reads
  the cache only: a cache miss is a page failure and no model request is made. Failures remain
  in all denominators.
- `unmess`: a registered `PipelineAdapter` placeholder. Phase 1 reports `not implemented yet`
  and `n/a` values. The full pipeline belongs to later phases.

Phase 2 replaces the placeholder in new runs with `unmess_parsing`: routing, page parsing, and
quality scoring only. The committed Phase 1 baseline report remains unchanged. The new parsing
report compares PyMuPDF, Docling, and Unmess on table F1, OCR CER, cheap-parser share, latency,
and failed-page rate. Phase 2c adds VLM-every-page and all-page text CER/WER. Retrieval metrics
are `n/a` for all Phase 2 systems until Phase 3.
Unavailable Docling and unreachable Ollama are counted as failed pages and listed by document
and page, including attempted parser errors.

Retrieval uses an in-memory BM25 index for every available parser, with the same question set
and split-specific corpus. It does not use Qdrant or Ollama in Phase 1.

## Metric definitions

The runner reports document-macro averages overall and by category, language, and scan
difficulty. `n/a` means the measure has no applicable reference or the system did not run.

The Phase 2d review-gate target is locked before evaluation. For each page, collapse all
whitespace in expected and parsed text, compute `text_accuracy = max(0, 1 - CER)`, and compute
page composite accuracy as follows:

- without a reference table: `composite = 1.0 * text_accuracy`;
- with a reference table: `composite = 0.5 * text_accuracy + 0.5 * table_cell_F1`.

A **bad page** is one whose composite accuracy is strictly below **0.90**. This cutoff and the
component weights must not be changed after inspecting gate results. Gate evaluation reports
the bad-page count, quality-score histogram, AUROC using `1 - quality_score` as badness,
review-flag precision/recall, and all confusion-matrix counts. If fewer than ten bad pages are
present, AUROC, precision, and recall are explicitly labeled unstable.

- **Table cell F1:** multiset matching of table ID, column, row span, column span,
  and stripped cell text after a single whole-table row-origin shift chosen to maximize
  matching cells. Missing rows and wrong spans still reduce precision/recall. This fixes the
  false zero caused when a parser omitted one merged heading and numbered all later rows
  from zero. Only documents with reference
  tables enter this average.
- **OCR CER:** Levenshtein character edits divided by reference characters on pages marked
  `is_ocr_page`. No extracted text therefore scores 1.0 on nonempty reference text.
- **All-page text CER/WER:** Levenshtein edits on characters or whitespace-delimited words,
  divided by the corresponding reference length, for **every** page. These apply to clean,
  receipt, table, mixed, and bilingual pages too. Hindi is additionally shown in the `hi`
  language group. Insertions can make either error rate exceed 1. Each report cell includes
  its own document and page denominator.
- **Recall@1/3 and MRR:** each question is a query. A retrieved chunk is relevant only when
  its document ID matches, it overlaps an answering page, and, if answer boxes exist, one of
  its boxes intersects an answer box. Recall@k is a binary hit per question. MRR is reciprocal
  rank of the first relevant chunk. Scores are averaged within each document, then across
  documents. Alias strings are preserved for later answer checking but do not change geometric
  retrieval relevance.
- **Table split rate:** fraction of reference tables whose nonempty cell text does not all
  appear in any single chunk. This is 1.0 if every table is split; lower is better.
- **Citation accuracy:** fraction of questions whose top-ranked chunk cites the correct
  document, answering page, and intersecting answer box when one exists.
- **Cheap parser share:** fraction of pages labeled `pymupdf` by the adapter. It measures route
  choice, not correctness.
- **Latency per page:** parser/extraction wall-clock seconds divided by page count, averaged by
  document. It excludes dataset generation and BM25 ranking. Compare only runs on similar
  hardware and dependency versions.

Scan difficulty is `low` for noise ≤ 0.2, `medium` for ≤ 0.5, and `high` otherwise; these
groups also vary in DPI and blur. The report includes a `not_scan` group for other documents.

## Superseded first Phase 2 test run

The first Phase 2 test-split run, using freeze commit
`caa7f35c2f46777eba1a690e0292dac1ea04fe39`, is **invalid as an assessment of the
routing design**: Docling's optional package/model artifacts were missing and Ollama was
unreachable. The run counted those pages as failures but could not measure the intended
backends. No routing or gate threshold was changed after seeing its test results. Its
report remains in `eval/results/phase2-parsing.md`, marked SUPERSEDED for audit. Phase 2b
requires `make preflight` to pass, dev-only tuning, and approval of a new freeze before
one replacement test run.

## Reproduce

From a clean clone with Python 3.11 or 3.12 and `uv`:

```bash
make setup
bash scripts/pull_font.sh
uv run python scripts/make_synthetic_docs.py
make eval
```

The font download is pinned to a Google Fonts revision. If network access is unavailable,
provide a local Noto Sans Devanagari font with `--font`. The generator never downloads a font
implicitly. `make eval` verifies every PDF hash against the manifest and writes
`eval/results/latest.json` and `latest.md` (both ignored by Git). The committed
`eval/results/baseline-phase1.md` is an actual run, including date, source commit, dirty-tree
flag, library versions, environment, model status, and separate dev/test tables.

For Phase 2b, `make preflight` verifies PyMuPDF, a real Docling parse using prefetched local
artifacts, localhost Ollama, the pulled `VISION_MODEL`, and a trivial model response.
`make eval` runs **dev only** using `eval/config/phase2b_dev.toml`. The runner refuses
`make eval-test` while the superseded freeze is active. After approval of a new freeze, it
will still refuse unless the freeze file is committed, the working tree is clean, preflight
passes, and no test page's initial route names an unavailable backend. The test report will
record that freeze hash, frozen values, vision model tag, and prompt version. The report
includes dev and test parsing results separately,
with category, language, and scan-difficulty breakdowns. It reports dev-only calibration as
Spearman rank correlation between page score and reference page accuracy, plus average accuracy
in score buckets `[0,.25)`, `[.25,.5)`, `[.5,.75)`, `[.75,1]`. Page accuracy is clipped
normalized-text similarity, averaged with page-level table F1 when a table is present. A
Calibration uses successfully parsed pages only and reports failed pages separately. It also
reports how many pages escalated and whether the reference page accuracy improved. Undefined
Spearman when all scores tie is reported as `n/a`, not zero. The dev-only threshold trials and
their measured effects are in `eval/TUNING_PHASE2B.md`.

The Phase 2 vision parser calls only local Ollama. Successful responses are cached under
`.cache/unmess/vlm` by raster-page SHA-256, model tag, and prompt version. No live service is
required for unit tests; the live Ollama smoke test is opt-in with
`uv run pytest -m integration`.
VLM-only text currently has a full-page bbox; it is coarse provenance, not precise highlighting.
The eval reports VLM attempts, cache hits, total VLM time, and pages per second.

Phase 2d additionally reports fixed-seed (`20261011`) percentile bootstrap 95% confidence
intervals from 2,000 whole-document resamples for all-page CER, WER, and table F1. Timing rows
label response-cache state. Only genuinely cold or cache-independent measurements support
cost comparisons; warm-cache measurements are retained as operational observations rather
than presented as cold latency.

## Limits

The documents deliberately use a small set of templates and fictional values. They are not a
representative sample of actual financial or personal records. The scan set varies degradation
parameters but does not capture every scanner artifact. Hindi appears as rasterized text, so
the cheap parser cannot extract it; its rendering depends on the pinned font and Pillow
version. Exact text and cell matching are strict. Bounding-box relevance rewards any geometric
intersection, not whether a reader would find the result useful. Reported numbers apply only
to this corpus, code revision, and environment.

## Phase 2c DEV-only audit trail

Visual inspection of `synthetic-merged_table-00` (DEV) found that the claimed merged heading
was drawn above the table border, while Docling and Unmess extracted all subsequent table
cells and numbered them from zero. The generator now boxes the merged heading as a real cell;
the metric aligns whole-table row origins without forgiving missing cells. The corrected
original 28-document DEV rerun changed merged-table F1 from 0.0000 to 1.0000 for both Docling
and Unmess. Overall table F1 changed from 0.5000 to 0.8333 for Docling and from 0.5417 to
0.8750 for Unmess. These are DEV-only, document-macro numbers from the corrected original
corpus, with unchanged routing thresholds. The pre-correction Phase 2b report is retained.
The fix lives in `scripts/make_synthetic_docs.py`; both splits' PDFs were regenerated. An
integration test rebuilds one DEV and one test document directly from the generator, compares
their bytes and MANIFEST hashes, and checks identical merged-heading box logic. It does not
read or score test outcomes.

The new scorer uses general character/script plausibility and rendered-ink/text-layer
alignment. It does not check for the generator's particular corruption strings. Score
calibration and every threshold trial must be evaluated on DEV only. The Phase 2c tuning log
is `eval/TUNING_PHASE2C.md`. The observed Spearman score/accuracy correlation is slightly
negative on the expanded DEV set, so these scores should be treated as review heuristics,
not calibrated probabilities. Cost figures disclose cache state; the routed and VLM-only
passes were not run under identical cold-cache conditions.

For the Phase 2d fairness audit, Docling's actual baseline configuration is forced full-page
EasyOCR with explicit `en` and `hi`, while the VLM prompt is script-neutral and requests every
visible word. The routed system still chooses PyMuPDF for the synthetic bilingual digital
pages and consequently omits the rasterized Hindi line; this is a routing limitation, not a
missing language setting in either heavy parser.
