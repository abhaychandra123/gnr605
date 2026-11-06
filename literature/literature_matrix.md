# Literature extraction matrix

Updated 27 October 2026. All three requested full PDFs read. NR means not clearly reported, not proof that a step was never performed. Detailed page anchors and critiques are in notes/paper_review.md.

| Paper | Region/period/sensor/resolution | Indicators | Thresholds and local calibration | Rainfall, irrigation, calendar and land cover | Validation | Statistics, sample size and limitations |
| --- | --- | --- | --- | --- | --- | --- |
| Taji & Keskar, 2022; DOI 10.1016/j.matpr.2021.09.523 | Beed study region; 1979–2013 stated as 34 years; CFSR reanalysis at 11 extraction locations; printed resolution inconsistent | SPI-1/3/6/9/12 in framing; 1/3/6/12 emphasized in results | Moderate -1 to -1.49; severe -1.5 to -1.99; extreme ≤-2; literature thresholds, no crop-based local calibration | Rainfall only; seasonal interpretation; no irrigation/crop masking analysis | Historical/documentary event comparison; yield validation proposed as future work | MK at 5%, Sen slope, sequential MK, IDW maps; serial independence asserted; largely nonsignificant annual/monsoon trends; AOI/date/event-label inconsistencies |
| Somni et al., 2021; DOI 10.12691/aees-9-7-5 | Marathwada, Oct–Dec 2001–2017; MOD13A2 NDVI 16-day/1 km; MOD11A2 LST 8-day/1 km | VCI, TCI, VHI; 0.5/0.5 weights | VHI breaks 10/20/30/40; printed bins overlap at boundaries; no demonstrated local calibration | Month-specific mapping; contextual monsoon rainfall; irrigation/crop masks NR | No implemented SPI, yield or field validation found; SPI/SWI discussion is about prior studies | 17 nominal years × 3 months; some October inputs missing; map interpretation; formal trend tests NR; detailed QA/compositing recipe missing |
| Andure et al., 2025; DOI 10.64252/y0bxsk22 | Beed and Maharashtra; figures 2020–2024, prose partly 2020–2023; precise product/resolution/sampling unit unclear | NDVI, LST, rainfall, SPI-3, VCI, TCI predict VHI | VCI/TCI/VHI <40 stress; >60 favorable; calibration not demonstrated | Irrigation and crop/land-cover controls NR; seasonal dry/monsoon contrasts | CV reported; headline fit on whole dataset; ground validation asserted without auditable results | n=262/2355; CV R²=.977/.993; whole-data R²=.998/.999; target constructed from inputs; lead time/folds/estimator insufficiently documented; sparse SPI-3; unit inconsistencies |
| Kulkarni et al., 2020; DOI 10.3390/rs12132091; additional prior-art screen | Marathwada, 2001–2018 | SPI-3, LST, soil moisture, NDVI | Combined indicator; full audit pending | Cropland mask | Detrended crop yields | Fixed versus PCA weights; establishes substantial prior overlap |

## Reading queue

1. Kulkarni et al. (2020), full replication/evaluation audit: https://doi.org/10.3390/rs12132091
2. Pandya & Gontia (2024), Saurashtra threshold calibration: https://doi.org/10.54302/mausam.v75i2.6077
3. Sandeep et al. (2021), CHIRPS/MODIS agricultural drought in peninsular India: https://doi.org/10.1016/j.ecolind.2020.107033 (identified from Taji reference 12; not yet independently reviewed).
4. Dutta & Kundu (2015), Rajasthan VCI/SPI: https://doi.org/10.1016/j.ejrs.2015.03.006 (Taji reference 11; not yet independently reviewed).
5. Pandey et al. (2021), Bundelkhand CHIRPS/SPI trends: https://doi.org/10.3390/su13031042 (Taji reference 3; not yet independently reviewed).
6. Duraisamy et al. (2018), Mula-Pravara land-use drivers: https://doi.org/10.1007/s10661-018-6919-5 (likely relevant to the meeting reference; exact intended citation unconfirmed).

For each later paper record baseline years, data product/version, units, sampling unit, missingness, mask vintage, calibration/test separation and forecast lead time. Do not populate unverified cells from another paper's review table.
