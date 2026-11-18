"""Resumable raw 30 m downloads. No server-side NDVI/classification/reduction."""
import argparse,json,math,time,re
from datetime import datetime,timezone
from concurrent.futures import ProcessPoolExecutor,as_completed
import ee,requests,rasterio
from common import DATA,OUT,BOUNDARY,BANDS,COLLECTION,PROJECT,YEARS,rings,sha,save

def init():
 ee.Initialize(project=PROJECT);ee.data.setDeadline(180000)

def inventory():
 path=DATA/'inventory.json'
 if path.exists():
  value=json.loads(path.read_text());assert value['boundary_sha256']==sha(BOUNDARY);return value
 init();g=json.loads(BOUNDARY.read_text())['features'][0]['geometry']
 aoi=ee.Geometry.Polygon([[[p[0],p[1]] for p in r] for r in g['coordinates']])
 c=ee.ImageCollection(COLLECTION).filterBounds(aoi).filterDate('2015-01-01','2025-01-01').filter(ee.Filter.calendarRange(10,10,'month')).sort('system:time_start')
 fields=['system:index','system:time_start','LANDSAT_PRODUCT_ID','WRS_PATH','WRS_ROW','CLOUD_COVER','CLOUD_COVER_LAND','PROCESSING_LEVEL']
 def record(im):
  p=im.select('SR_B1').projection()
  return im.set('record',im.toDictionary(fields).set('crs',p.crs()).set('transform',p.transform()).set('bounds_utm43',im.geometry().bounds(30,ee.Projection('EPSG:32643')).coordinates()))
 records=c.map(record).aggregate_array('record').getInfo()
 value={'collection':COLLECTION,'month':10,'years':list(YEARS),'boundary_sha256':sha(BOUNDARY),'retrieved_utc':datetime.now(timezone.utc).isoformat(),'scenes':records}
 save(path,value);return value

def grid(inv):
 pts=[p for ring in rings() for p in ring]
 left=15+30*math.floor((min(p[0] for p in pts)-15)/30);top=15+30*math.ceil((max(p[1] for p in pts)-15)/30)
 width=math.ceil((max(p[0] for p in pts)-left)/30);height=math.ceil((top-min(p[1] for p in pts))/30)
 for r in inv['scenes']:
  assert r['crs']=='EPSG:32643',r
  affine={key:float(value) for key,value in re.findall(r'PARAMETER\["(elt_[0-2]_[0-2])", ([^\]]+)\]',r['transform'])}
  assert affine['elt_0_0']==30 and affine['elt_1_1']==-30
  assert affine.get('elt_0_1',0)==0 and affine.get('elt_1_0',0)==0
  assert (affine['elt_0_2']-15)%30==0 and (affine['elt_1_2']-15)%30==0
 cfg={'crs':'EPSG:32643','transform':[30,0,left,0,-30,top],'width':width,'height':height,'tile_size':1200,'pixel_area_projected_km2':.0009,'boundary_sha256':sha(BOUNDARY),'note':'Fixed 30 m UTM grid; source native pixel alignment independently checked before processing. Grid-cell area, not geodesic area.'}
 path=DATA/'grid.json'
 if path.exists():assert json.loads(path.read_text())==cfg
 else:save(path,cfg)
 return cfg

def jobs(inv,cfg):
 result=[]
 for scene in inv['scenes']:
  coords=scene['bounds_utm43'][0];xmin=min(p[0] for p in coords);xmax=max(p[0] for p in coords);ymin=min(p[1] for p in coords);ymax=max(p[1] for p in coords)
  for row in range(0,cfg['height'],cfg['tile_size']):
   for col in range(0,cfg['width'],cfg['tile_size']):
    w=min(cfg['tile_size'],cfg['width']-col);h=min(cfg['tile_size'],cfg['height']-row)
    left=cfg['transform'][2]+30*col;top=cfg['transform'][5]-30*row
    if left>=xmax or left+30*w<=xmin or top<=ymin or top-30*h>=ymax:continue
    result.append({'scene':scene['system:index'],'row':row,'col':col,'width':w,'height':h,'transform':[30,0,left,0,-30,top],'crs':cfg['crs']})
 return result

def download(job):
 path=DATA/'raw'/job['scene']/f'r{job["row"]}_c{job["col"]}.tif';side=path.with_suffix('.json')
 if path.exists() and side.exists():
  rec=json.loads(side.read_text());assert rec['sha256']==sha(path);assert rec['request']==job;return rec
 path.parent.mkdir(parents=True,exist_ok=True)
 image=ee.Image(COLLECTION+'/'+job['scene']).select(BANDS).unmask(0).toUint16()
 for attempt in range(4):
  try:
   url=image.getDownloadURL({'crs':job['crs'],'crs_transform':job['transform'],'dimensions':[job['width'],job['height']],'format':'GEO_TIFF'})
   response=requests.get(url,timeout=(30,180))
   if response.status_code!=200:raise RuntimeError('HTTP '+str(response.status_code))
   if response.content[:4] not in (b'II*\0',b'MM\0*'):raise ValueError('Not a TIFF')
   tmp=path.with_suffix('.partial.tif');tmp.write_bytes(response.content)
   with rasterio.open(tmp) as src:
    assert src.count==len(BANDS) and src.shape==(job['height'],job['width'])
    assert src.crs.to_epsg()==32643
    for a,b in zip(list(src.transform)[:6],job['transform']):assert abs(a-b)<1e-6
    assert all(d=='uint16' for d in src.dtypes)
   tmp.replace(path)
   rec={'path':str(path.relative_to(DATA.parent.parent)),'request':job,'bands':BANDS,'sha256':sha(path),'bytes':path.stat().st_size,'retrieved_utc':datetime.now(timezone.utc).isoformat()}
   save(side,rec);return rec
  except Exception as err:
   if attempt==3:raise RuntimeError(f'{job["scene"]} tile {job["row"]},{job["col"]}: {type(err).__name__}') from None
   time.sleep(2**attempt)

def main():
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=6);p.add_argument('--limit',type=int);args=p.parse_args()
 inv=inventory();cfg=grid(inv);tasks=jobs(inv,cfg)
 print(f'{len(inv["scenes"])} scenes; grid {cfg["width"]}x{cfg["height"]}; {len(tasks)} tiles',flush=True)
 selected=tasks[:args.limit] if args.limit else tasks;records=[]
 with ProcessPoolExecutor(max_workers=args.workers,initializer=init) as pool:
  futures=[pool.submit(download,j) for j in selected]
  for f in as_completed(futures):
   rec=f.result();records.append(rec)
   if len(records)%20==0 or len(records)==len(selected):print(f'{len(records)}/{len(selected)} tiles verified; {sum(r["bytes"] for r in records)/1e6:.1f} MB',flush=True)
 if not args.limit:
  save(DATA/'download_manifest.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),'inventory_sha256':sha(DATA/'inventory.json'),'grid_sha256':sha(DATA/'grid.json'),'downloader_sha256':sha(__file__),'scene_count':len(inv['scenes']),'tile_count':len(records),'total_bytes':sum(r['bytes'] for r in records),'files':sorted(records,key=lambda r:r['path'])})
  print('DOWNLOAD COMPLETE',flush=True)
if __name__=='__main__':main()
