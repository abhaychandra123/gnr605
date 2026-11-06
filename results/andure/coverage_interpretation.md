# October 2020 coverage diagnosis

Source: user-pasted Earth Engine console on 6 November 2026, transcribed to `data/andure/beed_coverage_2020_10_console.csv`. This is not an independently downloaded Drive export. The user's preview summary repeats the previous result exactly. The local source for that run is the prior version of `pipeline/andure/01_indicators_gee.js`; the next QA/sensitivity additions have not been executed in Earth Engine.

Current QA-valid NDVI covers 67.0462% of the provisional district; LST covers 99.7825%. Their intersection is 66.9862%. Requiring at least 15 valid historical Octobers from 2001–2019 for NDVI reduces this to 26.1894%. The LST history requirement reduces it only to 26.1744%. Nonzero-range screening adds no further loss. Direct final VHI coverage agrees exactly with the cumulative diagnostic.

The historical NDVI requirement removes 40.7967 percentage points of district area, about 61% of the current joint-valid area. Independently, only 35.0249% of the district has the required NDVI history, compared with 99.7225% for LST. These measures identify the responsible eligibility rules, not the physical causes of missing or rejected observations. Clouds, QA decisions and data availability remain to be separated.

The 15-year threshold is our provisional reconstruction choice, not an established threshold recovered from Andure. Each reference sample is a monthly composite for one year, not an individual satellite image. A pixel with 14 accepted Octobers fails this rule even if October 2020 is valid. Lowering only this threshold cannot recover more than the approximately 67% current-data overlap, and shorter records can make min/max-based indices less stable.

VHI 91.4275 describes the retained footprint only. It does not establish that the entire district avoided drought. Means can hide spatial stress, excluded areas are unobserved, and the land mask is not a cropland mask. Changing valid footprints can also create misleading temporal comparisons.

## Prepared next experiment

The script now leaves the original index settings intact and adds two diagnostic tables when `inspectNDVIQuality: true`:

1. `NDVI QA comparison`: cumulative value range, land, SummaryQA=0, adjacent-cloud exclusion, mixed-cloud exclusion, snow/shadow exclusion. Each row reports current NDVI coverage, historical eligibility, and joint eligibility with the original thermal requirements. Quality rules are applied consistently to current and historical observations. Early rows are diagnostic only and may contain unsuitable observations. The final row should reproduce 26.1744% joint coverage.
2. `NDVI reference sensitivity`: compare 10, 12, 15 and 19 required NDVI years under the original QA and fixed 15-year LST requirement. These are exploratory comparison levels, not calibrated alternatives. This table measures coverage, not index accuracy. The 15-year row should reproduce 26.1744% coverage.

The next choice must weigh coverage against observation quality and historical stability, rather than maximize mapped area. If a QA policy is changed, recompute both the historical reference and current composites. Compare indices on common pixels as well as newly admitted pixels before accepting it. Only then proceed to temporal comparisons, verified AOI/cropland masking, rainfall anomalies and independent validation. The user can export the diagnostic tables as CSVs instead of copying all console metadata.

## Received QA and reference sensitivity results

The user subsequently supplied both diagnostic tables and an unchanged preview. Values were transcribed to `data/andure/beed_ndvi_qa_2020_10_console.csv` and `data/andure/beed_ndvi_reference_2020_10_console.csv` on 6 November 2026. These are console transcriptions, not independent downloads. The diagnostics' strict final stage matches the prior 26.1744% coverage exactly.

Current NDVI has numerical values throughout the district, but the land-class rule retains 86.6012%, and SummaryQA=0 retains 67.0462%. Numerical availability is not evidence of observation quality. The land filter's exclusions do not establish that 13.4% of Beed is water: QA classification, composite availability, mixed pixels and the provisional AOI all require consideration.

With historical eligibility and thermal requirements, adding SummaryQA=0 reduces joint coverage from 82.0681% to 26.2507%. The extra adjacent-cloud, mixed-cloud and snow/shadow filters together reduce it by only 0.0762 percentage points to 26.1744%. Relaxing only those extra filters would therefore not solve the coverage problem. These differences apply in the stated cumulative order.

The NDVI-year sensitivity is 64.5701% (10 years), 58.9236% (12), 26.1744% (15), and zero (19), with LST fixed at 15. Zero at 19 means no pixels pass all joint requirements with a complete accepted NDVI October history. It does not show that MODIS is absent for all years or identify any specific missing year.

Next: retain strict QA, preserve the 15-year baseline and run a separate exploratory 12-year eligibility comparison for October 2020–2024. Twelve is a sensitivity setting, not a calibrated minimum or a claim of sufficient climatological stability. Historical bounds remain 2001–2019, using all available accepted observations, for both variants. Only pixel eligibility changes. Thus any change in the same-month district mean is caused by the newly admitted footprint; pixel indices on the common footprint should be unchanged. Check historical year coverage for systematic gaps before choosing a final eligibility policy.

The script prepares `beed_october_2020_2024_ndvi12_vs15` (10 rows) and `beed_october_reference_year_audit` (19 rows) as batch exports. These new experiments have not yet run in Earth Engine. They are not a trend test or independent drought validation. The final AOI, crop population, temporal support and independent outcomes still need validation.
