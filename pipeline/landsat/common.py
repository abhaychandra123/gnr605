"""Landsat acquisition configuration and explicit geographic coordinate equations."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/landsat';OUT=ROOT/'results/landsat'
BOUNDARY=ROOT/'data/study/ancillary/soi2025_beed.geojson'
COLLECTION='LANDSAT/LC08/C02/T1_L2';PROJECT='weighttrack-493810'
YEARS=tuple(range(2015,2025))
BANDS=[f'SR_B{i}' for i in range(1,8)]+['QA_PIXEL','QA_RADSAT','SR_QA_AEROSOL']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
 tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(path)
def utm43(lon,lat):
 """WGS84 transverse Mercator forward series, UTM zone 43 north."""
 a=6378137.;e2=0.0066943799901413165;k=.9996
 p=math.radians(lat);l=math.radians(lon-75);ep=e2/(1-e2)
 n=a/math.sqrt(1-e2*math.sin(p)**2);t=math.tan(p)**2;c=ep*math.cos(p)**2;A=math.cos(p)*l
 m=a*((1-e2/4-3*e2**2/64-5*e2**3/256)*p-(3*e2/8+3*e2**2/32+45*e2**3/1024)*math.sin(2*p)+(15*e2**2/256+45*e2**3/1024)*math.sin(4*p)-(35*e2**3/3072)*math.sin(6*p))
 x=500000+k*n*(A+(1-t+c)*A**3/6+(5-18*t+t*t+72*c-58*ep)*A**5/120)
 y=k*(m+n*math.tan(p)*(A*A/2+(5-t+9*c+4*c*c)*A**4/24+(61-58*t+t*t+600*c-330*ep)*A**6/720))
 return x,y
def rings():
 g=json.loads(BOUNDARY.read_text())['features'][0]['geometry'];assert g['type']=='Polygon'
 return [[utm43(p[0],p[1]) for p in r] for r in g['coordinates']]
