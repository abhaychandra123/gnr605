# Andure reconstruction: first executable baseline

**Latest status:** script 04's full export is received and audited: 174 rows, 54 expected composites, six joint quality patterns, no consistency errors. Four audit tests also pass. See [the detailed quality review](../../results/andure/detailed_quality_review.md). Marginal observations divide into intermediate- and high-aerosol groups; the latter account for 58.81% of marginal observation area in 2019 and 22.49% in 2024. A candidate screened sensitivity policy is documented but not yet implemented or validated. Earlier instructions below document the original baseline. Corrected VHI and ML remain pending.

Started 6 November 2026. The user successfully ran the corrected October 2020 preview in Earth Engine and supplied its console summary and screenshot. VHI is 91.4275 over only 26.1744% of the provisional district. This is an initial computational result, not a validated district-wide drought assessment. All 26 reported fields are preserved in [the console-transcribed CSV](../../data/andure/beed_preview_2020_10_console.csv), with adjacent provenance metadata. The [audit](../../results/andure/preview_console_audit.json) passes consistency checks and flags low coverage. No original Drive export or ML results have been received. The updated coverage diagnostics still need a browser run.

## Why start here?

Andure et al. (2025), DOI https://doi.org/10.64252/y0bxsk22, is our selected local case study. Reconstruct the data and index calculations first, then assess the ML experiment. The paper's original data, code, exact sampling unit, products, estimator and split specification are unavailable in our materials. We cannot honestly promise to reproduce its 262 Beed rows or R² = 0.998.

The model predicts VHI from six inputs including VCI and TCI. Equation 4 defines VHI from those same components. A direct formula is therefore the essential benchmark; a high score on this target alone is not evidence of drought forecasting. Somni et al. provides an additional published precedent for the MODIS products and index calculations we choose here.

## What runs now

`01_indicators_gee.js` builds monthly NDVI and daytime LST, calculates pixel-level VCI/TCI against the same calendar month in the reference period, combines them into VHI, displays a preview, and prepares a CSV export. Monthly and trailing-three-month rainfall totals provide context. **A three-month total is not SPI-3.** SPI fitting and ML are pending stages.

`audit_export.py` reads the exported CSV, checks units, missing values, area/coverage consistency, duplicate dates and the VHI identity. Its coverage screen of 80% is a provisional engineering flag, not a calibrated drought criterion. It uses Python's standard library.

## Explicit reconstruction choices

These are our implementation choices unless marked as a paper equation. They are not presented as details recovered from Andure.

| Decision | Initial setting | Consequence |
| --- | --- | --- |
| Analysis | Monthly 2020–2024; first preview October 2020 | 60 district-month rows if batched, not the paper's 262 samples |
| NDVI | MODIS/061/MOD13A2, native nominal 1 km, 16-day | Shared MODIS precedent with Somni |
| Temperature | MODIS/061/MOD11A2 daytime, native nominal 1 km, 8-day | Kelvin throughout; not air temperature |
| Monthly alignment | Mean of composites with start timestamps inside the month | Not a daily calendar-month mean; composite support can cross month boundaries |
| Reference | 2001–2019, independently for each calendar month | Before the reconstruction period; reference-period sensitivity still required |
| Reference sufficiency | At least 15 valid annual monthly composites per variable/pixel | Exploratory threshold; masked where insufficient or min=max |
| Formula | VCI=100(NDVI−min)/(max−min); TCI=100(max−LST)/(max−min) | Calculate per pixel before district aggregation |
| VHI | 0.5 VCI + 0.5 TCI | Paper equation; 0.5 chosen because actual implementation weight is unclear |
| Values outside 0–100 | Retained | Observations can exceed a fixed historical range; visualization limits do not clip exported data |
| NDVI QA | SummaryQA=0, land class, no adjacent/mixed cloud, snow or shadow, raw product range | Current valid footprint varies; strict masking can reduce monsoon coverage |
| LST QA | Mandatory and data-quality bits good; reported LST error ≤1 K | Composite QA does not guarantee every contributing daily retrieval was good |
| AOI | Provisional FAO GAUL 2015 Beed/Bid/Bhir match; stop unless exactly one match | Historical dataset, now superseded; verify geometry and archive a final AOI before interpreting results |
| Rainfall | CHIRPS v2 daily, summed then area-weighted over the district on its own grid | Coarser than MODIS; no new spatial information from resampling |
| Rainfall missingness | Require every daily input per pixel | Missing totals stay blank, never zero-filled |
| Spatial summaries | Pixel-area-weighted mean; same valid support for all five satellite variables | Ensures district VHI remains the same weighted combination; footprint changes can still bias comparisons |
| Land use | MODIS QA land class only | Not cropland, rainfed, or sugarcane separation; agricultural impact claims premature |
| Coverage denominator | Full district area on the MODIS grid | Includes land excluded by QA/water flags; not a fraction of verified cropland |

The exported `ndvi`, `lst_k`, `vci`, `tci`, `vhi` are district means over joint valid support. `valid_area_km2` and `district_area_km2` define `valid_fraction`. Rainfall uses independent spatial support and reports daily source counts. No drought-area classification is made yet.

## Run the first month

**Current next step:** QA/sensitivity diagnostics are now received. SummaryQA=0 plus the 15-year NDVI requirement drives most exclusions; the additional detailed flags have little effect. See [the interpretation](../../results/andure/coverage_interpretation.md). The defaults now set `batch: false`, `inspectNDVIQuality: false`, `octoberPilot: true`. Run the script and start these two Tasks: `beed_october_2020_2024_ndvi12_vs15` and `beed_october_reference_year_audit`. Download their CSVs into `data/andure/`. This tests a 12-year NDVI eligibility threshold alongside the original 15, with unchanged QA, 2001–2019 reference bounds and 15-year LST eligibility. It does not yet adopt 12 as a final method.

The pilot has 10 rows: one per October/year/NDVI threshold. Read `min_ndvi_years` and `min_lst_years` as the actual eligibility settings; `min_baseline_years` records the original default. Values on common pixels are unchanged by the eligibility threshold alone. Differences in aggregate means can therefore arise from changed spatial coverage. The reference audit reports source-image counts and QA-valid area separately for each October in 2001–2019. Run these exports as batch tasks rather than attempting to print all rows in the interactive console. New pilot execution remains pending.

The first pilot task (`ADZ5BGA373SDB4DF54H2V4UY`, 6 November 2026 at 16:53 IST) failed with `Image.gte` receiving an Integer instead of an Image. The mapped NDVI threshold is now explicitly converted using `ee.Image.constant(ee.Number(ndviMinYears))`; the other image-versus-parameter comparisons also use constant images. Scientific settings are unchanged. Replace the Code Editor script, click Run to create a new export task, and start that new task. Retrying the old task would retain its old computation. The corrected batch export has not yet been verified on Earth Engine.

1. Open https://code.earthengine.google.com/ with an Earth Engine enabled project. Paste `01_indicators_gee.js` into a new script. Leave `batch: false`.
2. Click Run. The console must find exactly one boundary. If it does not, inspect the printed Maharashtra district names or set `boundaryAsset` to a verified FeatureCollection containing one district feature. Do not substitute a hand-drawn rectangle.
3. Inspect the boundary, NDVI, VHI, valid-composite counts and reference-year count layers. The initial geometry must still be checked against an authoritative Beed boundary. Record the chosen asset and boundary code.
4. Inspect `Preview summary`: units, source counts, nonzero valid area and coverage. Missing areas on maps are not drought classifications. Investigate low coverage; do not silently relax QA.
5. In Tasks, run the prepared `beed_preview_2020_10` table export. It writes a CSV to your Google Drive folder `gnr605_andure`. Download it into `data/andure/` in this repository. Running the script alone prepares but does not start the export task.
6. From the repository root:

```sh
python3 pipeline/andure/audit_export.py data/andure/beed_preview_2020_10.csv --output results/andure/preview_audit.json
```

7. After reviewing the map and audit, set `batch: true`, run again, and export `beed_monthly_2020_2024`. Audit that file the same way. Keep the script/configuration used with the export. It should have 60 rows including missing months, not 60 necessarily usable observations.

No local Earth Engine Python package or standard Earth Engine credential file was present during setup. The user's browser run confirms access to the Code Editor and GAUL collection. No credentials are required for the local CSV audit.

## Diagnose the first preview's missing area

`Coverage fractions by stage` reports area fractions of the same full district:

- `01_current_NDVI` and `02_current_LST`: valid October observations for each variable independently.
- `03_current_both`: their intersection, before reference requirements.
- `04_current_both_plus_NDVI_reference`: additionally require at least 15 reference years for NDVI.
- `05_current_both_plus_both_references`: additionally require at least 15 for LST.
- `06_above_plus_nonzero_ranges`: exclude undefined indices where a reference range is zero.
- `07_actual_VHI`: directly measure the final mask. This should agree with stage 06 and the preview summary.
- `08_NDVI_reference_alone` and `09_LST_reference_alone`: independent reference eligibility, without current-observation requirements.

Stages 03–06 are cumulative and should never increase. Their area differences attribute exclusions in this stated order; they are not independent causal effects. Stages 01/02/08/09 overlap and must not be added. A large loss at stage 03 indicates overlap/current-data limitations; a large subsequent loss identifies reference eligibility as an additional bottleneck. To diagnose individual QA flags within a sensor, a further QA-bit breakdown would be needed.

Two additional layers show current NDVI/LST before the shared VHI mask. The original NDVI layer used only VHI-valid pixels, so its gaps did not necessarily mean missing NDVI. The boundary is now an outline to avoid mistaking its solid grey fill for a drought class. Toggle one indicator at a time. Reference-year layers and a separate diagnostic CSV export are available.

The supplied rainfall totals are 148.6294 mm for October and 545.1822 mm for August–October. The daily collection counts match 31/31 and 92/92, respectively. Totals alone do not establish a rainfall anomaly or SPI. Mean LST on joint valid pixels is 305.9567 K (32.8067 °C), a surface temperature. VCI/TCI/VHI values are scaled indices, not percentages of healthy land or historical percentiles. The high means describe only the retained pixels and need coverage/selection-bias checks before broader interpretation.

## What to do after the first successful export

1. Plot NDVI, LST, VCI, TCI, VHI and coverage through time. Inspect seasons and gaps before fitting a model. Compare formula consistency, not the paper's reported accuracy yet.
2. Add SPI-3 using a long CHIRPS history and a documented calendar-month distribution fit, zero-rain handling and reference period. Do not fit it to only five years or call a z-score SPI without specifying the method.
3. Define the ML reconstruction with an explicitly chosen estimator. Preserve 2024 as a later-year test, use earlier years for fitting/tuning, and include the formula benchmark and an ablation excluding VCI/TCI. The latter is still contemporaneous estimation unless a future target and predictor cutoff are specified. Five years provide weak event-level evidence.
4. If a genuine forecast is desired, define a lead time and use only information available at issue time. Composite start dates are not actual availability dates. Evaluate against persistence/seasonal baselines and independent outcomes.
5. Add independently defined cropland/irrigation masks and external validation before making agricultural-drought accuracy claims. District means alone can hide localized stress.

## Checks and sources

```sh
node --check pipeline/andure/01_indicators_gee.js
python3 -m unittest discover -s pipeline/andure -p 'test_*.py' -v
```

Tests use temporary, explicitly synthetic fixtures only. They check incorrect identities, Celsius/Kelvin mistakes, missing values, duplicate months, nonfinite values and preservation of out-of-reference values. Syntax checks do not prove that Earth Engine assets or server-side operations execute successfully. A real preview export remains the integration check.

- Local full paper: [Andure et al.](../../literature/papers/Andure_et_al_2025_Beed_Drought_ML.pdf), equation 4 and Beed results pp. 3925–3926; see [critical review](../../literature/notes/paper_review.md).
- NDVI scale and QA: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A2
- LST scale and QA: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD11A2
- Rainfall: https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY
- Provisional geometry/vintage: https://developers.google.com/earth-engine/datasets/catalog/FAO_GAUL_2015_level2

Catalog and API documentation checked 6 November 2026. No original author code or data has been recovered.
