"""Source hashes/grids and independent scalar reconstruction of sampled real pixels."""
import csv,json,math,random
from pathlib import Path
from collections import defaultdict
import rasterio
from rasterio.windows import Window
from common import ROOT,DATA,OUT,YEARS,BANDS,BOUNDARY,sha,save

def accepted(values):
 for value in values[:7]:
  if not 1<=int(value)<=65455:return None
 qa=int(values[7]);sat=int(values[8]);aerosol=int(values[9])
 for bit in range(6):
  if (qa>>bit)&1:return None
 for bit in [0,1,2,3,4,5,6,11]:
  if (sat>>bit)&1:return None
 if aerosol%2==1 or (aerosol//64)%4==3:return None
 red=int(values[3])*.0000275-.2;nir=int(values[4])*.0000275-.2
 if not (0<=red<=1 and 0<=nir<=1) or red+nir<=0:return None
 return (nir-red)/(nir+red)

def main():
 cfg=json.loads((DATA/'grid.json').read_text());man=json.loads((DATA/'download_manifest.json').read_text())
 assert man['scene_count']==67 and man['tile_count']==len(man['files'])==573
 inventory=json.loads((DATA/'inventory.json').read_text())
 assert {r['request']['scene'] for r in man['files']}=={r['system:index'] for r in inventory['scenes']}
 plan=json.loads((DATA/'acquisition_plan.json').read_text())
 assert {r['path'] for r in man['files']}=={r['path'] for r in plan['files']}
 assert man['inventory_sha256']==sha(DATA/'inventory.json') and man['grid_sha256']==sha(DATA/'grid.json')
 assert cfg['boundary_sha256']==sha(BOUNDARY)
 for rec in man['files']:
  p=ROOT/rec['path'];assert sha(p)==rec['sha256'];assert rec['bands']==BANDS;j=rec['request']
  with rasterio.open(p) as src:
   assert src.count==10 and src.shape==(j['height'],j['width']) and src.crs.to_epsg()==32643
   for a,b in zip(list(src.transform)[:6],j['transform']):assert abs(a-b)<1e-6
 print('All 573 source hashes, dimensions and transforms passed',flush=True)
 with rasterio.open(DATA/'processed/district_mask.tif') as src:mask=src.read(1)
 with rasterio.open(DATA/'processed/common_valid_min1.tif') as src:common=src.read(1)
 rng=random.Random(605);points=[]
 # Fixed spatial stratification, chosen without looking at NDVI or clear status.
 for rr in range(8):
  for cc in range(16):
   candidates=[]
   for attempt in range(100):
    r=rng.randrange(rr*cfg['height']//8,(rr+1)*cfg['height']//8)
    c=rng.randrange(cc*cfg['width']//16,(cc+1)*cfg['width']//16)
    if mask[r,c]:points.append((r,c));break
 spatial_points=len(points)
 common_candidates=[]
 for r in range(cfg['height']):
  for c in range(cfg['width']):
   if common[r,c]:common_candidates.append((r,c))
 if common_candidates:
  for k in range(10):
   point=common_candidates[k*(len(common_candidates)-1)//9]
   if point not in points:points.append(point)
 checks=[]
 for year in YEARS:
  groups=defaultdict(list)
  for rec in man['files']:
   if rec['request']['scene'][-8:-4]==str(year):groups[rec['request']['scene']].append(rec)
  values=[{} for p in points]
  for scene in sorted(groups,key=lambda s:(s[-8:],s)):
   for rec in groups[scene]:
    j=rec['request'];inside=[]
    for k,(r,c) in enumerate(points):
     if j['row']<=r<j['row']+j['height'] and j['col']<=c<j['col']+j['width']:inside.append((k,r,c))
    if not inside:continue
    with rasterio.open(ROOT/rec['path']) as src:
     for k,r,c in inside:
      raw=src.read(window=Window(c-j['col'],r-j['row'],1,1))[:,0,0]
      ndvi=accepted(raw)
      if ndvi is not None and scene[-8:] not in values[k]:values[k][scene[-8:]]=ndvi
  with rasterio.open(DATA/f'processed/october_{year}_ndvi.tif') as src:out=src.read(1)
  with rasterio.open(DATA/f'processed/october_{year}_observations.tif') as src:count=src.read(1)
  with rasterio.open(DATA/f'processed/october_{year}_vegetation.tif') as src:classes=src.read(1)
  for k,(r,c) in enumerate(points):
   n=0;total=0.
   for v in values[k].values():n+=1;total+=v
   assert int(count[r,c])==n,(year,r,c,count[r,c],n)
   if n:
    expected=total/n;assert abs(float(out[r,c])-expected)<1e-12
    assert int(classes[r,c])==int(expected>.3+1e-12)
   else:assert out[r,c]==-9999 and classes[r,c]==255
   if common[r,c]:assert n>=1
   checks.append({'year':year,'row':r,'col':c,'observations':n,'common':bool(common[r,c])})
  print('Reconstructed',year,len(points),'pixel histories',flush=True)
 rows=list(csv.DictReader((OUT/'annual_vegetation.csv').open()));assert [int(r['year']) for r in rows]==list(YEARS)
 for r in rows:
  assert 0<=float(r['common_vegetation_km2'])<=float(r['common_area_km2'])<=float(r['district_grid_area_km2'])
  assert abs(float(r['valid_pixels'])*.0009+float(r['unknown_km2'])-float(r['district_grid_area_km2']))<1e-8
  assert abs(float(r['observed_vegetation_km2'])+float(r['unknown_km2'])-float(r['upper_bound_vegetation_km2']))<1e-8
 save(OUT/'validation.json',{'status':'passed','source_tiles':len(man['files']),'source_scenes':67,'source_hash_grid_checks':'passed','independent_sampled_pixel_years':len(checks),'spatial_sample_pixels':len(points),'sampling':'seed605 spatial stratification without NDVI/clear selection, supplemented with up to ten common-valid pixels to verify observed values in every year','unconditional_spatial_sample_pixels':spatial_points,'additional_common_sample_pixels':len(points)-spatial_points,'checks':checks,'field_ground_truth':False,'unit_tests':5})
 print('VALIDATION COMPLETE',flush=True)
if __name__=='__main__':main()
