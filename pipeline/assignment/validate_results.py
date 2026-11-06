"""Verify real files, pixel accounting and source-derived NDVI; no substitute data."""
import csv,json,math
from datetime import datetime
import rasterio
from common import DATA,OUT,YEARS,BANDS,sha,write_json
from vegetation import quality_ok,ndvi_value,is_vegetation,NODATA

def main():
 cfg=json.loads((DATA/'grid.json').read_text());rows=list(csv.DictReader((OUT/'year_vs_vegetation_area.csv').open()))
 assert len(rows)==10 and [int(r['year']) for r in rows]==list(YEARS)
 h=cfg['height'];w=cfg['width'];pixel_area=cfg['pixel_area_km2']
 with rasterio.open(DATA/'processed/district_mask.tif') as src:mask=src.read(1)
 with rasterio.open(DATA/'processed/common_valid_min1.tif') as src:common=src.read(1)
 with rasterio.open(DATA/'processed/common_valid_min2.tif') as src:common2=src.read(1)
 eligible=[]
 for y in range(h):
  for x in range(w):
   assert common2[y,x]<=common[y,x]<=mask[y,x]
   if common[y,x]:eligible.append((y,x))
 sample_points=[eligible[i*(len(eligible)-1)//8] for i in range(9)]
 source_count=0;sample_checks=0
 for year,record in zip(YEARS,rows):
  with rasterio.open(DATA/f'processed/october_{year}_ndvi.tif') as src:
   ndvi=src.read(1);assert src.descriptions==('mean_selected_pixel_october_ndvi_min1',)
   assert '6371007.181' in src.crs.to_wkt()
  with rasterio.open(DATA/f'processed/october_{year}_ndvi_min2.tif') as src:ndvi2=src.read(1)
  with rasterio.open(DATA/f'processed/october_{year}_vegetation_class.tif') as src:classes=src.read(1)
  with rasterio.open(DATA/f'processed/october_{year}_observations.tif') as src:counts=src.read(1)
  with rasterio.open(DATA/f'processed/october_{year}_reflectance_7band.tif') as src:
   assert src.count==7 and src.descriptions==tuple(BANDS[:7]);assert src.shape==(h,w)
  nvalid=nveg=ncommonveg=nunknown=0
  for row in range(h):
   for col in range(w):
    if not mask[row,col]:assert classes[row,col]==254;continue
    value=float(ndvi[row,col]);count=int(counts[row,col])
    assert 0<=count<=5
    if count==0:
     assert value==NODATA and classes[row,col]==255;nunknown+=1
    else:
     assert math.isfinite(value) and -1<=value<=1;nvalid+=1
     vegetation=is_vegetation(value,.3);assert int(classes[row,col])==int(vegetation)
     if vegetation:nveg+=1
     if common[row,col] and vegetation:ncommonveg+=1
    if count>=2:assert ndvi2[row,col]==value
    else:assert ndvi2[row,col]==NODATA
    if common[row,col]:assert count>=1
    if common2[row,col]:assert count>=2
  assert nvalid==int(record['valid_pixels']) and nveg==int(record['vegetated_pixels_observed'])
  assert ncommonveg==int(record['common_vegetated_pixels'])
  assert nvalid+nunknown==int(record['district_pixels'])
  assert abs(nveg*pixel_area-float(record['vegetated_area_observed_km2']))<1e-9
  assert abs((nveg+nunknown)*pixel_area-float(record['vegetated_area_upper_bound_km2']))<1e-9
  manifest=json.loads((DATA/'raw'/str(year)/'manifest.json').read_text());sources=[]
  for rec in manifest['files']:
   p=DATA/'raw'/str(year)/(rec['asset_id'].rsplit('/',1)[-1]+'.tif')
   assert sha(p)==rec['sha256'] and rec['bands']==BANDS
   with rasterio.open(p) as src:
    assert src.shape==(h,w) and src.count==10
    for a,b in zip(list(src.transform)[:6],cfg['transform']):assert abs(a-b)<1e-7
    sources.append(src.read())
   source_count+=1
  first=datetime(year,10,1).timetuple().tm_yday;end=datetime(year,11,1).timetuple().tm_yday
  for row,col in sample_points:
   total=0.;n=0
   for im in sources:
    day=float(im[9,row,col])
    if not(first<=day<end) or not quality_ok(int(im[7,row,col]),int(im[8,row,col])):continue
    good=True
    for band in range(7):
     v=float(im[band,row,col])
     if not math.isfinite(v) or not(-100<=v<=16000):good=False
    value=ndvi_value(float(im[0,row,col]),float(im[1,row,col]))
    if good and value is not None:total+=value;n+=1
   assert n>=1 and n==int(counts[row,col])
   assert abs(total/n-float(ndvi[row,col]))<1e-12
   sample_checks+=1
 assert source_count==43
 alternatives=list(csv.DictReader((OUT/'area_all_sensitivities.csv').open()))
 assert len(alternatives)==60
 for year in YEARS:
  for minobs in (1,2):
   subset=[r for r in alternatives if int(r['year'])==year and int(r['min_observations'])==minobs]
   a={float(r['ndvi_threshold']):int(r['common_vegetated_pixels']) for r in subset}
   assert a[.2]>=a[.3]>=a[.4]
 validation={'status':'passed','source_images':source_count,'years':10,'bands_per_source':10,
  'spectral_bands_per_source':7,'primary_minimum_observations':1,'primary_threshold':.3,
  'source_sha256_checks':'passed','image_grid_alignment':'passed','native_spherical_crs':'passed',
  'pixel_class_and_area_accounting':'passed','common_footprint_nestedness':'passed',
  'threshold_nestedness':'passed','independently_reconstructed_real_pixel_years':sample_checks,
  'algorithm_unit_tests':4,'field_vegetation_ground_truth_available':False,
  'ground_reference':'Official district drought history; context only, not a pixel accuracy benchmark'}
 write_json(OUT/'validation.json',validation);print(json.dumps(validation,indent=2))
if __name__=='__main__':main()
