"""Download actual native-grid spectral/QA rasters; perform no vegetation analysis."""
import argparse,time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime,timezone
import ee,requests,rasterio
from common import DATA,BANDS,YEARS,grid_config,sha,write_json

PROJECT='weighttrack-493810'

def download_year(year):
 ee.Initialize(project=PROJECT);ee.data.setDeadline(180000)
 import json
 cfg=json.loads((DATA/'grid.json').read_text());folder=DATA/'raw'/str(year);folder.mkdir(parents=True,exist_ok=True)
 collection=ee.ImageCollection('MODIS/061/MOD09A1').filterDate(f'{year}-09-24',f'{year}-11-01').sort('system:time_start')
 ids=collection.aggregate_array('system:id').getInfo();assert 4<=len(ids)<=5
 region=ee.Geometry.Rectangle(cfg['bounds'],proj=ee.Projection('SR-ORG:6974'),geodesic=False)
 records=[]
 for asset in ids:
  name=asset.rsplit('/',1)[-1];path=folder/f'{name}.tif';side=path.with_suffix('.json')
  if path.exists():
   if not side.exists():raise ValueError(f'Missing provenance for existing {path}')
   rec=json.loads(side.read_text());assert sha(path)==rec['sha256'];records.append(rec);continue
  for attempt in range(3):
   try:
    # float64 preserves every source int32 QA bit and negative reflectance/fill value.
    temporary=path.with_suffix('.tmp.tif')
    if not temporary.exists():
     url=ee.Image(asset).select(BANDS).toDouble().unmask(-99999).getDownloadURL({
       'name':name,'region':region,'crs':'SR-ORG:6974','crs_transform':cfg['transform'],'format':'GEO_TIFF'})
     response=requests.get(url,timeout=180)
     if response.status_code!=200:raise RuntimeError(f'Image download HTTP {response.status_code}')
     if response.content[:4] not in (b'II*\x00',b'MM\x00*'):raise ValueError('Not a TIFF response')
     temporary.write_bytes(response.content)
    with rasterio.open(temporary) as src:
     assert src.count==10 and src.width==cfg['width'] and src.height==cfg['height']
     for actual,expected in zip(list(src.transform)[:6],cfg['transform']):assert abs(actual-expected)<1e-7
     assert src.descriptions in (tuple(BANDS),(None,)*10),src.descriptions
    temporary.replace(path)
    rec={'asset_id':asset,'composite_start':name.replace('_','-'),'year':year,'bands':BANDS,
      'sha256':sha(path),'bytes':path.stat().st_size,'retrieved_utc':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),
      'band_order_evidence':'Explicit select(BANDS) order in download request; Earth Engine omits TIFF band descriptions.',
      'format_note':'Raw values stored as exact float64; -99999 fills native masks. Native sphere is encoded explicitly in local products; original download CRS tags are preserved here.'}
    write_json(side,rec);records.append(rec);print(f'Downloaded {name}: {rec["bytes"]} bytes',flush=True);break
   except Exception as error:
    if attempt==2:raise RuntimeError(f'Download failed for {asset}: {type(error).__name__}: {str(error)[:200] if not isinstance(error,requests.RequestException) else "network request failed"}') from None
    time.sleep(2*(attempt+1))
 write_json(folder/'manifest.json',{'year':year,'files':records,'grid_sha256':sha(DATA/'grid.json')})
 return year,len(records)

def main():
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=3);args=p.parse_args()
 ee.Initialize(project=PROJECT)
 native=ee.ImageCollection('MODIS/061/MOD09A1').first().select(BANDS[0]).projection().getInfo()
 cfg=grid_config(native);path=DATA/'grid.json'
 if path.exists():
  import json
  assert json.loads(path.read_text())==cfg
 else:write_json(path,cfg)
 print(f'Grid {cfg["width"]} x {cfg["height"]}; pixel area {cfg["pixel_area_km2"]:.9f} km2',flush=True)
 with ProcessPoolExecutor(max_workers=args.workers) as pool:
  for year,count in pool.map(download_year,YEARS):print(f'Completed October sources {year}: {count} images',flush=True)
 print('All ten years of source images downloaded',flush=True)
if __name__=='__main__':main()
