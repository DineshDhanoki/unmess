# Phase 2e DEV-only tuning log

The test-run criteria were committed first in `e4e6a83`. No test ground truth or test result
was read. The bad-page definition remained composite accuracy `< 0.90`; the existing review
threshold remained `0.70`.

## Changes and observed DEV effects

1. Added generic image-region ink coverage with routing threshold `0.05`. The first version
   counted all page ink and incorrectly routed four digital receipts because of vector divider
   lines. That pass had Unmess CER `0.04757`, WER `0.09392`, mean page accuracy `0.96031`, and
   26 VLM attempts. Restricting the signal to actual image rectangles kept receipts on
   PyMuPDF while still routing the five bilingual raster-line pages and the English
   raster-line/stamp unit fixture. Final CER was `0.01702`, WER `0.03314`, mean page accuracy
   `0.98149`, and VLM attempts were 21.
2. Added rendered-noise visual clarity (weight `0.30`) for image-dominant pages and a generic
   review reason at normalized noise `>= 0.85`. Added consecutive-table continuity uncertainty
   (weight `0.40`) when adjacent pages are independently table-likely. Against Phase 2d, review
   AUROC moved from `0.34286` to `0.97937`, recall from `0.0` to `1.0`, and precision from
   undefined to `0.70`. There are only seven bad pages, so all gate results remain unstable.
3. The first continuity implementation also escalated five second-page tables from Docling to
   VLM. Accuracy fell from `0.87500` to `0.65466` on each and no escalation improved accuracy.
   Continuity is now review-only for escalation decisions: it lowers the final confidence and
   flags the page but does not replace a successful structured parser. Table F1 stayed
   `0.86607`; CER returned from `0.04757` to `0.01702`.
4. Bilingual routing changed solely through uncovered image-region ink. Bilingual CER moved
   from `0.05020` to `0.03345`, WER from `0.09091` to `0.0`, and mean page accuracy from about
   `0.95` to `1.0`. No Devanagari, language label, category name, or generator coordinate is
   used by the routing signal.
5. The VLM-only baseline was changed from cache-miss failure to the same live local-model
   policy as routed VLM: 120 seconds per attempt, one retry, and a failed `ParsedPage` after
   both attempts. The three earlier merged-table failures (`00`, `02`, and `04`) were retried
   and still returned HTTP 500. They remain failures in all denominators; the overall VLM-only
   CER `0.17311`, WER `0.26689`, table F1 `0.64718`, and failed-page count `3` did not move.

The final gate flags all seven bad pages and three good pages. This small, templated DEV set
cannot validate the gate; leave-one-category-out results and the instability warning are
reported in the Phase 2e DEV report.

## Cold-timing protocol correction

The first controlled timing attempt started every system with an empty cache directory, but
Unmess recorded four cache hits because some synthetic pages have identical rendered content
within the same system run. The protocol had preregistered that any hit invalidates the row, so
the attempt was stopped before VLM-only completed and none of its times are reported. No routing,
gate, or bad-page threshold changed. The runner now disables cache reads during cold timing while
still writing successful responses. A unit test verifies that two identical pages make two model
calls and report zero hits. The complete replacement pass used fresh directories and every system
reported zero cache hits.
