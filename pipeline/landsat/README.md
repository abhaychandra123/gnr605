# Landsat refinement of the Beed assignment

**Executed 7 November 2026:** [actual report](../../results/landsat/landsat_report.md). All 67 scenes and 573 tiles were retrieved, ten years processed, five tests passed, and 1,050 sampled pixel-year calculations independently verified. Only 79 pixels are valid in every year, so no district-wide ten-year Landsat trend is supported.

This extension retains the same district and October 2015–2024 period as the
MODIS baseline. Its status is recorded in `results/landsat/`; do not infer completion
from the presence of source code. The original assignment outputs remain unchanged.

Run from repository root with the existing `.venv`:

```sh
.venv/bin/python pipeline/landsat/download.py --workers 8
.venv/bin/python -m unittest discover -s pipeline/landsat -p 'test_*.py' -v
.venv/bin/python pipeline/landsat/analyze.py
.venv/bin/python pipeline/landsat/validate.py
.venv/bin/python pipeline/landsat/aerosol_audit.py
.venv/bin/python pipeline/landsat/transitions.py
.venv/bin/python pipeline/landsat/present.py
```

Dependencies are the existing assignment packages plus the system C++ compiler
(`clang++` on this Mac). The compiler accelerates our own scalar loops; no built-in
image-analysis/classification/regression algorithm is used by the kernel.
The projection, scanline mask, QA, reflectance conversion, NDVI, accumulation,
classification and area calculations are explicit. NumPy provides array storage;
Rasterio provides I/O; Matplotlib displays outputs. The validation-only pyproj check
compares the handwritten projection against an independent implementation.

The downloader is resumable and retains 67 Landsat 8 Level 2 October scenes in
573 native-grid tiles with ten bands: seven spectral plus three QA. All source
native grids are checked for 30 m alignment in EPSG:32643. Downloads do not
resample, calculate NDVI, select cloud-free pixels, or create monthly composites.
The district is masked locally after acquisition. Surface reflectance requires
both scale 0.0000275 and offset -0.2 before NDVI.

Large raw and processed rasters are intentionally ignored by Git. Inventory,
source checksums, request coordinates, protocol, scripts, tables and figures are
tracked. Keep downloaded files locally; another checkout can retrieve them using
an authenticated Earth Engine project (currently `weighttrack-493810`). Credentials
are never stored in the repository.

The quality rule and interpretation limits are in
[the protocol](../../results/landsat/protocol.md). Source scenes on the same date
are deduplicated per pixel, retaining the first valid sample in sorted scene-ID
order. Valid water is retained, unlike the earlier MODIS land-only screen. Sensor
comparisons therefore require attention to population and observation differences.

A finer-resolution result is not field ground truth. Independent reference labels
and spatially held-out evaluation are required before claiming ML classification
accuracy or improvement. This stage does not train a forecasting model.
