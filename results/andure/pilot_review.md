# First exported October pilot: what it establishes

Reviewed 6 November 2026. Both uploaded CSVs were read in full: 10 pilot rows and 19 historical audit rows. Original file identities: `libfile_44b2bb47a79c81918811564803027a87` and `libfile_8cd25cac98148191afc0a94e130d61b4`. Direct original-byte transfer into the repository failed; `pilot_input_extract.json` preserves the complete parsed tabular fields except empty geometry and system indexes, with provenance. It is an analysis extract, not a byte-identical original CSV. The source uploads remain unchanged.

## Findings

| October | Coverage, 12 years | Coverage, 15 years | VHI, 12 years | VHI, 15 years | October rain (mm) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020 | 58.92% | 26.17% | 95.75 | 91.43 | 148.63 |
| 2021 | 10.06% | 5.08% | 93.07 | 94.64 | 84.24 |
| 2022 | 70.98% | 32.86% | 91.58 | 93.38 | 189.27 |
| 2023 | 3.69% | 1.60% | 48.17 | 56.11 | 20.66 |
| 2024 | 1.89% | 0.97% | 106.32 | 106.98 | 85.54 |

The VHI identity passes to within 3.13e-13; area ratios, unique year/settings pairs, matching rainfall between variants and expected row counts pass. All rows trigger the provisional 80% coverage screen. This screen is a warning, not a calibrated accept/reject criterion. More importantly, 2021, 2023 and 2024 have very limited valid footprints under both settings.

The lower 2023 VHI and rainfall warrant further investigation, but cannot establish a district drought classification. October rainfall is the lowest of these five Octobers; August–October rainfall is also lowest (261.80 mm). Neither comparison replaces SPI against a long reference record or independent crop-impact validation. The 12-year VHI comes from about 421 km² and the 15-year VHI from about 183 km².

VHI exceeding 100 in 2024 is mathematically possible because fixed 2001–2019 bounds are not clipped: NDVI can exceed its historical maximum and LST can fall below its historical minimum. Both component means exceed 100 here. This is not 106% healthy land and should not be hidden by clipping. Coverage, narrow baseline ranges, extreme observations and sensor consistency still need checking.

Changing only eligibility leaves pixel-level values on shared support unchanged. Differences between the two same-year district means therefore describe the effect of the additional spatial footprint. Across years the footprint also changes, so these means are not a controlled vegetation trend. No trend test, forecast model or drought accuracy claim is justified from this pilot alone.

## Historical coverage and timing

Historical accepted NDVI area is especially limited in 2019 (0.5150%), 2017 (25.5840%), 2015 (27.6751%) and 2010 (37.6717%). The 2019 image exists: source count is one. Low valid coverage is not absence of the entire source collection. Its tiny accepted footprint helps constrain complete 19-year eligibility, but annual aggregate areas cannot alone prove why every pixel fails the joint requirement.

Every non-leap historical October has one NDVI source image under the current rule; leap-year Octobers have two. The same pattern occurs in the five pilot years. LST has three versus four source composites. This is consistent with the interaction between fixed composite cadence and filtering by start timestamp, not evidence of a missing-image anomaly by itself.

The original rule selects a composite if its start falls in October. That can discard October observations belonging to a composite starting in late September and include November observations belonging to a late-October composite. The limitation was documented initially, but this audit shows that month-to-month temporal support needs direct examination. It is not yet established how much of the low coverage a different date rule will recover, especially in 2024 where two source composites already exist.

## Next controlled experiment

`pipeline/andure/02_october_date_audit_gee.js` is a separate, unexecuted Earth Engine experiment. It uses the same provisional boundary and identical strict NDVI QA. For each October in 2001–2024 it compares:

1. Original composite-start filtering.
2. Candidate composites starting within the month or the preceding 15 days, retaining only pixels whose `DayOfYear` falls inside October.

The second rule uses the selected observation day provided in MOD13A2. It still represents selected composite observations, not a mean of every daily observation. No gap filling, interpolation or quality relaxation is introduced. New coverage may gain some pixels and lose others previously supported only by out-of-month observations.

Export `beed_october_pixel_date_audit_2001_2024`. It contains 24 rows with actual source start-date lists, both coverage fractions, common/gained/lost fractions and candidate counts. Verify old fractions against the existing historical audit and check `new = common + gained`, `old = common + lost`. Check both improved and degraded years, rather than choosing a rule solely to maximize coverage.

If adopted, recompute the current NDVI and the full historical NDVI reference consistently before comparing VCI/VHI. LST is not processed by this experiment; its 8-day monthly alignment remains a separate issue. Verified geometry/crop masks and independent validation remain required. Do not train the proposed ML baseline on the current sparse October summaries.

## Reproduce this local analysis

Run `python3 pipeline/andure/analyze_pilot.py` from the repository root. It generates `pilot_comparison.csv`, `pilot_upload_audit.json` and `pilot_coverage.png` from the provenance-bearing extract. The data were supplied by the user; no satellite jobs were executed locally.

Source documentation: MOD13A2 cadence, QA and DayOfYear at https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A2 ; date filtering at https://developers.google.com/earth-engine/apidocs/ee-filter-date . These support the date experiment, not a claim that it reproduces Andure's unpublished processing choices.
