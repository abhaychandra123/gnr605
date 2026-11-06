# Beed drought project: critical reading notes

Reviewed 27 October 2026. All three supplied PDFs are now present locally. The rainfall paper is 10 pages, the Marathwada MODIS paper 24 pages, and the machine-learning paper 16 pages. Page references below use printed page numbers. Findings attributed to authors are distinguished from our interpretation. No satellite analysis has yet been run.

## 1. Taji and Keskar: precipitation trends in Beed

Source: ../papers/1-s2.0-S221478532106449X-main.pdf
DOI: https://doi.org/10.1016/j.matpr.2021.09.523
Materials Today: Proceedings 61 (2022), 332–341; available online October 2021.

### Question and data

The authors ask when meteorological drought occurred and whether rainfall has changed systematically across their Beed study region. They use NCEP Climate Forecast System Reanalysis (CFSR) precipitation for 1979–2013, repeatedly described as 34 years. Eleven extraction locations are divided into eastern (5), central (3), and western (3) groups. These are reanalysis sampling locations, not a demonstrated network of eleven local rain gauges (Section 2.2, p. 334).

Reanalysis combines a physical model and observations to estimate historical conditions. Its rainfall can be useful, but should not be treated as error-free local measurement. A spatially interpolated map does not gain independent information merely because it contains more pixels.

### Workflow

1. Assemble precipitation time series and examine monthly and annual rainfall.
2. Check serial correlation. The results state that serial correlation is absent; the paper gives limited diagnostic detail (Section 3.1, p. 336).
3. Apply Mann–Kendall at the 5% significance level. This tests evidence for a monotonic change without assuming a normal rainfall distribution.
4. Estimate magnitude using Sen's slope, the median of all pairwise slopes.
5. Use sequential Mann–Kendall to identify candidate changes in trend timing.
6. Calculate SPI by fitting a gamma distribution to precipitation totals, accounting for zero precipitation, and transforming the cumulative probability to a standard normal variable (Section 2.5, p. 335).
7. Compare several accumulation timescales. The abstract/method framing includes 1, 3, 6, 9 and 12 months; the principal results and plots emphasize 1, 3, 6 and 12 months.
8. Identify drought events using SPI-12, and use inverse-distance weighting (IDW) to map the eleven point estimates (p. 337).

The reported drought classes are moderate from -1.00 to -1.49, severe from -1.50 to -1.99, and extreme at -2 or below. The event description uses a threshold of -1 for drought initiation and a return to positive SPI for termination. For our implementation, document a continuous interval convention and exact run-definition rather than relying on rounded table ranges.

### Findings

Six episodes are identified: 1985–86, 1987–88, 1992–93, 2001–02, 2005–06 and 2011–12. The authors identify 1992–93 as driest, with regional SPI-12 around -2.02. Shorter SPI windows fluctuate more frequently; longer windows reveal persistent deficits.

The authors report nonsignificant monsoon decreases in eastern/western zones and a nonsignificant increase centrally. Annual trends are also largely nonsignificant. Significant monthly results occur for some May series and December series. Do not describe this as proof of a general annual rainfall decline. A nonsignificant trend is also not proof that no change exists.

Validation consists principally of comparisons with previously reported drought histories and documentary sources. Crop-production validation is proposed as future work in the conclusion (p. 340); it was not completed here.

### Issues to record

- **AOI:** The study lists eight talukas including Jamkhed. The current official Beed list has eleven and excludes Jamkhed; an official Ahilyanagar notice places Jamkhed there. Reconcile the historical geometry rather than copying it into a current district analysis.
- **Period:** Inclusive calendar years 1979–2013 number 35. Exact start/end months or dropped data must be clarified before reproducing the authors' stated 34-year series.
- **Resolution:** The PDF prints 0.50 × 0.50 km while also referring to a 38 km atmospheric model. NCAR describes approximately 38 km atmospheric resolution. The exact delivered rainfall grid must be established from metadata; do not claim 500 m independent rainfall information.
- **Event labels:** The spatial-results prose calls event 4 “2005–06,” whereas Figure 5 labels event 4 as 2001–02 and event 5 as 2005–06. Do not copy event-specific spatial claims without checking the figure.
- **Trend interpretation:** Table 2 is monthly/annual; do not assume its entries constitute a separately reported test of aggregated June–September rainfall. A count of significant station-month tests also needs consideration of multiple comparisons.

Use this paper for SPI, timescale reasoning and trend analysis, not as a vegetation-impact or land-degradation validation study.

## 2. Somni et al.: post-monsoon drought in Marathwada

Source: ../papers/aees-9-7-5.pdf
DOI: https://doi.org/10.12691/aees-9-7-5
Applied Ecology and Environmental Sciences 9(7), 2021, 656–679.

### Question and workflow

The study maps spatial and temporal vegetation/thermal stress during October, November and December of 2001–2017 across eight Marathwada districts. It uses Terra MODIS MOD13A2 NDVI (16-day, 1 km) and MOD11A2 land-surface temperature (8-day, 1 km). The paper reports an Albers equal-area projection with WGS84 datum and processing in ENVI, ArcGIS and ERDAS Imagine (pp. 657–658).

For each pixel and relevant seasonal period:

VCI = 100 × (NDVI_current - NDVI_min) / (NDVI_max - NDVI_min)

TCI = 100 × (LST_max - LST_current) / (LST_max - LST_min)

VHI = 0.5 × VCI + 0.5 × TCI

VCI describes greenness relative to its historical range. TCI gives lower values to unusually warm conditions. VHI gives both equal weight. None directly measures soil moisture or crop yield.

Table 1, p. 659, prints extreme drought <10; severe ≥10 and ≤20; moderate ≥20 and ≤30; mild ≥30 and ≤40; no drought ≥40. These overlap at 20, 30 and 40. A reproducible implementation needs mutually exclusive bins. A possible explicitly stated convention is <10, [10,20), [20,30), [30,40), and ≥40. These remain literature-based categories, not locally validated Beed thresholds.

### Findings and validation

The maps and discussion emphasize 2014 and 2015, with other dry periods varying by month and district. October 2016 and 2017 show better vegetation conditions in the authors' interpretation. These broad comparisons do not mean every taluka had the same condition.

The paper does **not** implement SPI validation. References to SPI/SWI validation in the introduction describe earlier studies. Its own evidence is mainly index maps and contextual monsoon rainfall. No documented comparison against crop yields, field measurements, or an independent drought-label test set is presented.

### Issues to record

- Missing October NDVI inputs are reported for 2001 and 2009, and missing October LST for 2010 (p. 678). Figure 17 confirms the blank October 2010 VHI map. Missing data must remain missing, not enter an average as zero.
- The paper does not provide a sufficiently detailed quality-bit mask and temporal-compositing recipe for exact replication.
- The min/max baseline construction needs explicit seasonal indexing in our implementation. Comparing October to a year-round minimum would confuse normal seasonality with stress.
- A 1 km pixel mixes land uses. No explicit irrigation or crop-specific stratification is documented.
- Equal 0.5 weights are assumed, not estimated using local impacts.
- Agreement of VHI with VCI/TCI is partly mathematical: they are its ingredients. It is not independent validation.
- Formal Mann–Kendall/Sen estimates are not presented despite introductory references to trend analysis.

This is our seasonal mapping baseline. Extending its date range alone is an update, not evidence of methodological novelty.

## 3. Andure et al.: Beed/Maharashtra machine learning

Source: ../papers/Andure_et_al_2025_Beed_Drought_ML.pdf
DOI: https://doi.org/10.64252/y0bxsk22
International Journal of Environmental Sciences 11(8), 2025, 3914–3929.

### What was modeled

The results report 262 cleaned Beed samples and 2,355 Maharashtra samples. Six predictors (NDVI, LST, rainfall, SPI-3, VCI and TCI) estimate VHI. Figures refer to 2020–2024, while some prose focuses on early 2020–2023. Exact sensor-product IDs, spatial resolution, sampling unit and forecast horizon are not clearly documented.

Mean cross-validation R² is reported as 0.977 ± 0.028 for Beed and 0.993 ± 0.010 for Maharashtra. The headline R² values 0.998 and 0.999, with RMSE 0.836 and 0.351, are described as performance on the whole dataset (pp. 3925 and 3927). This distinction matters: they are not established independent future-year test scores.

### Methodological assessment

The paper defines VHI as a weighted function of VCI and TCI and supplies both as predictors. A model may therefore reconstruct the target from its ingredients. With the exact same underlying inputs and weights, the formula itself is the relevant zero-training benchmark. No documented future lead time establishes that it predicts drought before the target indicators become available. Cross-validation does not resolve this target-construction problem.

Do not infer from near-zero rainfall importance that rainfall does not drive drought. Feature importance is conditional on the inputs and target; strongly related downstream vegetation indicators can absorb predictive information. Importance is not causal attribution.

Additional concerns:

- SPI-3 has only 10 Beed and 74 Maharashtra observations in descriptive summaries, despite much larger model sample counts; alignment and imputation are unclear.
- The paper claims ground validation but does not provide a clearly auditable site/date/sample design and independent validation results.
- Kelvin-like surface temperatures are inconsistently labeled Celsius in the text.
- Generic mentions of multiple satellite platforms do not establish the actual data products used.
- The estimator, hyperparameters and temporal/spatial fold construction are insufficiently clear for independent reproduction.
- The Beed summary means for VCI, TCI and VHI do not match the equal-weight identity if evaluated on the same rows; weights and row alignment need clarification before diagnosing the cause.

Use it as a local example and a lesson in evaluation design. Do not use its headline score as our target or evidence that ML is necessary.

## 4. A prior study that changes the novelty assessment

[Kulkarni et al. (2020)](https://doi.org/10.3390/rs12132091) developed CDI_M for Marathwada using SPI-3, temperature, soil moisture and NDVI (2001–2018), cropland masking, fixed/PCA weights and detrended crop-yield comparisons. Authors include IIT Bombay researchers. Relevant publisher sections were inspected; a complete replication audit remains pending. Combining indices, masking cropland and checking yields are therefore established precedents. Our candidate contribution needs a narrower, tested improvement.

## External checks

- Beed administrative units: https://beed.gov.in/en/about-district/administrative-setup/tehsil/
- Jamkhed district reference: https://ahilyanagar.maharashtra.gov.in/en/notice/public-announcement-regarding-sale-at-dhongaon-tal-jamkhed-dist-ahilyanagar-gat-no-233-3/
- CFSR description: https://climatedataguide.ucar.edu/climate-data/climate-forecast-system-reanalysis-cfsr

These checks address current administrative geography and dataset characteristics; they do not reconstruct the authors' original input files.
