"""Configuration and scalar geometry equations; no image-analysis built-ins."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/assignment'; OUT=ROOT/'results/assignment'
BOUNDARY=ROOT/'data/study/ancillary/soi2025_beed.geojson'
YEARS=tuple(range(2015,2025)); RADIUS=6371007.181
BANDS=[f'sur_refl_b0{i}' for i in range(1,8)]+['QA','StateQA','DayOfYear']
CRS='+proj=sinu +R=6371007.181 +nadgrids=@null +units=m +no_defs'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_json(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temp.replace(path)
def projected_rings():
 g=json.loads(BOUNDARY.read_text())['features'][0]['geometry'];assert g['type']=='Polygon'
 rings=[]
 for ring in g['coordinates']:
  points=[]
  for p in ring:
   lon=p[0]*math.pi/180;lat=p[1]*math.pi/180
   points.append((RADIUS*lon*math.cos(lat),RADIUS*lat))
  rings.append(points)
 return rings

def grid_config(native):
 step=native['transform'][0];x0=native['transform'][2];y0=native['transform'][5]
 xmin=ymin=float('inf');xmax=ymax=-float('inf')
 for ring in projected_rings():
  for x,y in ring:
   if x<xmin:xmin=x
   if x>xmax:xmax=x
   if y<ymin:ymin=y
   if y>ymax:ymax=y
 col0=math.floor((xmin-x0)/step);col1=math.ceil((xmax-x0)/step)
 row0=math.floor((y0-ymax)/step);row1=math.ceil((y0-ymin)/step)
 left=x0+col0*step;top=y0-row0*step
 return {'native':native,'transform':[step,0,left,0,-step,top],
  'width':col1-col0,'height':row1-row0,'bounds':[left,y0-row1*step,x0+col1*step,top],
  'pixel_area_km2':step*step/1e6,'crs_proj4':CRS,'boundary_sha256':sha(BOUNDARY)}
