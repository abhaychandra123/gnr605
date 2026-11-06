# Controlled seasonal reconstruction and precipitation baseline

**Historical extended pipeline.** The user's clarified course assignment is now completed in [pipeline/assignment](../assignment/README.md): Beed, October 2015–2024, downloaded multispectral images, explicit vegetation-area calculations and year–area plots. Read the [assignment report](../../results/assignment/assignment_report.md) first. The VHI/SPI/yield work below remains intact as separate exploration and is not required for the assignment.

## Completed corrected-boundary and crop-impact stage

The latest [executed report](../../results/study_corrected/research_results.md) uses
Survey of India ABDB2025 Beed (LGD523) and fixed WorldCover2021 cropland fractions.
Data are separate in `data/study_corrected/`, with results in `results/study_corrected/`.
Original GAUL results remain untouched. The corrected stage contains 240 controlled
comparison rows, 288 historical C/D indicator rows, 528 rainfall rows and 125 crop
records from 25 official annual PDFs. The 2001-2019 indicator reference excludes
its target year for historical association; 2020-2024 uses the fixed reference.
This is retrospective evaluation, not prospective forecast validation.

The previous-year yield benchmark beat all 30 indicator calibrations on the five
2020-2024 evaluation years. The historical trend underpredicted all 15 crop-year
outcomes. Coverage improvements and positive gains over that weak trend baseline
must not be reported as established crop-impact prediction skill.

Reproduce (commands run from repository root, dependencies already in `.venv`):

```sh
.venv/bin/python pipeline/study/execute_corrected.py --project weighttrack-493810
.venv/bin/python pipeline/study/harmonize_yields.py
.venv/bin/python pipeline/study/review_corrected_mask.py
.venv/bin/python pipeline/study/review_corrected_rain.py
.venv/bin/python pipeline/study/analyze_impacts.py
.venv/bin/python -m unittest discover -s pipeline/study -p 'test_*.py' -v
.venv/bin/python pipeline/study/report_corrected.py
```

The executor checks implementation and geometry hashes before reusing checkpoints.
`prefill_corrected.py` was an optional bounded parallel retrieval helper; it is not
needed to reproduce completed checkpoints. The source snapshots preserve the exact
Earth Engine computations. Crop extraction records source strings, units, page,
SHA256 and extraction method; rendered source reviews are logged separately.

The mask download is retained as `worldcover2021_crop_fraction_soi_beed.ee_original.tif`.
Its exported WGS84 spheroid tag lost the native projection's sphere overrides in GDAL.
The companion `.tif` explicitly encodes the MODIS 6371007.181m sphere; pixel values
and transform are identical. Provenance records both hashes and the source definition.
No local TIFF was used for the server-side numerical reductions.

The following sections document the earlier provisional GAUL experiment.

Executed 6 November 2026 using project `weighttrack-493810`. All 936 rows are local
in `data/study/`. Read `results/study/research_results.md`, `execution_manifest.json`,
and `cross_run_validation.json` for actual findings and provenance. No synthetic
values are used as Beed observations. The 12 tests include statistical fixtures and
corruption checks on the downloaded real exports.

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

The GAUL 2015 Bid polygon was compared with official Survey of India ABDB 2025:
8.56% of its area lies outside official Beed and intersection-over-union is 90.12%.
Most excess overlaps present-day Ahilyanagar. The primary experiment retains GAUL
for exact comparability with the earlier audits; it is not a validated current-Beed
assessment. Candidate cropland/irrigation masks and 25 official annual crop tables
were acquired separately. Annual irrigation, crop species, crop calendars and a
boundary-consistent rerun remain prerequisites for impact validation.

## Rainfall and local analysis

CHIRPS daily data are summed only where every expected daily input is present.
Means use pixel-area weights on the native rainfall grid. Native-grid district area
can differ slightly from MODIS-grid area. Local SPI additionally requires essentially
full district coverage, so changing valid footprints are not fitted as a climate series.

The three real exports are already in `data/study/`. Reproduce local analysis from
the repository root:

```sh
.venv/bin/python pipeline/study/analysis.py
.venv/bin/python pipeline/study/review_results.py
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

Network access works outside the sandbox. Dependencies are installed in `.venv`;
`requirements-executed.txt` captures installed versions, including ancillary readers.
The user completed Google's local OAuth flow; credentials remain in the standard
local Earth Engine configuration and are not stored in this repository.

`execute_ee.py` implements the JavaScript experiment in Python. The live A/October/2020
preflight exactly reproduces coverage, VHI and grid area. Three Drive batch tasks were
submitted; the comparison remained running and retried internally while the others
queued. All results were therefore retrieved with the same computation graphs through
official `ee.data.computeFeatures`, by month (comparison/history) or year (rainfall).
After validation, only these three redundant batch jobs were cancelled. A submitted
batch task is not being represented as a completed Drive export.

Each direct request has a JSON checkpoint, UTC retrieval timestamp and implementation
hash. `finalize_exports.py` verifies CSV contents against all checkpoints; source
snapshots are in `data/study/tasks/`. Existing completed files are preserved on rerun.
Original JS and Andure scripts remain intact.

For a new output directory, the network execution command is:

```sh
.venv/bin/python pipeline/study/execute_ee.py --project weighttrack-493810 --mode direct --output-dir NEW_DIRECTORY
```

Use `--mode preflight` for the live reference check. `--mode batch` and
`retrieve_ee.py` retain batch submission/retrieval support. Do not silently reuse
checkpoints across changed implementations. `acquire_masks.py`, `acquire_public.py`,
`review_boundaries.py`, and `extract_crop_tables.py` document ancillary acquisition
and inspection. Crop extraction retains source units and logs 32 ambiguous cells
instead of guessing their row alignment.

```sh
node --check pipeline/study/export_study_gee.js
.venv/bin/python -m unittest discover -s pipeline/study -p 'test_*.py' -v
.venv/bin/python pipeline/study/check_access.py --project weighttrack-493810
```

Sources: MOD13A2 and MOD11A1/MOD11A2 official Earth Engine catalogues;
CHIRPS v2 catalogue; WMO SPI User Guide (2012); UCAR NCL SPI guidance on gamma MLE.
This is a documented methodological reconstruction, not author-code replication.
