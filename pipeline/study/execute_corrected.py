"""Official-boundary rerun. Original execution and outputs remain untouched."""
import argparse,csv,hashlib,json
from datetime import datetime,timezone
from functools import lru_cache
from pathlib import Path
import ee
from execute_ee import Study,SCENARIOS,ROOT,compute,atomic_json

OUT=ROOT/'data/study_corrected'
GEO=ROOT/'data/study/ancillary/soi2025_beed.geojson'

class CorrectedStudy(Study):
    def __init__(self, crop=False):
        self.nraw=ee.ImageCollection('MODIS/061/MOD13A2')
        self.t8=ee.ImageCollection('MODIS/061/MOD11A2')
        self.td=ee.ImageCollection('MODIS/061/MOD11A1')
        self.rain=ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
        self.grid=self.nraw.first().select('NDVI').projection()
        self.rain_grid=self.rain.first().select('precipitation').projection()
        geometry=json.loads(GEO.read_text())['features'][0]['geometry']
        assert geometry['type']=='Polygon'
        geometry['coordinates']=[[[p[0],p[1]] for p in ring] for ring in geometry['coordinates']]
        self.aoi=ee.Geometry(geometry,geodesic=False)
        self.weighting='worldcover2021_crop_fraction' if crop else 'all_land'
        self.crop=crop
        self.pixel_area=ee.Image.pixelArea()
        self.full_area=self.sum(ee.Image.constant(1))
        if crop:
            wc=ee.ImageCollection('ESA/WorldCover/v200').first().select('Map')
            self.fraction=(wc.eq(40).clip(self.aoi.bounds().buffer(2000))
                .reduceResolution(ee.Reducer.mean(),maxPixels=256)
                .reproject(crs=wc.projection(),scale=100)
                .reduceResolution(ee.Reducer.mean(),maxPixels=1024).reproject(self.grid))
            self.pixel_area=self.pixel_area.multiply(self.fraction.unmask(0))
        self.area=self.sum(ee.Image.constant(1))
        self.rain_area=self.sum(ee.Image.constant(1),self.rain_grid)

    def label(self,f):
        return f.set({'boundary_code':523,'boundary_source':'Survey_of_India_ABDB2025',
            'boundary_sha256':hashlib.sha256(GEO.read_bytes()).hexdigest(),
            'spatial_weighting':self.weighting,'method':'official_boundary_corrected_v1',
            'full_district_modis_area_km2':self.full_area.divide(1e6),
            'weighted_support_area_km2':self.area.divide(1e6)})

    @lru_cache(maxsize=None)
    def reference_excluding(self,month,scenario,excluded):
        coll=ee.ImageCollection.fromImages([self.monthly(y,month,scenario).select(['ndvi','lst_k'])
            for y in range(2001,2020) if y!=excluded])
        return coll.min(),coll.max(),coll.count()

    def retrospective_indices(self,year,month,scenario):
        cur=self.monthly(year,month,scenario)
        lo,hi,count=self.reference_excluding(month,scenario,year if year<=2019 else None)
        span=hi.subtract(lo)
        vci=(cur.select('ndvi').subtract(lo.select('ndvi')).divide(span.select('ndvi')).multiply(100)
            .rename('vci').updateMask(span.select('ndvi').gt(0).And(count.select('ndvi').gte(15))))
        tci=(hi.select('lst_k').subtract(cur.select('lst_k')).divide(span.select('lst_k')).multiply(100)
            .rename('tci').updateMask(span.select('lst_k').gt(0).And(count.select('lst_k').gte(15))))
        return cur.addBands(vci).addBands(tci).addBands(vci.add(tci).multiply(.5).rename('vhi'))

    def impacts(self,year,month):
        rows=[]
        for i in (2,3):
            im=self.retrospective_indices(year,month,i)
            mask=im.select('vhi').mask()
            area=self.sum(mask)
            rows.append(self.label(ee.Feature(None,self.means(im,mask)).set({
                'year':year,'month':month,'date':f'{year}-{month:02d}','scenario':SCENARIOS[i],
                'valid_fraction':area.divide(self.area),'valid_area_km2':area.divide(1e6),
                'reference_mode':'leave_target_year_out' if year<=2019 else 'fixed_2001_2019',
                'min_reference_years':15,'reference_end':2019,'reference_start':2001,
                'vhi_outside_0_100_fraction_valid':self.sum(mask.And(im.select('vhi').lt(0).Or(im.select('vhi').gt(100)))).divide(area)
            })))
        return rows

    def comparison(self,year,month):
        # In inherited output, district_area_km2 is weighted support area for crop rows;
        # explicit full and weighted areas above remove ambiguity.
        return [self.label(f) for f in super().comparison(year,month)]

    def rainfall(self,year,month):
        if self.crop:raise ValueError('Rainfall must use native-grid district area, not MODIS crop weights')
        return [self.label(f) for f in super().rainfall(year,month)]


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['comparison','impacts','rainfall','all'],default='all')
    p.add_argument('--project',default='weighttrack-493810');a=p.parse_args()
    ee.Initialize(project=a.project);ee.data.setDeadline(180000)
    assert ee.Number(1).getInfo()==1
    OUT.mkdir(exist_ok=True)
    files=[Path(__file__),ROOT/'pipeline/study/execute_ee.py',GEO]
    signature=hashlib.sha256(b''.join(x.read_bytes() for x in files)).hexdigest()
    land=CorrectedStudy();crop=CorrectedStudy(True)
    for stage in (['comparison','impacts','rainfall'] if a.stage=='all' else [a.stage]):
        years=range(1981,2025) if stage=='rainfall' else range(2020 if stage=='comparison' else 2001,2025)
        expected={'comparison':240,'impacts':288,'rainfall':528}[stage]
        rows=[]
        for year in years:
            # Month checkpoints keep graphs small; rainfall groups one year.
            groups=[list(range(1,13))] if stage=='rainfall' else [[m] for m in (10,11,12)]
            for months in groups:
                label=str(year) if stage=='rainfall' else f'{year}-{months[0]:02d}'
                dest=OUT/'checkpoints'/stage/f'{label}.json'
                if dest.exists():
                    saved=json.loads(dest.read_text())
                    if saved['implementation_sha256']!=signature:raise ValueError(f'Stale checkpoint {dest}')
                    part=saved['rows']
                else:
                    part=compute([f for m in months for s in ([land] if stage=='rainfall' else [land,crop])
                        for f in getattr(s,stage)(year,m)])
                    atomic_json(dest,{'rows':part,'implementation_sha256':signature,
                        'retrieved_utc':datetime.now(timezone.utc).isoformat()})
                rows.extend(part)
                print(f'{stage} {label}: {len(rows)}/{expected} real rows',flush=True)
        assert len(rows)==expected
        target=OUT/f'{stage}.csv'
        fields=sorted(set().union(*(r.keys() for r in rows)))
        temp=target.with_suffix('.csv.tmp')
        with temp.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        if target.exists() and target.read_bytes()!=temp.read_bytes():raise ValueError('Refusing to overwrite changed completed CSV')
        temp.replace(target)
        atomic_json(OUT/f'{stage}.provenance.json',{'rows':len(rows),'implementation_sha256':signature,
            'csv_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'project':a.project,
            'sources':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files}})
        for x in files[:2]:
            snap=OUT/'source_snapshots'/x.name;snap.parent.mkdir(exist_ok=True)
            if snap.exists() and snap.read_bytes()!=x.read_bytes():raise ValueError('Snapshot changed')
            snap.write_bytes(x.read_bytes())

if __name__=='__main__':main()
