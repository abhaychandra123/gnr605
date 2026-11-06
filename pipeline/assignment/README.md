# Beed: ten years of October vegetation-covered area

This is the completed course assignment, using October 2015–2024. Read the
[actual report](../../results/assignment/assignment_report.md) and
[year–area plot](../../results/assignment/year_vs_vegetation_area.png).
The earlier `pipeline/study/` research is preserved separately.

Inputs are 43 NASA Terra MOD09A1 Collection 6.1 GeoTIFFs with seven spectral bands
(including infrared), QA and selected-pixel dates. The fixed official Beed polygon
is `data/study/ancillary/soi2025_beed.geojson`. Downloaded inputs are already local;
analysis, validation and plotting need no network or login.

From the repository root, using the existing `.venv`:

```sh
.venv/bin/python -m pip install -r pipeline/assignment/requirements.txt
# Optional: verify/retrieve source imagery; requires existing Earth Engine login.
.venv/bin/python pipeline/assignment/download_images.py
# Recompute the actual assignment from downloaded files.
.venv/bin/python pipeline/assignment/vegetation.py
.venv/bin/python -m unittest discover -s pipeline/assignment -p 'test_*.py' -v
.venv/bin/python pipeline/assignment/validate_results.py
.venv/bin/python pipeline/assignment/present_results.py
```

The downloader uses authenticated project `weighttrack-493810`; it verifies hashes
before reusing existing source files. Never copy credentials into this repository.
Processed outputs are reproducibly replaced by the analysis commands; raw imagery
and previous exploratory results are retained.

The core uses explicit scalar arithmetic and loops for sinusoidal projection,
polygon masking, QA bit decoding, NDVI, monthly accumulation, fixed-threshold
classification, pixel counting and descriptive trends. Rasterio handles raster I/O,
NumPy stores arrays and Matplotlib displays results. Earth Engine locates and
downloads source imagery; it does not calculate the assignment's vegetation index
or areas. NASA's upstream surface-reflectance processing is part of the input product.

Primary vegetation means October mean NDVI > 0.30 with at least one accepted
observation. Thresholds 0.20/0.40 and a two-observation requirement are sensitivities.
The original min2 rule yielded only 4.2% common coverage; the documented amendment
uses min1 (65.7%) and preserves the initial run in `initial_min2_audit/`.
See [protocol and amendment](../../results/assignment/protocol.md).

Outputs:

- `data/assignment/raw/`: actual source images and asset/hash metadata.
- `data/assignment/processed/`: October seven-band composites, NDVI, observation
  counts, vegetation classes, district mask and fixed common masks.
- `results/assignment/`: annual CSVs, trend summaries, QA counts, four figures,
  report, validation and execution provenance.

Class rasters use 0 = below threshold, 1 = vegetation, 254 = outside district
(nodata), 255 = unknown. Missing observations are never silently classified as bare.
Native pixel spacing is 463.312716528 m on the MODIS sphere. Original TIFFs retain
their downloaded CRS tags; processed TIFFs explicitly encode the correct sphere.
The pixel grid and source spectral values are not resampled.

The primary fixed-footprint result has four yearly decreases and five increases:
there is no consistent annual decline. Almost all common pixels exceed 0.30, so
this threshold is insensitive to some changes in greenness. The 2024 raw-area drop
coincides with much less valid coverage. Do not extrapolate the common footprint
to the whole district or infer drought causality from the area series alone.
Official drought records support the choice of Beed; pixel-level vegetation field
truth remains unavailable, and no classification-accuracy percentage is claimed.
