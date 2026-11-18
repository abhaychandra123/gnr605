# Landsat refinement: fixed acquisition and analysis protocol

Scope: Beed, October 2015–2024, same official boundary and years as the preserved
MODIS baseline. This extension improves spatial detail and evaluates the original
classification; it does not assume a declining result or established ML skill.

Acquire all 67 intersecting Landsat 8 Collection 2 Tier 1 Level 2 October scenes,
without scene-cloud filtering. Retain seven reflectance bands (SR_B1–SR_B7),
QA_PIXEL, QA_RADSAT and SR_QA_AEROSOL. Source data remain unscaled uint16 with zero
fill, delivered in bounded tiles at native 30 m EPSG:32643 pixel alignment. Verify
all scene grid origins and preserve identifiers, checksums and request geometry.
No server-side vegetation index, masking, monthly reduction or classification.

Apply surface-reflectance scale 0.0000275 AND offset -0.2 before NDVI. Unlike the
MODIS multiplicative-only scale, the Landsat offset cannot be omitted from NDVI.
Reject QA_PIXEL fill, dilated cloud, cirrus, cloud, shadow and snow bits (0–5),
SR_QA_AEROSOL fill/high aerosol, and QA_RADSAT optical saturation or terrain
occlusion. Require red/NIR reflectances in [0,1] and positive sum; all seven raw
spectral DNs must be in 1..65455. Aerosol climatology/interpolation are retained
in the primary assessment and counted; they are not described as ideal retrievals.
Water is not automatically excluded: valid observed water remains eligible for
classification. This differs from the earlier MODIS land-only rule and must be
reported when comparing sensors.

Use explicit arithmetic and scalar loops for projection, polygon masking, QA,
reflectance conversion, NDVI, counting and accumulation. A compiled C++ kernel may
accelerate the handwritten loops; it uses no image-analysis or statistical library.
Array allocation, image I/O and plotting remain library operations. Geometry
projection is checked against an independent library for verification only.

For overlapping scenes on the same acquisition date, retain the first valid
observation in sorted scene-ID order, counting each pixel at most once per day.
Compute October mean NDVI across accepted acquisition dates. Require one date for
primary coverage and retain the two-date coverage diagnostic. Use the fixed
NDVI > 0.30 baseline and 0.20/0.40 sensitivities. Keep missing pixels unknown.
Report observed area bounds and the fixed intersection of pixels valid in all ten
years, without extrapolation. Pixel area is projected UTM grid-cell area (900 m²),
not a geodesic survey area. Report mean NDVI and distributions alongside area.

Landsat comparisons are cross-sensor evidence, not field ground truth. No ML
accuracy or improvement will be claimed without independent reference labels and
spatially held-out testing. Do not use NDVI-derived labels to validate NDVI or a
classifier trained to reproduce it. No forecasting is included in this acquisition
and vegetation-refinement stage.

Sources:
- https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2
- https://developers.google.com/earth-engine/apidocs/ee-image-getdownloadurl
- https://www.usgs.gov/landsat-missions/landsat-8

## Additional checks after the first coverage audit

The initial 2015 calculation retained 25.9% of district pixels, with high-aerosol
exclusion responsible for much of the otherwise eligible loss. The primary rule
was not relaxed. An added diagnostic quantifies coverage if high-aerosol flags
were admitted, keeping other checks fixed; it does not use those pixels to infer
vegetation or drought. USGS cautions against their use:
https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-reflectance

Adjacent-year shared-footprint changes and the 2015–2024 endpoint comparison were
added to distinguish local threshold crossings from changes in observation
coverage. Each pair uses a different common footprint; their net changes cannot
be added into a district-wide trend. The original all-ten-year comparison remains
reported, with its observed coverage limitation. These additions were specified
before the complete ten-year Landsat results were available.
