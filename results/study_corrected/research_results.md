# Corrected Beed reconstruction and exploratory crop-impact comparison

Executed and retrieved using authenticated Earth Engine project `weighttrack-493810`. **Main finding: the previous-year-yield baseline outperformed all 30 tested indicator calibrations on 2020-2024 MAE. Better satellite coverage did not establish crop-impact predictive skill.** All earlier GAUL runs and original PDFs are preserved. No batch-task submission is being counted as a completed result. New outputs come from completed official `computeFeatures` requests and an actual GeoTIFF download.

## What was completed

- 240 comparison rows: 2020-2024 Oct-Dec, all four original policies, own/common support, official-district and cropland-fraction weighting.
- 288 impact-history rows: 2001-2024 Oct-Dec, policies C/D, both spatial weightings.
- 528 monthly CHIRPS rows for 1981-2024 over official Beed, all with complete rainfall support. SPI-1/3/6/12 fitted using 1981-2019 only.
- 125 harmonized official crop records: 25 agricultural years, five crops. Rabi jowar, wheat and gram/chickpea used for this impact check; soybean and cotton retained for future season-specific work.
- Every completed CSV matches its saved request checkpoints and SHA256 manifest. Expected key sets, VHI arithmetic, class partitions, support fractions and duplicate independently reconstructed 2020-2024 C/D values passed validation. Fifteen tests passed, including temporal leakage and original real-data corruption checks.

## Boundary and cropland correction

The official Survey of India ABDB2025 polygon (Beed LGD523) replaces GAUL for this rerun. Its MODIS-grid integration is **10602.13 km²**; the WorldCover2021 cropland weights total **8143.02 km²**, or **76.81%** of that area. Grid-integrated areas differ slightly from vector equal-area estimates. Only unused zero height coordinates were removed for Earth Engine; the supplied polygon was not simplified.

Across all 120 matched date/policy/support combinations, changing GAUL to official Beed changes VHI by -8.39 to 1.02 points (median absolute change 0.39). Within official Beed, applying crop-fraction weights changes VHI by -3.04 to 1.20 points. Those comparisons can include different valid footprints; they do not isolate a physical vegetation change.

WorldCover class 40 was aggregated from 10m via 100m to the native MODIS grid. Fractions multiply pixel area exactly once. The fraction raster was downloaded and inspected, with values in [0,1] and exact MODIS grid alignment. The original GeoTIFF's CRS tag loses the native 6371007.181m sphere overrides when read by GDAL; its coordinates otherwise match the native grid. A corrected local copy explicitly encodes that sphere, preserving pixel values and transform exactly, with the original download retained. The native definition was verified against Earth Engine's projection WKT and [NASA's MODIS projection definition](https://modis.ornl.gov/files/modis.prj). No downloaded TIFF enters the server-side numerical reductions. These are cropland-weighted **mixed-pixel** retrievals, not species-specific crop pixels. The fixed current boundary and fixed 2021 land-cover map do not recreate each historical year's geography or cropland.

October VHI coverage, percent of weighted cropland support:

| year | A | B | C | D |
| --- | --- | --- | --- | --- |
| 2020 | 22.510 | 37.810 | 83.530 | 83.600 |
| 2021 | 5.020 | 9.650 | 82.860 | 82.930 |
| 2022 | 29.430 | 51.800 | 83.690 | 83.760 |
| 2023 | 1.430 | 40.100 | 82.550 | 82.620 |
| 2024 | 0.690 | 14.310 | 63.820 | 63.850 |

Coverage improvement does not establish crop-damage accuracy. On policy C's crop-weighted support, the largest out-of-[0,100] VHI area fraction is 67.06% in 2023-12. Values remain unclipped. Daily LST policy D is a clear-sky product/aggregation sensitivity, with only one accepted current observation required per pixel/month; it is not all-weather temperature.

## Crop-table repair and alignment

The previous raw extract had split crop headings and some unit subheaders mislabelled as crops. The new extractor merges complete header groups, aligns Beed within merged district cells, and compares table extraction with complete text rows where possible. Of 125 target records, 121 agree between both methods, three use unambiguous table alignment, and one (2019 soybean, a missing right table border) uses the complete printed text row. Problematic pages and recent-year values were visually inspected. All 125 area/production/yield identities are compatible with their displayed rounding; reported yield is retained, never replaced by an inferred ratio.

Area is normalized from hundreds of hectares, grain production from hundreds of tonnes, and cotton production from hundreds of 170kg bales. Cotton yield is lint kg/ha. The PDF title/version, page, original numeric strings, units and source SHA remain attached to each row. Some source tables are explicitly final advance estimates, not independent field-level measurements. The three rabi crops repeat exactly the same reported area in 2019, 2020 and 2021; these source values are retained and flagged. No external revision audit is claimed.

OND year y is paired with the agricultural-year y-(y+1) rabi yield. The historical [ICAR-CRIDA Beed contingency plan](https://www.icar-crida.res.in/CP-2012/statewiseplans/Maharastra(Pdf)/MAU,%20Parbhani/Maharashtra%2027-Beed-3%201-12-2011.pdf), p.5, places rainfed gram/sorghum sowing in early October and irrigated wheat sowing in November. The [Beed Gazetteer](https://www.gazetteers.maharashtra.gov.in/cultural.maharashtra.gov.in/english/gazetteer/Beed/agri_seasons.html) places rabi harvest in February-March. Thus OND is only early-season context, including pre-establishment October for wheat. Later weather and irrigation can change outcomes. Neither source supplies year-specific observed planting dates.

## Actual exploratory impact agreement

The protocol was written before examining these corrected outcome correlations, but this is a continuation of previously inspected data, not a blinded test or preregistration. Yield trends and simple one-indicator residual regressions use 2001-2019 only. Evaluation uses 2020-2024. For reference-period VHI, the target year is left out of the 2001-2019 extrema; post-2019 VHI uses the fixed reference. Training reconstructions still use information from other future reference years, so this is **retrospective agreement, not demonstrated operational forecasting**.

All three OND months must have at least 50% weighted VHI coverage for a seasonal mean. Tightening to 75% is reported separately. Eligible seasons (out of 24 per row):

| spatial_weighting | scenario | eligible_50pct | eligible_75pct |
| --- | --- | --- | --- |
| all_land | C | 24 | 22 |
| all_land | D | 24 | 22 |
| worldcover2021_crop_fraction | C | 24 | 22 |
| worldcover2021_crop_fraction | D | 24 | 22 |

The following table reports every predeclared main VHI/SPI check for all three crops. MAE is kg/ha. Positive gain means lower test error than the training-only linear yield trend; negative gain means worse error. Test rho is the Spearman correlation between indicator and detrended yield, based on only five years where all are eligible. No statistical significance or selected winning model is claimed.

| Crop | Indicator | Train n | Test n | Test rho | Trend MAE | Previous-year MAE | Indicator MAE | MAE gain |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chickpea | December SPI-3 | 19 | 5 | 0.700 | 232.177 | 94.658 | 225.131 | 7.046 |
| chickpea | December SPI-6 | 19 | 5 | 0.600 | 232.177 | 94.658 | 190.027 | 42.150 |
| chickpea | C crop VHI | 19 | 5 | 0.100 | 232.177 | 94.658 | 168.452 | 63.726 |
| chickpea | D crop VHI | 19 | 5 | 0.100 | 232.177 | 94.658 | 163.238 | 68.939 |
| rabi_jowar | December SPI-3 | 19 | 5 | -0.300 | 744.254 | 258.132 | 717.973 | 26.282 |
| rabi_jowar | December SPI-6 | 19 | 5 | -0.400 | 744.254 | 258.132 | 662.820 | 81.434 |
| rabi_jowar | C crop VHI | 19 | 5 | -0.400 | 744.254 | 258.132 | 592.124 | 152.130 |
| rabi_jowar | D crop VHI | 19 | 5 | -0.900 | 744.254 | 258.132 | 587.351 | 156.904 |
| wheat | December SPI-3 | 19 | 5 | 0.600 | 913.497 | 316.622 | 858.047 | 55.450 |
| wheat | December SPI-6 | 19 | 5 | 0.300 | 913.497 | 316.622 | 751.516 | 161.981 |
| wheat | C crop VHI | 19 | 5 | -0.700 | 913.497 | 316.622 | 668.800 | 244.697 |
| wheat | D crop VHI | 19 | 5 | -0.700 | 913.497 | 316.622 | 656.241 | 257.256 |

Full results, including raw NDVI, whole-district weighting, training correlations, climatology and persistence comparisons, are in `impact_agreement.csv`. Individual test-year observations and predictions are in `test_predictions.csv`. Leave-one-test-year-out ranges assess sensitivity to those five years; they are not confidence intervals. Coverage sensitivity at 75% changes the evaluated subset only, retaining the original fitted model.

The apparent improvement over the old trend baseline is insufficient: previous-year yield has lower MAE than every one of the 30 tested calibrations. For crop-weighted C VHI, MAE is 168.5 versus 94.7 kg/ha for chickpea, 592.1 versus 258.1 for rabi jowar, and 668.8 versus 316.6 for wheat (indicator versus previous-year yield). All 15 crop-year test yields are above their fitted historical trends, so this evaluation contains **no below-trend yield-loss events** under that definition. The level shift and possible source-estimate changes must be investigated before treating this residual as a crop-loss target.

For crop-weighted policy C VHI, test rank correlations range from -0.70 to 0.10, and MAE gains over the simple trend range from 63.7 to 244.7 kg/ha. These three crops are not independent replications of the weather exposure. Multiple inspected indicators, changing footprints, irrigation, crop mixture, estimated yields and only five recent evaluation years prevent a general accuracy claim.

Reported yield departures from the pre-2020 linear trend (%):

| year | chickpea | rabi_jowar | wheat |
| --- | --- | --- | --- |
| 2020 | 45.669 | 157.603 | 98.786 |
| 2021 | 38.424 | 138.177 | 80.169 |
| 2022 | 28.192 | 134.284 | 97.827 |
| 2023 | 10.250 | 191.499 | 80.283 |
| 2024 | 23.748 | 130.666 | 65.346 |

December district-average precipitation indicators:

| year | spi_3 | spi_6 |
| --- | --- | --- |
| 2020 | 1.028 | 0.933 |
| 2021 | 0.320 | 0.991 |
| 2022 | 1.639 | 1.707 |
| 2023 | -0.171 | 0.339 |
| 2024 | 0.101 | 0.729 |

SPI measures rainfall anomaly, not observed crop damage. Its spatial support is the full official district on the native rainfall grid; it is not a cropland-weighted pixel SPI map. Corrected gamma-fit checks used 1,999 refitted parametric bootstrap replicates per fit. January SPI-1 has raw p=.003, November SPI-1 p=.006, and December SPI-1 p=.0255; the smallest Holm-adjusted p across 48 checks is .144. These departures warrant care, and failure to reject after adjustment does not establish distributional correctness or rare-tail accuracy. Q-Q plots and all fit checks are retained in `spi_gamma_qq.png` and `spi_gamma_fit_review.csv`.

## Deliverables and limits

- `corrected_comparison.png`: actual coverage and VHI under corrected geography/weighting.
- `cropland_weighting.png`: actual retrieved crop-fraction grid.
- `yield_indicator_history.png`: observed yield residuals alongside crop-weighted policy C VHI.
- `holdout_error_comparison.png`: absolute test errors against training-mean, trend and previous-year-yield baselines; test-year sensitivity is in the CSV.
- `validation.json`, data CSV provenance sidecars, request checkpoints and source snapshots: reproducibility evidence.

This completes the corrected rerun, yield harmonization and an exploratory independent-outcome check. It does not justify a complex ML architecture or a crop-loss forecasting claim. A stronger next study needs crop-specific annual spatial support, year-specific irrigation/management and planting dates, publication-time data availability, reconciliation of crop-estimate revisions, and more independent held-out district-seasons. These are scientific data limitations, not terminal/download or authentication failures. No manual download or login is currently required from the user.
