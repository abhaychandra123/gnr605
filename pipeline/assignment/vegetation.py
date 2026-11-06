"""Explicit assignment algorithms: no built-in index, mask, classification or fitting.

NumPy stores arrays only. All science operations below use scalar arithmetic,
bit operations, conditionals and loops. Rasterio is used only for image I/O.
"""
import csv,json,math
from datetime import datetime
import numpy as np
import rasterio
from rasterio.transform import Affine
from common import DATA,OUT,YEARS,BANDS,CRS,projected_rings,sha,write_json
NODATA=-9999.0

def insertion_sort(values):
 for i in range(1,len(values)):
  value=values[i];j=i-1
  while j>=0 and values[j]>value:
   values[j+1]=values[j];j-=1
  values[j+1]=value
 return values

def polygon_mask(rings,height,width,transform):
 """Even-odd scanline rasterization at pixel centres, including polygon holes."""
 step=transform[0];left=transform[2];top=transform[5]
 output=np.zeros((height,width),dtype='uint8')
 for row in range(height):
  y=top-(row+.5)*step;crossings=[]
  for ring in rings:
   for i in range(len(ring)-1):
    x1,y1=ring[i];x2,y2=ring[i+1]
    if (y1>y)!=(y2>y):crossings.append(x1+(y-y1)*(x2-x1)/(y2-y1))
  insertion_sort(crossings)
  if len(crossings)%2:raise ValueError('Odd polygon crossing count')
  k=0
  for col in range(width):
   x=left+(col+.5)*step
   while k<len(crossings) and crossings[k]<=x:k+=1
   if k%2:output[row,col]=1
 return output

def quality_ok(qa,state):
 if qa<0 or state<0:return False
 if (qa&3)!=0 or ((qa>>2)&15)!=0 or ((qa>>6)&15)!=0:return False
 if (state&3)!=0 or ((state>>3)&7)!=1:return False
 if ((state>>6)&3)==3 or ((state>>8)&3)!=0:return False
 for bit in (2,10,12,13,15):
  if ((state>>bit)&1)!=0:return False
 return True

def ndvi_value(red,nir):
 if red<0 or nir<0 or red>10000 or nir>10000 or red+nir<=0:return None
 return (nir-red)/(nir+red)

def is_vegetation(value,threshold):
 # Protect the strict > boundary from roundoff at mathematical equality.
 return value>threshold+1e-12

def linear_slope(xs,ys):
 n=0;sx=sy=sxx=sxy=0.0
 for x,y in zip(xs,ys):n+=1;sx+=x;sy+=y;sxx+=x*x;sxy+=x*y
 denominator=n*sxx-sx*sx
 if denominator==0:raise ValueError('Degenerate x values')
 slope=(n*sxy-sx*sy)/denominator
 return slope,(sy-slope*sx)/n

def median(values):
 v=insertion_sort(list(values));n=len(v)
 return v[n//2] if n%2 else (v[n//2-1]+v[n//2])/2

def statistics(years,areas):
 slope,intercept=linear_slope([y-years[0] for y in years],areas)
 decreases=increases=unchanged=0;differences=[];pair_slopes=[]
 for i in range(1,len(areas)):
  delta=areas[i]-areas[i-1];differences.append({'from_year':years[i-1],'to_year':years[i],'change_km2':delta})
  if delta<0:decreases+=1
  elif delta>0:increases+=1
  else:unchanged+=1
 for i in range(len(years)):
  for j in range(i+1,len(years)):pair_slopes.append((areas[j]-areas[i])/(years[j]-years[i]))
 loo=[]
 for leave in range(len(years)):
  x=[];y=[]
  for i in range(len(years)):
   if i!=leave:x.append(years[i]-years[0]);y.append(areas[i])
  loo.append(linear_slope(x,y)[0])
 low=high=loo[0]
 for value in loo:
  if value<low:low=value
  if value>high:high=value
 return {'ols_km2_per_year':slope,'ols_intercept_at_2015':intercept,'sen_km2_per_year':median(pair_slopes),
  'decreasing_transitions':decreases,'increasing_transitions':increases,'unchanged_transitions':unchanged,
  'decreases_every_year':decreases==len(years)-1,'end_minus_start_km2':areas[-1]-areas[0],
  'leave_one_year_out_slope_min':low,'leave_one_year_out_slope_max':high,'year_changes':differences,
  'interpretation':'Descriptive ten-year summaries, no significance or causal drought claim'}

def write_raster(path,array,cfg,descriptions,nodata):
 count=1 if len(array.shape)==2 else array.shape[0]
 with rasterio.open(path,'w',driver='GTiff',width=cfg['width'],height=cfg['height'],count=count,
     dtype=str(array.dtype),crs=CRS,transform=Affine(*cfg['transform']),nodata=nodata,compress='deflate') as dest:
  if count==1:dest.write(array,1)
  else:dest.write(array)
  for i,name in enumerate(descriptions,1):dest.set_band_description(i,name)

def process_year(year,cfg,mask):
 h,w=mask.shape;sums=np.zeros((7,h,w),dtype='float64');ndvi_sums=np.zeros((h,w),dtype='float64');counts=np.zeros((h,w),dtype='uint8')
 manifest=json.loads((DATA/'raw'/str(year)/'manifest.json').read_text())
 first=datetime(year,10,1).timetuple().tm_yday;end=datetime(year,11,1).timetuple().tm_yday
 diagnostics=[]
 for rec in manifest['files']:
  path=DATA/'raw'/str(year)/(rec['asset_id'].rsplit('/',1)[-1]+'.tif')
  assert sha(path)==rec['sha256']
  with rasterio.open(path) as src:
   assert rec['bands']==BANDS
   assert src.descriptions in (tuple(BANDS),(None,)*10);assert src.width==w and src.height==h
   for actual,expected in zip(list(src.transform)[:6],cfg['transform']):assert abs(actual-expected)<1e-7
   raw=src.read()
  reasons={'outside_october_or_fill':0,'quality_rejected':0,'reflectance_rejected':0,'accepted':0}
  for row in range(h):
   for col in range(w):
    if mask[row,col]==0:continue
    day=float(raw[9,row,col])
    if not math.isfinite(day) or day<first or day>=end:
     reasons['outside_october_or_fill']+=1;continue
    qa=int(raw[7,row,col]);state=int(raw[8,row,col])
    if not quality_ok(qa,state):reasons['quality_rejected']+=1;continue
    red=float(raw[0,row,col]);nir=float(raw[1,row,col]);value=ndvi_value(red,nir);bands=[];bad=False
    for band in range(7):
     reflectance=float(raw[band,row,col]);bands.append(reflectance)
     if not math.isfinite(reflectance) or reflectance < -100 or reflectance >16000:bad=True
    if value is None or bad:reasons['reflectance_rejected']+=1;continue
    counts[row,col]+=1;ndvi_sums[row,col]+=value
    for band in range(7):sums[band,row,col]+=bands[band]*.0001
    reasons['accepted']+=1
  diagnostics.append({'asset':rec['asset_id'],**reasons})
 monthly=np.full((h,w),NODATA,dtype='float64');reflectance=np.full((7,h,w),NODATA,dtype='float32')
 monthly_one=np.full((h,w),NODATA,dtype='float64')
 for row in range(h):
  for col in range(w):
   n=int(counts[row,col])
   if n>=1:
    monthly_one[row,col]=ndvi_sums[row,col]/n
    for band in range(7):reflectance[band,row,col]=sums[band,row,col]/n
   if n>=2:monthly[row,col]=ndvi_sums[row,col]/n
 write_raster(DATA/f'processed/october_{year}_reflectance_7band.tif',reflectance,cfg,BANDS[:7],NODATA)
 write_raster(DATA/f'processed/october_{year}_ndvi.tif',monthly_one,cfg,['mean_selected_pixel_october_ndvi_min1'],NODATA)
 write_raster(DATA/f'processed/october_{year}_ndvi_min2.tif',monthly,cfg,['mean_selected_pixel_october_ndvi_min2'],NODATA)
 write_raster(DATA/f'processed/october_{year}_observations.tif',counts,cfg,['accepted_october_composites'],None)
 write_json(OUT/f'qa/{year}.json',diagnostics)
 return monthly,monthly_one,counts

def csv_write(path,rows):
 with path.open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def main():
 cfg=json.loads((DATA/'grid.json').read_text());h=cfg['height'];w=cfg['width'];area=cfg['pixel_area_km2']
 (DATA/'processed').mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 mask=polygon_mask(projected_rings(),h,w,cfg['transform']);write_raster(DATA/'processed/district_mask.tif',mask,cfg,['district_pixel_centres'],None)
 district_count=0
 for row in range(h):
  for col in range(w):district_count+=int(mask[row,col])
 primary=[];one=[];counts_all=[]
 for year in YEARS:
  im,im_one,counts=process_year(year,cfg,mask);primary.append(im);one.append(im_one);counts_all.append(counts)
  print(f'Computed October {year} from downloaded reflectance and QA',flush=True)
 all_rows=[];summaries=[]
 for min_obs,images in [(2,primary),(1,one)]:
  common=np.zeros((h,w),dtype='uint8');common_count=0
  for row in range(h):
   for col in range(w):
    good=bool(mask[row,col])
    for image in images:
     if image[row,col]==NODATA:good=False
    if good:common[row,col]=1;common_count+=1
  if common_count==0:raise ValueError('No ten-year common valid footprint')
  write_raster(DATA/f'processed/common_valid_min{min_obs}.tif',common,cfg,[f'all10years_min{min_obs}_observations'],None)
  for threshold in [.2,.3,.4]:
   this=[]
   for year,im in zip(YEARS,images):
    valid=veg=common_veg=0;ndvi_total=0.0;common_total=0.0
    classes=np.full((h,w),254,dtype='uint8')
    for row in range(h):
     for col in range(w):
      if mask[row,col]==0:continue
      value=float(im[row,col])
      if value==NODATA:classes[row,col]=255;continue
      valid+=1;ndvi_total+=value
      vegetated=is_vegetation(value,threshold)
      classes[row,col]=1 if vegetated else 0
      if vegetated:veg+=1
      if common[row,col]:
       common_total+=value
       if vegetated:common_veg+=1
    unknown=district_count-valid
    record={'year':year,'month':10,'min_observations':min_obs,'ndvi_threshold':threshold,
     'district_pixels':district_count,'district_area_km2':district_count*area,'valid_pixels':valid,
     'valid_area_km2':valid*area,'coverage_pct':100*valid/district_count,'unknown_area_km2':unknown*area,
     'vegetated_pixels_observed':veg,'vegetated_area_observed_km2':veg*area,
     'vegetated_area_upper_bound_km2':(veg+unknown)*area,'vegetated_pct_of_valid':100*veg/valid,
     'common_pixels':common_count,'common_area_km2':common_count*area,
     'common_coverage_pct':100*common_count/district_count,'common_vegetated_pixels':common_veg,
     'common_vegetated_area_km2':common_veg*area,'common_vegetated_pct':100*common_veg/common_count,
     'mean_ndvi_valid':ndvi_total/valid,'mean_ndvi_common':common_total/common_count}
    this.append(record);all_rows.append(record)
    if min_obs==1 and threshold==.3:
     write_raster(DATA/f'processed/october_{year}_vegetation_class.tif',classes,cfg,['0_nonveg_1_veg_254_outside_255_unknown'],254)
   stat=statistics(list(YEARS),[r['common_vegetated_area_km2'] for r in this])
   summaries.append({'min_observations':min_obs,'ndvi_threshold':threshold,'common_area_km2':common_count*area,
      'common_coverage_pct':100*common_count/district_count,**stat})
 csv_write(OUT/'area_all_sensitivities.csv',all_rows)
 main_rows=[r for r in all_rows if r['min_observations']==1 and r['ndvi_threshold']==.3]
 csv_write(OUT/'year_vs_vegetation_area.csv',main_rows)
 write_json(OUT/'trend_summary.json',summaries)
 write_json(OUT/'computation_provenance.json',{'years':list(YEARS),'source':'MODIS/061/MOD09A1',
  'boundary_sha256':cfg['boundary_sha256'],'grid_sha256':sha(DATA/'grid.json'),
  'core_code_sha256':sha(__file__),'common_code_sha256':sha(DATA.parents[1]/'pipeline/assignment/common.py'),
  'source_files':[r for y in YEARS for r in json.loads((DATA/'raw'/str(y)/'manifest.json').read_text())['files']],
  'science_implementation':'explicit local scalar arithmetic and loops; no EE index/reducer/classifier or built-in trend fitting',
  'pixel_area_km2':area,'district_pixel_count':district_count})
 print(json.dumps(main_rows,indent=2),flush=True)
if __name__=='__main__':main()
