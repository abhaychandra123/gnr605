# October observation-date audit

Reviewed 6 November 2026 from `beed_october_pixel_date_audit_2001_2024.csv` (24 rows). Source identity and full reader-returned CSV text are preserved in `date_audit_input_extract.json`; this is an analysis extract, not a byte-identical original download.

## Result

Selecting MOD13A2 observations by their pixel DayOfYear recovers substantial October coverage in some years without relaxing QA. It does not resolve all missing coverage. These fractions concern current NDVI alone, before LST intersection, historical eligibility or nonzero reference-range requirements. They are not corrected VHI coverage, vegetation-area fractions or drought percentages.

| October | Original NDVI coverage | Pixel-date NDVI coverage | Net change, percentage points |
| --- | ---: | ---: | ---: |
| 2019 | 0.51% | 25.58% | +25.06 |
| 2020 | 67.05% | 62.27% | -4.78 |
| 2021 | 11.03% | 13.02% | +1.99 |
| 2022 | 81.17% | 81.29% | +0.12 |
| 2023 | 4.23% | 48.14% | +43.91 |
| 2024 | 2.18% | 18.98% | +16.80 |

Coverage increases in 19 years and decreases in five (2004, 2008, 2012, 2016, 2020). In 2024 there is both a gain of 17.64 percentage points and a loss of 0.84 points, yielding the 16.80-point net gain. New October coverage still leaves 86.98% of the provisional district without accepted NDVI in 2021 and 81.02% in 2024. Subsequent index masks cannot increase this footprint under the same data selection.

## What the source dates establish

Non-leap-year original selection contains only October 16. Candidate selection adds September 30, which can contain October observations. Leap-year original selection contains October 15 and October 31; candidate selection adds September 29. The pixel-date filter retains only observations selected within October. Thus it can exclude November observations from the October 31 composite while recovering October observations from a September-start composite. The source count pattern is consistent with the 16-day schedule, not proof of missing assets.

For an explicitly October-observation study, selected pixel dates provide a better-aligned definition than composite start dates. This is a methodological choice for our reconstruction, not confirmation of the paper's undocumented processing. Averages still use selected composite observations, not all daily observations. Shared old/new spatial support does not imply identical NDVI values because observation membership can change even where both masks are valid.

## Verification

`python3 pipeline/andure/analyze_date_audit.py` reproduces `date_audit_comparison.csv` and `date_audit_validation.json`. Checks pass: 24 unique ordered years; fractions in [0,1]; source counts and date windows; QA and boundary identifiers; all 19 old historical NDVI fractions exactly agree with the previous audit; 2020 agrees with the earlier console diagnostic. The largest residual in `old = common + lost` and `new = common + gained` is approximately 1e-15. This verifies internal consistency, not satellite retrieval accuracy or boundary validity.

## Next experiment and decision

Run `pipeline/andure/03_october_qa_audit_gee.js` as a separate script and export `beed_october_pixel_date_qa_audit_2001_2024`. It keeps pixel-date selection fixed and reports 24 rows of cumulative QA gates: date/value range, land, good SummaryQA, no adjacent cloud, no mixed cloud, no snow/shadow. Stage 06 must reproduce this audit's new NDVI fraction in every year.

Two separate diagnostic branches measure marginal SummaryQA observations and good-or-marginal observations with the original detailed cloud/snow/shadow exclusions. They do not adopt marginal data as a production policy. Their monthly footprints overlap; do not add branch fractions. Marginal means inspect further QA, not automatically reliable or automatically cloudy. If marginal observations dominate the gap, inspect usefulness, aerosol and observation geometry before deciding whether to include any. If cloud or land classifications dominate, quality relaxation alone is not justified; inspect spatial patterns and consider a separately documented data-source or season-window experiment.

The next script has passed a local JavaScript syntax check; its Earth Engine execution remains pending. The original index script is unchanged. Before any corrected VHI comparison, apply the chosen NDVI rule consistently to all current and reference years and resolve LST temporal alignment. Do not append new NDVI to old reference extrema. The date audit alone does not justify dropping reference eligibility to obtain a fuller map or fitting ML to the earlier sparse district means.

Official product documentation for cadence, selected-pixel DayOfYear and QA definitions: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A2 .
