"""Retrieve and inspect the actual crop weighting grid over official Beed."""
import hashlib,json,os
from datetime import datetime,timezone
import requests,ee,numpy as np,rasterio
import geopandas as gpd
from rasterio.features import geometry_mask
from rasterio.crs import CRS
os.environ.setdefault('MPLCONFIGDIR','/tmp/gnr605-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from execute_corrected import CorrectedStudy,OUT,ROOT
from execute_ee import atomic_json

def main():
 ee.Initialize(project='weighttrack-493810');ee.data.setDeadline(180000)
 s=CorrectedStudy(True);grid=s.grid.getInfo();path=OUT/'worldcover2021_crop_fraction_soi_beed.tif'
 rawpath=OUT/'worldcover2021_crop_fraction_soi_beed.ee_original.tif'
 if path.exists() and not rawpath.exists():
  path.rename(rawpath)
 if not rawpath.exists():
  url=s.fraction.toFloat().clip(s.aoi).getDownloadURL({'name':'beed_crop_fraction','region':s.aoi,
   'crs':grid['crs'],'crs_transform':grid['transform'],'format':'GEO_TIFF'})
  response=requests.get(url,timeout=180);response.raise_for_status()
  assert response.content[:4] in [b'II*\x00',b'MM\x00*'];rawpath.write_bytes(response.content)
 # EE WKT includes semi_major/minor projection parameters of 6371007.181 m,
 # but GeoTIFF/GDAL loses those overrides and reads the underlying WGS84 spheroid.
 # Encode the equivalent native sphere directly, without resampling any pixels.
 native=CRS.from_string('+proj=sinu +R=6371007.181 +nadgrids=@null +units=m +no_defs')
 with rasterio.open(rawpath) as original:
  values=original.read();profile=original.profile.copy();profile.update(crs=native)
  with rasterio.open(path,'w',**profile) as corrected:corrected.write(values)
 with rasterio.open(path) as src:
  assert np.array_equal(src.read(),values)
  assert src.crs==native
  polygon=gpd.read_file(ROOT/'data/study/ancillary/soi2025_beed.geojson').to_crs(native)
  inside=geometry_mask(polygon.geometry,out_shape=src.shape,transform=src.transform,invert=True)
  im=src.read(1,masked=True);v=im.compressed();v=v[np.isfinite(v)]
  assert np.isfinite(im.filled(np.nan)[inside]).all()
  assert v.min()>=0 and v.max()<=1
  # Pixel dimensions must match the native MODIS transform, including grid offsets.
  assert np.isclose(src.transform.a,grid['transform'][0])
  assert np.isclose(src.transform.e,grid['transform'][4])
  assert np.isclose((src.transform.c-grid['transform'][2])/src.transform.a,round((src.transform.c-grid['transform'][2])/src.transform.a))
  assert np.isclose((src.transform.f-grid['transform'][5])/src.transform.e,round((src.transform.f-grid['transform'][5])/src.transform.e))
  fig,ax=plt.subplots(figsize=(8,7),constrained_layout=True)
  plot=ax.imshow(im,cmap='YlGn',vmin=0,vmax=1);fig.colorbar(plot,ax=ax,label='Cropland fraction of MODIS pixel')
  ax.set_axis_off();ax.set_title('WorldCover 2021 cropland weighting\nSurvey of India Beed boundary; MODIS mixed pixels')
  fig.savefig(ROOT/'results/study_corrected/cropland_weighting.png',dpi=170);plt.close(fig)
  metadata={'dataset':'ESA/WorldCover/v200','class':40,'aggregation':'10m mean to 100m mean to MODIS grid',
   'boundary':'Survey of India ABDB2025 Beed LGD523','grid':grid,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
   'valid_raster_pixels':len(v),'minimum':float(v.min()),'maximum':float(v.max()),'shape':list(im.shape),
   'retrieved_utc':datetime.fromtimestamp(rawpath.stat().st_mtime,timezone.utc).isoformat(),
   'reviewed_utc':datetime.now(timezone.utc).isoformat(),
   'original_download_sha256':hashlib.sha256(rawpath.read_bytes()).hexdigest(),
   'original_download':rawpath.name,'corrected_crs':native.to_wkt(),
   'crs_correction':'Native MODIS sphere encoded explicitly; original TIFF preserved; pixel values and transform unchanged.',
   'projection_source':'https://modis.ornl.gov/files/modis.prj',
   'polygon_centres_inside_raster':int(inside.sum()),
   'limitation':'Fixed 2021 cropland fraction; no annual land-use, crop species or irrigation labels; not pure cropland MODIS retrievals.'}
 atomic_json(OUT/'crop_fraction.provenance.json',metadata);print(json.dumps(metadata,indent=2))
if __name__=='__main__':main()
