"""Select well-separated Landsat sites and retrieve blinded Sentinel-2 reference chips."""
import hashlib
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import ee
import numpy as np
import rasterio
import requests
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline/landsat"))
from validate import accepted
from common import PROJECT

DATA = ROOT / "data/reference"
LS = ROOT / "data/landsat"
SIZE = 21
BANDS = ["B4", "B3", "B2", "B8", "SCL"]
TILE = "COPERNICUS/S2_SR_HARMONIZED"


def sample():
    rng = random.Random(60522)
    with rasterio.open(LS / "processed/october_2022_ndvi.tif") as src:
        ndvi = src.read(1)
        transform = src.transform
    records = []
    for group, side in [('train', -1), ('test', 1)]:
        for green in (False, True):
            n = 0
            while n < 16:
                r, c = rng.randrange(ndvi.shape[0]), rng.randrange(ndvi.shape[1])
                if side * (c - ndvi.shape[1] / 2) < 200:
                    continue
                if ndvi[r,c] == -9999 or bool(ndvi[r,c] > .3 + 1e-12) != green:
                    continue
                if any((r-s['row'])**2 + (c-s['col'])**2 < 30**2 for s in records):
                    continue
                x, y = transform * (c+.5,r+.5)
                records.append(dict(row=r,col=c,x=x,y=y,split=group))
                n += 1
    rng.shuffle(records)
    tiles = json.loads((LS/'download_manifest.json').read_text())['files']
    for i,s in enumerate(records):
        dates = set()
        for tile in tiles:
            j = tile['request']
            if j['scene'][-8:-4] != '2022':
                continue
            r,c = s['row']-j['row'], s['col']-j['col']
            if 0 <= r < j['height'] and 0 <= c < j['width']:
                with rasterio.open(ROOT/tile['path']) as src:
                    if accepted(src.read(window=Window(c,r,1,1))[:,0,0]) is not None:
                        dates.add(int(j['scene'][-2:]))
        assert dates
        s.update(id=f'P{i+1:02}',landsat_days=sorted(dates))
    return records


def init():
    ee.Initialize(project=PROJECT)


def retrieve(s):
    from rasterio.io import MemoryFile
    point = ee.Geometry.Point([s['x'],s['y']], 'EPSG:32643')
    collection = ee.ImageCollection(TILE).filterBounds(point).filterDate('2022-10-01','2022-11-01')
    ids = collection.aggregate_array('system:index').getInfo()
    def difference(asset):
        return min(abs(int(asset[6:8])-day) for day in s['landsat_days'])
    for asset in sorted(ids,key=lambda a:(difference(a),a)):
        if difference(asset)>3:
            break
        # Centre of Landsat lies on a 10m grid corner. Centre reference pixel 5m NE.
        left,top=s['x']-100,s['y']+110
        options=dict(crs='EPSG:32643',crs_transform=[10,0,left,0,-10,top],
                     dimensions=[SIZE,SIZE],format='GEO_TIFF')
        image=ee.Image(TILE+'/'+asset).select(BANDS).unmask(0).toUint16()
        response=requests.get(image.getDownloadURL(options),timeout=90)
        response.raise_for_status()
        with MemoryFile(response.content) as mem, mem.open() as src:
            a=src.read()
            assert a.shape==(5,SIZE,SIZE) and src.crs.to_epsg()==32643
            if not all(int(v) in (4,5,6) for v in a[4,8:13,8:13].flat):
                continue
        path=DATA/'chips'/(s['id']+'.tif')
        path.write_bytes(response.content)
        s.update(asset_id=TILE+'/'+asset,lag_days=difference(asset),sha256=hashlib.sha256(response.content).hexdigest())
        break
    return s


def main():
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    (DATA/'chips').mkdir(parents=True,exist_ok=True)
    sites=sample()
    with ProcessPoolExecutor(max_workers=6,initializer=init) as pool:
        sites=list(pool.map(retrieve,sites))
    (DATA/'sites.json').write_text(json.dumps(sites,indent=2)+'\n')
    for page in range(4):
        fig,axes=plt.subplots(4,8,figsize=(12,6.5))
        for k,s in enumerate(sites[16*page:16*page+16]):
            for variant,indices in enumerate(([0,1,2],[3,0,1])):
                ax=axes[k//4,2*(k%4)+variant]
                if 'asset_id' in s:
                    with rasterio.open(DATA/'chips'/(s['id']+'.tif')) as src:a=src.read()
                    disp=np.empty((SIZE,SIZE,3))
                    for r in range(SIZE):
                        for c in range(SIZE):
                            for j,b in enumerate(indices):
                                disp[r,c,j]=min(1,float(a[b,r,c])/(4500 if b==3 else 3000))**.8
                    ax.imshow(disp,interpolation='nearest')
                    # Grid centre of pixel 10,10 is +5m east/north of Landsat centre.
                    ax.add_patch(Rectangle((8,9),3,3,linewidth=.75,fill=False,edgecolor='cyan'))
                ax.set_title(s['id'] if variant==0 else 'IR',fontsize=9)
                ax.axis('off')
        fig.tight_layout(pad=.3)
        fig.savefig(DATA/f'blind_{page+1}.png',dpi=120)
        plt.close(fig)
    print('Usable reference chips',sum('asset_id' in s for s in sites),'of',len(sites))


if __name__=='__main__': main()
