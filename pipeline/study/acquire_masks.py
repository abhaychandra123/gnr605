"""Acquire candidate masks; do not silently apply them to the primary experiment."""
import hashlib
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

import ee


def acquire(study, folder):
    folder.mkdir(parents=True, exist_ok=True)
    boundary = folder / 'gaul2015_bid.geojson'
    if not boundary.exists():
        boundary.write_text(json.dumps(study.boundary.getInfo()) + '\n')
    grid = study.grid.getInfo()
    gfsad = ee.Image('USGS/GFSAD1000_V1').select('landcover')
    worldcover = ee.ImageCollection('ESA/WorldCover/v200').first().select('Map')
    # Aggregate in two stages to avoid the interactive reprojection pixel limit.
    crop_100m = (worldcover.eq(40).clip(study.aoi.bounds().buffer(2000))
                 .reduceResolution(reducer=ee.Reducer.mean(), maxPixels=256)
                 .reproject(crs=worldcover.projection(), scale=100))
    crop_fraction = crop_100m.reduceResolution(reducer=ee.Reducer.mean(), maxPixels=1024).reproject(study.grid)
    masks = {
        'gfsad2010_crop_irrigation_classes_modis_grid': (
            gfsad, 'USGS/GFSAD1000_V1',
            'Nearest-neighbour class sampling on MODIS grid; nominal 2010, inputs 2007–2012. '
            '0 noncrop; 1 major irrigation; 2 minor irrigation; 3–5 rainfed. '
            'Not a 2020–2024 irrigation observation or crop-type map.'),
        'worldcover2021_crop_fraction_modis_grid': (
            crop_fraction, 'ESA/WorldCover/v200',
            'Area-weighted 10m cropland class 40 fraction aggregated via a 100m intermediate to MODIS grid, nominal 2021. '
            'No crop species or irrigation identification; CC-BY-4.0, ESA WorldCover consortium.')}
    manifest = {}
    for name, (image, source, limitation) in masks.items():
        path = folder / f'{name}.tif'
        if not path.exists():
            url = image.toFloat().clip(study.aoi).getDownloadURL({
                'name': name, 'region': study.aoi, 'crs': grid['crs'],
                'crs_transform': grid['transform'], 'format': 'GEO_TIFF'})
            try:
                with urllib.request.urlopen(url, timeout=180) as response:
                    raw = response.read()
            except urllib.error.HTTPError as error:
                # Print the computation error, never the signed download URL.
                raise RuntimeError(error.read().decode('utf-8')[:3000]) from None
            if raw[:4] not in (b'II*\x00', b'MM\x00*'):
                raise ValueError('Expected a GeoTIFF download')
            path.write_bytes(raw)
        manifest[name] = {'dataset': source, 'limitation': limitation,
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size,
                          'grid': grid, 'aoi': 'FAO/GAUL/2015/level2 ADM2_CODE=70179',
                          'retrieved_utc': datetime.now(timezone.utc).isoformat()}
        print(f'Acquired {name}: {path.stat().st_size} bytes', flush=True)
    (folder / 'mask_provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
