# Andure reconstruction: first executable baseline

Started 6 November 2026. Stage 1 implements satellite indicators and a processing audit. The first user-run Earth Engine attempt successfully matched one GAUL feature named Bid, then stopped before displaying the indices because `copyProperties` returned an Element rather than an Image. Explicit Image casts now fix that return type in the three affected functions. The corrected satellite run is pending; no Beed indicator results or model scores have been produced. Local JavaScript syntax and Python audit tests are checked separately.

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
