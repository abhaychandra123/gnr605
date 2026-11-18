"""Compute local 30 m October vegetation metrics with explicit compiled loops."""
import argparse,ctypes,csv,importlib.util,json,subprocess,sys,time
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import Affine
from common import DATA,OUT,ROOT,YEARS,BANDS,rings,sha,save

# Reuse tested handwritten scanline and descriptive-statistics code, without
# importing assignment.common under this module's common namespace.
spec=importlib.util.spec_from_file_location('assignment_common',ROOT/'pipeline/assignment/common.py')
ac=importlib.util.module_from_spec(spec);spec.loader.exec_module(ac)
previous=sys.modules['common'];sys.modules['common']=ac
spec=importlib.util.spec_from_file_location('assignment_algorithms',ROOT/'pipeline/assignment/vegetation.py')
alg=importlib.util.module_from_spec(spec);spec.loader.exec_module(alg);sys.modules['common']=previous

def library():
 src=Path(__file__).with_name('kernel.cpp');build=src.parent/'build';build.mkdir(exist_ok=True)
 target=build/'kernel.dylib'
 if not target.exists() or target.stat().st_mtime<src.stat().st_mtime:
  subprocess.run(['clang++','-O3','-std=c++17','-dynamiclib',str(src),'-o',str(target)],check=True)
 lib=ctypes.CDLL(str(target));P=ctypes.c_void_p;I=ctypes.c_int
 lib.accumulate.argtypes=[P,I,I,I,I,I,I,P,I,P,P,P,P,P];lib.accumulate.restype=None
 lib.finish.argtypes=[I,P,P,P,P,P,P,P];lib.finish.restype=None
 lib.intersect.argtypes=[I,P,P,P,P];lib.intersect.restype=None
 lib.summarize.argtypes=[I,P,P,P,P,P,P];lib.summarize.restype=None
 lib.valid_observation.argtypes=[P,I,I];lib.valid_observation.restype=I
 return lib

def ptr(a):return a.ctypes.data_as(ctypes.c_void_p)
def write(path,a,cfg,names,nodata):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.partial.tif')
 with rasterio.open(tmp,'w',driver='GTiff',width=cfg['width'],height=cfg['height'],count=1 if a.ndim==2 else a.shape[0],dtype=str(a.dtype),crs=cfg['crs'],transform=Affine(*cfg['transform']),nodata=nodata,compress='deflate',tiled=True) as dst:
  if a.ndim==2:dst.write(a,1)
  else:dst.write(a)
  dst.descriptions=tuple(names)
 tmp.replace(path)
def read(name):
 with rasterio.open(DATA/'processed'/name) as src:return src.read(1)
def table(path,rows):
 with path.open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def main():
 args=argparse.ArgumentParser();args.add_argument('--year',type=int);opt=args.parse_args()
 cfg=json.loads((DATA/'grid.json').read_text());inv=json.loads((DATA/'inventory.json').read_text())
 h=cfg['height'];w=cfg['width'];size=h*w;lib=library()
 mask_path=DATA/'processed/district_mask.tif'
 if mask_path.exists():mask=read(mask_path.name)
 else:
  mask=alg.polygon_mask(rings(),h,w,cfg['transform']);write(mask_path,mask,cfg,['district_pixel_centre_mask'],0)
 for year in ([opt.year] if opt.year else YEARS):
  flag=OUT/f'qa/{year}.json'
  year_scenes=sorted([s for s in inv['scenes'] if s['system:index'][-8:-4]==str(year)],key=lambda s:(s['system:index'][-8:],s['system:index']))
  sources=[]
  for scene in year_scenes:
   sides=sorted((DATA/'raw'/scene['system:index']).glob('*.json'))
   if not sides:raise RuntimeError('Missing scene '+scene['system:index'])
   for side in sides:
    rec=json.loads(side.read_text());assert sha(ROOT/rec['path'])==rec['sha256'];sources.append(rec)
  manifest_path=DATA/'download_manifest.json'
  if not manifest_path.exists():manifest_path=DATA/'acquisition_plan.json'
  expected=json.loads(manifest_path.read_text())['files']
  expected=[r for r in expected if r['request']['scene'][-8:-4]==str(year)]
  assert len(sources)==len(expected),(year,len(sources),len(expected))
  assert {r['path'] for r in sources}=={r['path'] for r in expected}
  signature={'kernel':sha(Path(__file__).with_name('kernel.cpp')),'analysis':sha(__file__),'common':sha(Path(__file__).with_name('common.py')),'grid':sha(DATA/'grid.json'),'sources':{r['path']:r['sha256'] for r in sources}}
  if flag.exists() and json.loads(flag.read_text())['signature']==signature:
   print('Reusing validated year',year,flush=True);continue
  print('Processing',year,len(sources),'source tiles',flush=True)
  count=np.zeros((h,w),dtype='uint16');last=np.zeros((h,w),dtype='uint16')
  total=np.zeros((h,w),dtype='float64');reflectance=np.zeros((7,h,w),dtype='float64')
  dates=sorted({s['system:index'][-8:] for s in year_scenes});records=[]
  for scene in year_scenes:
   qa=np.zeros(10,dtype='uint64');date=dates.index(scene['system:index'][-8:])+1
   for rec in sources:
    job=rec['request']
    if job['scene']!=scene['system:index']:continue
    with rasterio.open(ROOT/rec['path']) as src:bands=src.read()
    lib.accumulate(ptr(bands),job['height'],job['width'],job['row'],job['col'],w,h,ptr(mask),date,ptr(last),ptr(count),ptr(total),ptr(reflectance),ptr(qa))
   records.append({'scene':scene['system:index'],'counts':{name:int(n) for name,n in zip(['quality_accepted_before_date_dedup','invalid_dn','cloud_snow_fill','saturation_occlusion','aerosol','invalid_red_nir','accepted_unique_date','accepted_water_flag','accepted_interpolated_aerosol','accepted_climatology_aerosol'],qa)}})
  ndvi=np.empty((h,w),dtype='float64');mean=np.empty((7,h,w),dtype='float32');classes=np.empty((h,w),dtype='uint8')
  lib.finish(size,ptr(mask),ptr(count),ptr(total),ptr(reflectance),ptr(ndvi),ptr(mean),ptr(classes))
  del reflectance,total,last
  prefix=DATA/'processed'/f'october_{year}'
  write(Path(str(prefix)+'_ndvi.tif'),ndvi,cfg,['mean_october_ndvi'], -9999)
  write(Path(str(prefix)+'_reflectance.tif'),mean,cfg,BANDS[:7],-9999)
  write(Path(str(prefix)+'_observations.tif'),count,cfg,['accepted_unique_dates'],0)
  write(Path(str(prefix)+'_vegetation.tif'),classes,cfg,['0_below_threshold_1_vegetation_254_outside_255_unknown'],254)
  save(flag,{'year':year,'signature':signature,'scenes':records,'unique_source_dates':dates})
  del ndvi,mean,classes,count
  print('Completed',year,flush=True)
 if opt.year:return
 common=np.ones((h,w),dtype='uint8');common2=np.ones((h,w),dtype='uint8')
 for year in YEARS:
  count=read(f'october_{year}_observations.tif');lib.intersect(size,ptr(mask),ptr(count),ptr(common),ptr(common2))
 write(DATA/'processed/common_valid_min1.tif',common,cfg,['valid_all_ten_years_min1'],0)
 write(DATA/'processed/common_valid_min2.tif',common2,cfg,['valid_all_ten_years_min2'],0)
 rows=[];histograms=[]
 for year in YEARS:
  count=read(f'october_{year}_observations.tif');ndvi=read(f'october_{year}_ndvi.tif')
  totals=np.zeros(12,dtype='float64');hist=np.zeros(40,dtype='uint64')
  lib.summarize(size,ptr(mask),ptr(common),ptr(count),ptr(ndvi),ptr(totals),ptr(hist));t=totals;area=.0009
  for k,threshold in enumerate([.2,.3,.4]):
   rows.append({'year':year,'threshold':threshold,'district_pixels':int(t[0]),'district_grid_area_km2':t[0]*area,'valid_pixels':int(t[1]),'valid_coverage_pct':100*t[1]/t[0],
    'valid_two_dates_pct':100*t[11]/t[0],'observed_vegetation_km2':t[5+k]*area,'unknown_km2':(t[0]-t[1])*area,'upper_bound_vegetation_km2':(t[5+k]+t[0]-t[1])*area,
    'common_pixels':int(t[2]),'common_area_km2':t[2]*area,'common_coverage_pct':100*t[2]/t[0],
    'common_vegetation_km2':t[8+k]*area,'common_vegetation_pct':100*t[8+k]/t[2] if t[2] else None,
    'mean_ndvi_valid':t[3]/t[1] if t[1] else None,'mean_ndvi_common':t[4]/t[2] if t[2] else None})
  for k,n in enumerate(hist):histograms.append({'year':year,'bin_lower':-1+.05*k,'bin_upper':-1+.05*(k+1),'common_pixel_count':int(n)})
 table(OUT/'area_sensitivities.csv',rows);table(OUT/'annual_vegetation.csv',[r for r in rows if r['threshold']==.3]);table(OUT/'ndvi_histograms.csv',histograms)
 trends=[]
 for threshold in [.2,.3,.4]:
  values=[r['common_vegetation_km2'] for r in rows if r['threshold']==threshold]
  trends.append({'threshold':threshold,**alg.statistics(list(YEARS),values)})
 save(OUT/'trend_summary.json',trends)
 save(OUT/'computation_provenance.json',{'analysis_sha256':sha(__file__),'kernel_sha256':sha(Path(__file__).with_name('kernel.cpp')),'common_sha256':sha(Path(__file__).with_name('common.py')),'reused_assignment_algorithm_sha256':sha(ROOT/'pipeline/assignment/vegetation.py'),'download_manifest_sha256':sha(DATA/'download_manifest.json'),'completed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'years':list(YEARS),'all_common_min2_pixels':int(sum(int(v) for v in common2.flat))})
 print('ANALYSIS COMPLETE',flush=True)
if __name__=='__main__':main()
