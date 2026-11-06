"""Compare the provisional GAUL polygon with official Survey of India geometry."""
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/gnr605-matplotlib')
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import rasterio
from rasterio.warp import transform_bounds

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'data/study/ancillary'
OUT = ROOT / 'results/study'
gaul = gpd.read_file(FOLDER / 'gaul2015_bid.geojson').to_crs(4326)
official = gpd.read_file(FOLDER / 'soi_district/District Boundary.shp',
                         where="STATE_UT = 'MAHARASHTRA' AND DISTRICT = 'BEED'")
assert len(official) == 1
official = official.to_crs(4326)
official.to_file(FOLDER / 'soi2025_beed.geojson', driver='GeoJSON')
if not gaul.is_valid.all() or not official.is_valid.all():
    raise ValueError('Invalid boundary geometry; inspect before comparing')
old = gaul.to_crs(6933).geometry.iloc[0]
new = official.to_crs(6933).geometry.iloc[0]
overlap = old.intersection(new)
result = {'source': 'Survey of India ABDB 2025, publication 2026-05-06',
          'official_url': 'https://surveyofindia.gov.in/pages/administrative-boundary-data-base-abdb-',
          'metadata': 'Maharashtra harmonized with ORGI in 2025; 1:50,000 source mapping',
          'official_district_lgd': str(official.DIST_LGD.iloc[0]),
          'area_method': 'EPSG:6933 equal-area polygon calculation; not raster pixel-area sum',
          'gaul2015_area_km2': old.area / 1e6, 'soi2025_area_km2': new.area / 1e6,
          'intersection_km2': overlap.area / 1e6, 'gaul_only_km2': old.difference(new).area / 1e6,
          'soi_only_km2': new.difference(old).area / 1e6,
          'intersection_over_union': overlap.area / old.union(new).area,
          'official_area_included_in_gaul_fraction': overlap.area / new.area,
          'gaul_area_outside_official_fraction': old.difference(new).area / old.area,
          'interpretation': 'Primary controlled comparison retains historical GAUL for reproducibility; '
                            'current official geography differs. Recompute on a justified historical/current '
                            'boundary before crop-impact validation.'}
(OUT / 'boundary_validation.json').write_text(json.dumps(result, indent=2) + '\n')
fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
gaul.plot(ax=ax, color='#E9C29A', edgecolor='#B66B2B', alpha=.55, linewidth=1)
official.boundary.plot(ax=ax, color='#276A88', linewidth=1.4)
ax.set_title('Provisional GAUL 2015 Bid versus Survey of India 2025 Beed\nOrange fill: GAUL; blue outline: official ABDB', fontsize=12)
ax.set_xlabel('Longitude'); ax.set_ylabel('Latitude')
ax.text(.02, .02, f'Polygon overlap / union: {result["intersection_over_union"]:.1%}\n'
        f'GAUL area outside official polygon: {result["gaul_area_outside_official_fraction"]:.1%}',
        transform=ax.transAxes, bbox={'facecolor': 'white', 'alpha': .85, 'edgecolor': 'none'})
fig.savefig(OUT / 'boundary_comparison.png', dpi=180)
plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
summaries = {}
for ax, filename, title in zip(axes,
    ['gfsad2010_crop_irrigation_classes_modis_grid.tif', 'worldcover2021_crop_fraction_modis_grid.tif'],
    ['GFSAD · nominal 2010\n0 noncrop; 1–2 irrigated; 3–5 rainfed', 'ESA WorldCover · 2021\nCropland fraction, aggregated to MODIS grid']):
    with rasterio.open(FOLDER / filename) as src:
        array = src.read(1, masked=True)
        if 'worldcover' in filename:
            artist = ax.imshow(array, cmap='YlGn', vmin=0, vmax=1)
        else:
            palette = ListedColormap(['#DADADA', '#287CBA', '#80B9D5', '#389557', '#94BE72', '#D6DCAE'])
            artist = ax.imshow(array, cmap=palette, norm=BoundaryNorm(np.arange(-.5, 6), 6))
        summaries[filename] = {'shape': list(src.shape), 'valid_pixels': int(array.count()),
                               'minimum': float(array.min()), 'maximum': float(array.max()),
                               'crs_wkt': src.crs.to_wkt(), 'transform': list(src.transform),
                               'bounds_wgs84': list(transform_bounds(src.crs, 'EPSG:4326', *src.bounds)),
                               'unweighted_pixel_mean_not_district_area_fraction': float(array.mean())}
        assert np.isfinite(array.compressed()).all()
        ax.set_title(title, fontsize=11); ax.axis('off')
        fig.colorbar(artist, ax=ax, shrink=.6, ticks=np.arange(6) if 'gfsad' in filename else None)
fig.suptitle('Acquired candidate masks · provisional GAUL footprint\nReference layers only; no crop species or annual irrigation inference', fontsize=12)
fig.savefig(OUT / 'candidate_masks.png', dpi=180)
plt.close(fig)
(OUT / 'mask_validation.json').write_text(json.dumps(summaries, indent=2) + '\n')
print(json.dumps(result, indent=2))
