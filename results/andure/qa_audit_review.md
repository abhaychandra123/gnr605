# October QA audit: the missing coverage is concentrated in marginal data

Reviewed 6 November 2026. The complete 24-row user export is retained as reader-returned text with provenance in `qa_audit_input_extract.json`. It is not an original-byte download. Reproduce the checks with `python3 pipeline/andure/analyze_qa_audit.py`.

## Evidence

All 24 final strict fractions exactly match the preceding date audit. Cumulative gates decrease monotonically, separate branches respect containment, and dates/counts/areas/boundary metadata agree. `qa_audit_validation.json` has no errors. These are internal consistency checks, not accuracy validation.

| October | Land after date/value checks | Strict good-only coverage | Good or marginal, same detailed exclusions | Additional district coverage |
| --- | ---: | ---: | ---: | ---: |
| 2019 | 86.79% | 25.58% | 75.74% | 50.16 pp |
| 2020 | 88.27% | 62.27% | 88.27% | 26.00 pp |
| 2021 | 86.57% | 13.02% | 86.57% | 73.55 pp |
| 2022 | 88.48% | 81.29% | 88.15% | 6.86 pp |
| 2023 | 84.77% | 48.14% | 84.77% | 36.64 pp |
| 2024 | 82.81% | 18.98% | 82.44% | 63.46 pp |

Denominator throughout: full provisional GAUL district. These are current NDVI footprints before reference eligibility or LST intersection. The land stage is a dynamic per-observation QA flag, not an independently verified land/water or cropland map. Coverage left out by this gate cannot be interpreted as actual district water area.

In 2021, the good-only SummaryQA gate removes 73.55 percentage points after land selection. The subsequent adjacent-cloud/mixed-cloud/snow/shadow gates remove no additional monthly coverage. In 2024, the good-only gate removes 62.35 points; subsequent flags remove another 1.48 points. Thus SummaryQA selection is the dominant remaining exclusion in these years, given the specified order of filters.

Including SummaryQA 1 while retaining the existing detailed exclusions recovers most of the land-stage footprint in the recent pilot years. This does not establish that all recovered observations are accurate. The current mask does not explicitly screen detailed VI usefulness, aerosol quantity or MODLAND quality; those attributes must be examined before selecting a marginal-data policy.

The catalogue describes SummaryQA 0 as good and 1 as marginal requiring inspection of other QA. SummaryQA 2 and 3 designate snow/ice and cloudy conditions. DetailedQA separately includes MODLAND quality (bits 0–1), usefulness (2–5) and aerosol (6–7). Absence of an adjacent-cloud or mixed-cloud flag alone is insufficient to establish reliable NDVI. These results do not identify whether aerosols, geometry or another quality issue explains the marginal labels.

The marginal-only monthly footprint in stage 07 overlaps the good footprint: a location can have a good observation in one composite and a marginal observation in another. Do not add stages 06 and 07. Stage 08 minus stage 06 measures new locations accepted by the expanded mask. Even on shared locations, monthly NDVI can change because the expanded rule adds observations to the average.

## Decision and next executable step

Keep the original strict pipeline as a benchmark. Treat the good-or-marginal variant as a sensitivity experiment, not as a validated fix or a source of final drought classifications. The audit now identifies the exclusion gate; repeating the same coverage checks or lowering historical-year requirements will not establish the reliability of marginal observations.

`pipeline/andure/04_marginal_quality_profile_gee.js` prepares one export, `beed_october_detailed_quality_profile_2001_2024`. For each candidate composite it reports area grouped jointly by SummaryQA, MODLAND quality, VI usefulness and aerosol category, after the same October/land/cloud/snow/shadow selection as stage 08. It profiles both good and marginal data so their detailed quality distributions can be compared. Empty composites receive an explicit record. No additional quality cutoffs are chosen in this diagnostic.

These are per-composite observation areas. Summing them across dates can count the same location more than once, so those totals must not be reported as unique district coverage. The joint code preserves co-occurrence of flags and avoids inferring relationships from separate marginal histograms. The profile does not prove the physical cause of a quality flag or replace independent validation.

The next decision is whether any defined subset of marginal observations warrants a sensitivity reconstruction. If detailed flags indicate unsuitable observations, change the data-source or temporal-window design explicitly rather than silently accepting them. If a subset is defensible, rebuild its full 2001–2019 NDVI reference and current series consistently, retain strict results alongside it, resolve LST temporal alignment, and compare both shared-area and full-footprint results before drought interpretation. Historical eligibility and VHI coverage cannot be inferred from this current-NDVI table.

Local validation: the analysis passes on the supplied export; the new script passes JavaScript syntax checking. Earth Engine execution of script 04 is pending. No corrected VHI or ML run has been performed.

Official QA definitions: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A2 (checked 6 November 2026).
