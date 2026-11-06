# Controlled seasonal reconstruction and precipitation baseline

Prepared 6 November 2026. Run status is recorded in `results/study/execution_status.json`.
The satellite computations below have NOT executed in this session. No synthetic values
are used as Beed observations. Tests use synthetic fixtures only.

## Satellite experiment

`export_study_gee.js` creates three GEE Drive exports in a single run:

| File/task | Rows | Contents |
| --- | ---: | --- |
| beed_controlled_seasonal_2020_2024 | 120 | 15 Oct/Nov/Dec months × 4 variants × own/shared support |
| beed_policy_history_2001_2024 | 288 | 24 years × 3 months × 4 variants, current coverage and NDVI |
| beed_chirps_monthly_1981_2024 | 528 | Full monthly rainfall record for district SPI |

Variants isolate changes sequentially:

- A: original strict MOD13A2 start-date selection and MOD11A2 start-date selection.
- B: NDVI selected-pixel dates, strict QA; same MOD11A2 as A.
- C: B plus marginal NDVI with SummaryQA=1, MODLAND=1, usefulness explicitly 1 or 2,
  aerosol=2 and all original detailed exclusions. Original good observations retained.
- D: C with daily MOD11A1 LST restricted to the calendar month, strict LST QA.

B–A isolates NDVI timing; C–B isolates the candidate QA change. D–C is an LST
product/aggregation comparison, not a pure date-only effect. Daily LST is a mean of
accepted clear-sky retrievals, not an all-weather monthly temperature. At least one
accepted observation per pixel/month is the explicit initial setting; observation
counts are exported. More defensible monthly support thresholds need assessment.

Each variant rebuilds its own same-calendar-month reference for 2001–2019, with
15 valid years required. No threshold reduction is mixed into this primary test.
Evaluation months 2020–2024 follow the reference period. Historical NDVI is exported
for context; 2014/2015 are not held-out validation years against this reference.
The code supports October through December, including the December year boundary.
It rejects January because a different cross-year selected-date implementation is needed.

Each comparison row reports coverage, means of all five indices on identical
VHI-valid support, mean observation counts, reference support/ranges, exclusive class
fractions, unclassified area and out-of-[0,100] VHI fraction. Values are not clipped.
Class bins are <10, [10,20), [20,30), [30,40), >=40, literature-inspired and uncalibrated.
The shared support is the intersection of all four variants WITHIN one month; it is
not a fixed footprint across years. Class disagreement with A uses pairwise overlap.
These means alone must not be presented as a land-condition trend.

The GAUL 2015 Bid polygon remains provisional. The optional boundary asset must be
verified before geographical or crop-specific conclusions. The mask is land QA, not
cropland. Irrigation, sugarcane and crop calendar remain independent validation needs.

## Rainfall and local analysis

CHIRPS daily data are summed only where every expected daily input is present.
Means use pixel-area weights on the native rainfall grid. Native-grid district area
can differ slightly from MODIS-grid area. Local SPI additionally requires essentially
full district coverage, so changing valid footprints are not fitted as a climate series.

Download the three exports as CSV into `data/study/` with their task names above.
Then run, from repository root:

```sh
python3 pipeline/study/analysis.py
```

The runner always computes screened-coverage bounds from existing real uploaded
exports. It computes the new satellite comparison and rainfall SPI only when the
corresponding real export exists, recording missing stages explicitly.

SPI-1/3/6/12 use a 1981–2019 reference, independently per ending calendar month;
two-parameter gamma maximum-likelihood fit on positive totals; q=zeros/n; mixed CDF
q+(1-q)G(x); standard normal inverse. Min 30 valid reference totals and 20 positive
totals are declared implementation requirements. Degenerate reference distributions
remain missing. Zero totals use CDF=q. Probability clipping at 1e-8 and 1-1e-8 avoids
infinite numerical output and is recorded in the fit diagnostics. Missing months
invalidate rolling accumulations. Fit parameters do not use post-2019 observations.
This is SPI of the district-average rainfall series, not a map or mean of pixel SPI.
Gamma fit suitability must still be inspected before interpreting tail categories.

Rainfall trend outputs are exploratory JJAS and OND complete-year aggregates, with
Kendall tau, uncorrected independence-based p-values, Sen slope and its conventional
interval, plus adjacent-year lag-one correlation. Serial-dependence adjustments and
multiple-comparison control are not claimed. Do not report naive p-values as settled
trend evidence. Five-year vegetation trend inference and ML are deliberately absent.

## Execution and access

The local session cannot resolve public data hosts and has no EE Python package or
credentials. There is no browser-control tool. The GEE export script passes Node's
syntax check; this does not establish successful server computation. A network-enabled,
authenticated session still needs to run GEE, download exports, inspect results and fix
any server errors. The current GEE script prepares Tasks; it does not submit them.
A Python equivalent or browser execution is needed for fully autonomous submission.

```sh
node --check pipeline/study/export_study_gee.js
python3 -m unittest discover -s pipeline/study -p 'test_*.py' -v
python3 pipeline/study/check_access.py --project YOUR_PROJECT_ID
```

Sources: MOD13A2 and MOD11A1/MOD11A2 official Earth Engine catalogues;
CHIRPS v2 catalogue; WMO SPI User Guide (2012); UCAR NCL SPI guidance on gamma MLE.
This is a documented methodological reconstruction, not author-code replication.
