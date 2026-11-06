# Ancillary study data

The national Survey of India archive and its extracted district shapefile are
kept locally and excluded from Git because they exceed GitHub file-size limits.
All shapefile components are excluded together; the incomplete archive download
is also excluded. Existing local copies are preserved.

The derived `soi2025_beed.geojson` remains tracked and is the boundary used by the
assignment. The completed assignment can be recomputed without the national files.

Original national source:
https://surveyofindia.gov.in/documents/State_District_Subdistrict_PAN%20INDIA.rar

`soi_complete.provenance.json` records the original URL, retrieval time, byte count
and SHA256. `pipeline/study/acquire_public.py` contains the acquisition code.
Re-running `pipeline/study/review_boundaries.py` requires extracting the district
shapefile and its companion files into `soi_district/` first.
