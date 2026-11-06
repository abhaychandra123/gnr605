# Assignment scope and fixed method

7 November 2026. This supersedes the earlier extended research proposal for the course assignment; all earlier work is preserved separately.

Problem: identify a long-term drought-prone area in India; obtain satellite images spanning ten years for one post-monsoon month; compute vegetation-covered area; plot year against area; assess whether cover is low or decreases each year.

Study area: fixed official Survey of India ABDB2025 Beed district, Maharashtra, LGD523. Period: October 2015-2024 (ten complete years, aligned to the existing study endpoint). Do not select years or change boundaries in response to the results. Historical boundary exactness is not claimed.

Input: NASA Terra MODIS MOD09A1 Collection6.1 eight-day surface reflectance at native nominal500m (actual grid spacing about463.313m), seven spectral bands including red, near-infrared and shortwave infrared, plus QA, StateQA and selected-pixel DayOfYear. Download all source composites potentially containing October observations, not a precomputed NDVI product. Include late-September composite starts only when their selected-pixel dates fall inside October.

Assignment calculations are implemented explicitly in local Python: native sinusoidal coordinate equations, scanline polygon mask, quality-bit decoding, NDVI=(NIR-red)/(NIR+red), accumulation/count division, fixed-threshold classification, pixel counting, least-squares slope and adjacent-year differences. Rasterio is limited to raster file reading/writing and metadata; NumPy to array storage; Matplotlib to display/plotting. Earth Engine is used for locating/selecting/downloading source image bands on their native grid, not vegetation indices, monthly reducers, classification or area statistics. No image-analysis, classifier, trend-fitting or segmentation built-ins are used in the core computation.

Primary QA: clear StateQA cloud state0; no shadow, internal cloud, cloud adjacency, MOD35 snow or internal snow; land class1; aerosol not high (code3 excluded); no cirrus. MODLAND QA0; highest-quality red/NIR bands. Red/NIR must be nonnegative and <=10000 raw units, sum>0; reflectance scale0.0001. Remaining bands must lie within their published valid range -100..16000. Their band-quality flags are not independently screened, so visual composites are illustrative; NDVI uses only screened red/NIR.

Monthly NDVI is the arithmetic mean of accepted October selected-pixel observations; it is not a daily time-weighted mean. At least2 accepted composites required per pixel. Display a min1-observation sensitivity, without replacing the primary rule.

Vegetation is operationally defined as monthly mean NDVI>0.30, held fixed across years. Show thresholds0.20 and0.40 as sensitivity; no threshold is tuned to obtain decline. This is green-vegetation presence in coarse mixed pixels, not fractional plant cover or permanent forest area. No universal definition of 'low' vegetation or pixel-level field ground truth is supplied by the assignment.

Area equals manually counted eligible pixel centres times the squared native spacing in km². Fixed pixel-centre district mask and native spherical grid introduce boundary and projection approximations, stated alongside the original vector area. Missing pixels are unknown, never nonvegetation. Whole-district vegetated-area bounds are observed vegetated area through observed area+unknown area. For fair year-to-year comparison also use the intersection of valid pixels across all ten years, and disclose how much of the district this common footprint covers. Do not extrapolate common-footprint area to unobserved district pixels.

Report the actual direction, nine adjacent-year changes and descriptive slope. Do not force a decrease or claim that one month's vegetation series alone proves drought, land degradation or causality. Official drought history supplies independent contextual evidence, not annual October vegetation-class ground truth. Yield forecasting, VHI/TCI/SPI modelling, crop-target auditing and ML are out of scope for this deliverable.


## Documented coverage amendment before final interpretation

The initial min2 run yielded only4.2384% common district coverage, driven by low repeat-observation availability in2019,2022 and2024. The min1 sensitivity yielded65.6589%. To meet the assignment's October-image requirement with a useful comparable footprint, min1 is the primary analysis; min2 remains the stricter temporal-support sensitivity. The initial tables, summaries and source snapshot are retained in initial_min2_audit/. Cloud/reflectance QA, the NDVI thresholds, month, years and boundary are unchanged. The final report explicitly states that one accepted observation may not represent the whole month. No whole-district extrapolation is performed. NDVI calculations and storage use float64; strict threshold comparisons use a1e-12 tolerance to avoid roundoff at equality.
