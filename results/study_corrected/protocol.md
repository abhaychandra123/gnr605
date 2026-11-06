# Corrected boundary and exploratory crop-impact check

Written before examining corrected yield correlations, 6 November 2026. This is a continuation of an already inspected study, not a preregistration or blinded validation.

Use the downloaded Survey of India ABDB2025 Beed polygon (LGD523) at its full supplied resolution. Apply this fixed current boundary to all historical observations; exact historical administrative consistency is not established. Preserve all earlier GAUL outputs.

Reconstruct the four original policies for Oct-Dec 2020-2024 on official-district and WorldCover2021 cropland-fraction-weighted support. Crop fractions are aggregated from 10m through 100m to the MODIS grid; multiply area weights once, not fractional image masks. These remain mixed MODIS pixels and a fixed 2021 map, not crop-specific observations or an operational historical forecast.

For impact comparisons, evaluate screened policy C and daily-LST sensitivity D for Oct-Dec 2001-2024 on both supports. In reference years, exclude the target year from the 2001-2019 reference (18 possible years); require 15 valid reference years. After 2019 use the fixed 19-year reference. This is a retrospective index reconstruction, not prospective training-series availability. Keep VHI unclipped; preserve missing pixels and observation-count diagnostics.

Use rabi jowar, wheat and gram/chickpea as primary outcomes. Align OND year y with the official agricultural-year y-(y+1) yield. OND is an early-season window, not the complete rabi season (harvest commonly Feb-Mar); irrigation and later weather can alter yields. Do not interpret OND against already harvested kharif soybean as early warning. Harmonize soybean and cotton for future work but do not select windows by observed correlations.

Require all three OND months and at least 50% weighted VHI coverage in every month for a season mean. Report eligibility explicitly and show coverage sensitivity at 75%. Relate season mean VHI and NDVI, and December SPI-3/6, to yield residuals from a linear trend fitted ONLY on 2001-2019. Fit any simple one-indicator residual regression on those training years only; compare 2020-2024 errors against training climatology, training linear trend and previous-year yield. Report every crop/policy combination, no winner selection, no complex ML and no claims of established forecasting skill from five test years. Training association is exploratory; show test-year values and error sensitivity, not unsupported significance claims.

Sources for seasonal interpretation:
- Maharashtra Gazetteer, Beed agriculture seasons: https://www.gazetteers.maharashtra.gov.in/cultural.maharashtra.gov.in/english/gazetteer/Beed/agri_seasons.html
- Official annual APY PDFs retained in data/study/ancillary, with source URLs and SHA256 in crop_source_manifest.json.

Calendar source check: ICAR-CRIDA's district contingency plan (2011), p.5, lists rainfed gram and sorghum sowing in early October, irrigated gram/sorghum in mid-October to mid-November, and irrigated wheat in November. Thus October can precede wheat establishment; the shared OND window measures district seasonal conditions and is not a crop-specific phenology window. The historical document is retained as data/study_corrected/beed_icar_contingency_2011.pdf; it does not provide observed planting dates for each study year. URL: https://www.icar-crida.res.in/CP-2012/statewiseplans/Maharastra(Pdf)/MAU,%20Parbhani/Maharashtra%2027-Beed-3%201-12-2011.pdf
