# Proposed Beed pilot and meeting brief

**Superseded for the course assignment, 7 November 2026.** The user clarified the actual problem as a ten-year, single post-monsoon-month vegetation-area analysis. That work is now executed for Beed, October 2015–2024: [report](../results/assignment/assignment_report.md), [plot](../results/assignment/year_vs_vegetation_area.png), [code and reproduction](../pipeline/assignment/README.md). The broader proposal below is retained as history, not an instruction to expand the assignment.

27 October 2026. Proposed design, not empirical findings. The three supplied papers are reviewed; no imagery, crop data or drought-label dataset has yet been processed. GEE access has not been checked.

## Working question

How sensitive is post-monsoon agricultural-stress detection in Beed to the observation window, drought threshold and irrigation/land-cover context, and which design agrees best with independent agricultural outcomes?

Working title: Evaluating post-monsoon vegetation-stress indicators in Beed using rainfall context and crop-outcome validation.

A combined drought framework already exists for Marathwada. The credible course contribution is a transparent baseline comparison and sensitivity evaluation. A claim of new methodology must wait for the wider literature review and results. An October vegetation trend alone cannot establish land degradation.

## Scientific setting

Rainfall deficits can reduce soil moisture, stress crops and affect yields, but timing, heat, soil properties, irrigation and crop choice modify these relationships. Crop harvest can reduce greenness without water stress. Irrigation can maintain greenness during deficient rainfall. Permanent land-use change can alter a trend without being drought.

Distinguish meteorological drought, agricultural drought, water-storage drought and long-term degradation. A normal dry season is not automatically an anomalous drought. Compare like seasons and land-cover types against an explicit reference period.

## Minimum viable experiment

1. Confirm a documented Beed polygon and boundary vintage. Check taluka names/geometry against official sources. Preserve exact source metadata and checksum.
2. Start with MODIS 2001–2025 for seasonal context and Landsat 8 2013–2025 for finer vegetation detail, subject to data completeness. The original 2016–2025 window can remain a sensitivity subset, but misses 2014–2015. Keep the two sensors' series separate unless calibration is demonstrated.
3. Build one October composite and inspect true colour, NDVI, clouds/shadows, eligible land and valid coverage before batching years. Surface-reflectance scaling, QA flags, saturated pixels and time-window rules must be documented.
4. For the baseline, retain monthly Oct, Nov and Dec NDVI/VCI; calculate MODIS TCI/VHI where quality allows. Align the differing 8- and 16-day products explicitly. Do not claim a thermal stress map has 30 m independent detail after resampling 1 km temperature.
5. Test a fixed October window against a predeclared Oct 1–Nov 15 alternative. Only add phenology-aligned windows after a reliable seasonal trajectory and rules are defined. Avoid selecting each year's window to maximize the desired finding.
6. Use an independently defined cropland population. Track annual land-cover changes and compare a fixed eligible footprint with an annual mask as a sensitivity analysis. A stable-only mask can omit genuine transitions; report the excluded area. Do not define eligible crops using the same current-year NDVI threshold being evaluated.
7. Use a validated irrigation mask if available; otherwise report irrigation as unresolved and defer rainfed-versus-irrigated causal claims. Sugarcane is not identifiable from a generic cropland class alone.
8. Compute seasonal rainfall totals/anomalies and SPI-3 from a long CHIRPS record, with a specified reference period and distribution fit. Inspect rainfall coverage and compare with independent IMD observations if obtainable. Gridded rain resampled to Landsat remains coarse evidence.
9. Report continuous NDVI/anomaly and stress area fractions. Keep green area (NDVI above a vegetation threshold) distinct from drought area (stress classification).
10. Validate against crop-specific detrended yield anomalies and dated official drought reports matched to area and crop season. Yield is production divided by harvested/cropped area with compatible definitions. Declarations are useful contextual labels, not perfect field-level ground truth.

## Comparisons that make this research

| Comparison | What it tests | Evidence required |
| --- | --- | --- |
| Fixed window vs wider/phenology-aware window | Crop timing sensitivity | Coverage, season curves, held-out crop outcomes |
| Published thresholds vs locally calibrated thresholds | Misclassification from generic cutoffs | Sufficient independent training/validation years |
| Whole AOI vs cropland vs irrigation strata | Composition and management effects | Reliable masks and documented uncertainty |
| NDVI/VCI alone vs thermal/rainfall context | Whether additional variables help | Same evaluation years and outcomes for both |
| Full period vs 2016–2025 subset | Short-record instability | Slopes, intervals and extreme-year sensitivity |

Hold out years before threshold tuning. Where data are scarce, use blocked/leave-year-out validation with calibration nested inside each training fold. Keep drought and non-drought examples. Match district-level yield validation to district-level summaries; do not assign one district label to thousands of pixels and count them as independent samples.

Predeclare a reference climatology. For example, MODIS 2001–2020 can define a retrospective baseline, with 2021–2025 reserved for evaluation if all required inputs exist. That leaves few test years; report uncertainty honestly. Historical maps within baseline years are retrospective descriptions, not out-of-sample forecasts. Compare reference-period choices. Handle zero VCI/TCI denominators explicitly and document whether outside-range values are retained or clipped.

## Rainfall adjustment and trends

The main drought analysis must retain rainfall-driven stress. A separate exploratory question can ask whether vegetation changes remain after conditioning on measured rainfall.

A simple starting model is NDVI_y = intercept + b × antecedent_rain_y + c × year + error_y. Do not fit many controls to ten annual points. Check rainfall/year dependence and influential years. A residual trend is unexplained by this model, not proof of human-caused degradation; omitted weather, pests, irrigation, crop switches and measurement effects remain.

Sen's slope describes magnitude; Mann–Kendall tests monotonic association. Check serial dependence and multiple testing. Use year/block-aware uncertainty rather than treating neighboring pixels as independent replication. Bootstrap choices must respect dependence and the limited number of years. Report interval width and leave-one-year-out sensitivity, including when conclusions are inconclusive.

Forecasting is a separate extension. If attempted, use predictors available before a defined future target, blocked future-year tests, and simple persistence/climatology baselines. Predicting same-date VHI from VCI and TCI is formula reconstruction.

## First deliverables and division of work

| Owner | Before the next substantive analysis review | Completion criterion |
| --- | --- | --- |
| A: literature/metrics | Review the next relevant papers, especially combined Marathwada and regional-threshold studies | Exact methods/evidence and page anchors; distinguish missing from absent |
| B: pipeline | Verify GEE access, AOI and one October composite | Map inspection, per-pixel counts, valid-area fraction, dataset/version log |
| C: validation/statistics | Source crop statistics and drought documents; define season matching and holdout | Data availability table with years, crops, units, geography and provenance |

First quantitative output: one table per year/window with eligible area, valid area, valid coverage, NDVI median/quantiles, VCI/VHI summaries where defensible, green/stress area fractions, rainfall, and validation availability. No inferred values for missing years.

## Questions for the supervisor

- Is agricultural-stress evaluation the primary outcome, or is there an explicit requirement to study land degradation?
- Which crop statistics and irrigation layers can the group realistically access?
- Is the two-sensor design feasible within the remaining course time?
- Should transfer testing be optional after the Beed pilot passes validation?
- Which previously studied baseline should we reproduce most closely?

Transfer should reuse code with explicit regional configuration. Compare frozen Beed settings against local recalibration separately. If the crop calendar or masks need adjustment, report that requirement rather than claiming polygon-only generality.

## Data documentation already identified

- Landsat 8: https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2
- MODIS NDVI: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A2
- MODIS LST: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD11A2
- CHIRPS: https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY

These are candidate inputs, not verified Beed exports. Complete seasons through 2025 avoid the incomplete October 2026 window.
