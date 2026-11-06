# Detailed quality export: full-file audit and interpretation

Reviewed 6 November 2026. Source: `beed_october_detailed_quality_profile_2001_2024.csv`, reported size 39,372 bytes (about 38.4 KiB). Full reader-returned text, source identity and completion metadata are retained in `detailed_quality_input_extract.json`. Reader text has 39,371 characters and may normalize the terminal newline; this is not represented as an original-byte download or checksum verification.

## Completeness and numerical verification

All 174 data rows were parsed programmatically, not sampled: 169 quality-group rows and five explicit empty-composite records. All 54 expected composite start dates across 2001–2024 are present, matched against the preceding date audit. An empty record means no observations survived the selected October/quality mask for that composite, not that the satellite asset was absent.

Every record was checked for CSV field count, dates and source IDs, year/month/boundary, finite nonnegative areas, full-district denominator consistency, area/fraction agreement, record uniqueness, and quality-code decoding. Within each composite, disjoint group fractions do not exceed the district. Previous annual good-only and expanded monthly coverage satisfy the bounds implied by per-composite totals: the monthly union must be at least the largest composite footprint and no larger than the sum (capped at one).

There are no audit errors. Maximum area/fraction discrepancy is 2.22e-16. The independent decoding uses bit operations on the exported joint integer, whereas the GEE script used division/modulo. This checks internal agreement of exported codes and labels; it does not independently re-read raw satellite pixels.

One warning is retained: usefulness code 3 occurs in the data and is consistent with its joint integer, but the current Earth Engine catalogue's enumerated usefulness labels omit 3. It is preserved as observed/unlabelled rather than assigned another class. All such observations here carry high-aerosol flags.

## What the 174 rows show

Only six joint QA patterns occur after the October, land and existing detailed exclusions:

| SummaryQA | MODLAND QA | VI usefulness | Aerosol | Interpretation |
| ---: | ---: | ---: | ---: | --- |
| 0 | 0 | 0 | 1 | Good; low aerosol |
| 0 | 0 | 1 | 1 | Good; low aerosol |
| 1 | 1 | 1 | 2 | Marginal; intermediate aerosol |
| 1 | 1 | 2 | 2 | Marginal; intermediate aerosol |
| 1 | 1 | 3 | 3 | Marginal; high aerosol; usefulness label unresolved |
| 1 | 1 | 4 | 3 | Marginal; high aerosol |

This is an association within the already-filtered observations, not proof that aerosol alone caused the marginal label. No claim is made about rejected observations or other months/regions. Low aerosol does not prove the good retrievals are accurate, and intermediate aerosol does not automatically make marginal retrievals acceptable.

| October | High-aerosol share of marginal observation area |
| --- | ---: |
| 2019 | 58.81% |
| 2020 | 0.07% |
| 2021 | 0.94% |
| 2022 | 2.60% |
| 2023 | 0.00% |
| 2024 | 22.49% |

Each percentage is computed as the sum of high-aerosol marginal group areas over that October's candidate composites, divided by the sum of all marginal group areas over those composites. The same location can contribute more than once. These percentages therefore describe observation-area composition, NOT unique district area, added map coverage, or drought extent. They also do not isolate only locations absent from the strict monthly map.

The large 2019 high-aerosol share matters because 2019 belongs to the historical reference period. Blindly admitting all marginal observations can change the reference minimum/maximum, affecting VCI in later years even if those later observations have better QA. In 2021 and 2023 most or all retained marginal observation area belongs instead to the intermediate-aerosol patterns. This makes a screened sensitivity experiment more informative than a blanket SummaryQA <= 1 change.

## Next methodological decision

Retain the strict variant as a benchmark. A concrete candidate sensitivity variant would keep all original strict observations and add only observations satisfying all of:

- SummaryQA 1;
- MODLAND QA 1;
- VI usefulness explicitly 1 or 2;
- aerosol category 2;
- the same October pixel dates, valid range, land and detailed cloud/snow/shadow exclusions.

This is a proposed analysis choice informed by the observed quality combinations, not a manufacturer-endorsed acceptance threshold, recovered Andure method, or validated production policy. It excludes the observed high-aerosol groups and the unresolved usefulness code. It has not yet been run, and its unique monthly coverage cannot be reconstructed exactly from this grouped CSV because spatial overlaps were discarded.

The next computation should rebuild October NDVI and its 2001–2019 reference under both strict and candidate policies, then compare coverage, NDVI and VCI on both shared locations and each full retained footprint. Keep the same historical eligibility in the primary comparison so QA and year-count effects are not mixed. Do not insert candidate current NDVI into the old reference extrema. Full VHI additionally requires the pending LST temporal-alignment decision.

This CSV contains areas and quality categories, not NDVI/LST values or ground truth. It cannot establish VCI/VHI accuracy, quantify actual aerosol retrieval bias, or validate a drought classification. The audit verifies completeness and internal consistency of the supplied export within those limits.

## Reproduce

Run `python3 pipeline/andure/analyze_detailed_quality.py`. Outputs are `detailed_quality_validation.json` and `detailed_quality_year_summary.csv`. The latter explicitly uses observation-area denominators. The accompanying tests exercise a valid export and deliberate corruption of code labels, an entire missing composite, and mismatched areas.

Official quality-bit positions and aerosol definitions: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A2 (checked 6 November 2026).
