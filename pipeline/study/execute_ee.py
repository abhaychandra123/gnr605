"""Execute the controlled reconstruction using official Earth Engine APIs.

Matches export_study_gee.js v0.2. Small requests are checkpointed locally;
Drive batch exports are available for computations exceeding interactive limits.
Never replaces an existing completed CSV. No credentials are logged or copied.
"""
import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import ee

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ('A_start_strict_8day', 'B_pixel_strict_8day',
             'C_pixel_screened_8day', 'D_pixel_screened_daily')
NAMES = {'comparison': 'beed_controlled_seasonal_2020_2024',
         'history': 'beed_policy_history_2001_2024',
         'rainfall': 'beed_chirps_monthly_1981_2024'}
EXPECTED = {'comparison': 120, 'history': 288, 'rainfall': 528}


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


class Study:
    def __init__(self):
        self.nraw = ee.ImageCollection('MODIS/061/MOD13A2')
        self.t8 = ee.ImageCollection('MODIS/061/MOD11A2')
        self.td = ee.ImageCollection('MODIS/061/MOD11A1')
        self.rain = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
        self.grid = self.nraw.first().select('NDVI').projection()
        self.rain_grid = self.rain.first().select('precipitation').projection()
        self.boundary = (ee.FeatureCollection('FAO/GAUL/2015/level2')
                         .filter(ee.Filter.eq('ADM0_NAME', 'India'))
                         .filter(ee.Filter.eq('ADM2_CODE', 70179)))
        if self.boundary.size().getInfo() != 1:
            raise ValueError('Boundary must contain exactly one feature')
        self.aoi = self.boundary.geometry()
        self.pixel_area = ee.Image.pixelArea()
        self.area = self.sum(ee.Image.constant(1))
        self.rain_area = self.sum(ee.Image.constant(1), self.rain_grid)

    def sum(self, mask, projection=None):
        return ee.Number(self.pixel_area.rename('area').updateMask(mask).unmask(0)
                         .reduceRegion(reducer=ee.Reducer.sum(), geometry=self.aoi,
                                       crs=self.grid if projection is None else projection,
                                       maxPixels=1e8, tileScale=4).get('area', 0))

    def means(self, image, mask):
        denominator = self.sum(mask)
        totals = (image.updateMask(mask).multiply(self.pixel_area).unmask(0)
                  .reduceRegion(reducer=ee.Reducer.sum(), geometry=self.aoi,
                                crs=self.grid, maxPixels=1e8, tileScale=4))
        return totals.map(lambda key, value: ee.Algorithms.If(
            denominator.gt(0), ee.Number(value).divide(denominator), None))

    @lru_cache(maxsize=None)
    def monthly(self, year, month, scenario):
        if month not in range(2, 13):
            raise ValueError('January selected-pixel year wrap is not implemented')
        pixel_date, marginal, daily = scenario != 0, scenario >= 2, scenario == 3
        start = ee.Date.fromYMD(year, month, 1)
        end = start.advance(1, 'month')
        first_day = ee.Image.constant(start.getRelative('day', 'year').add(1))
        end_day = ee.Image.constant(end.difference(ee.Date.fromYMD(year, 1, 1), 'day').add(1))
        ns = self.nraw.filterDate(start.advance(-15, 'day') if pixel_date else start, end)

        def ndvi(im):
            qa, summary, value = im.select('DetailedQA'), im.select('SummaryQA'), im.select('NDVI')
            accepted = summary.eq(0)
            if marginal:
                usefulness = qa.rightShift(2).bitwiseAnd(15)
                accepted = accepted.Or(summary.eq(1).And(qa.bitwiseAnd(3).eq(1))
                                       .And(usefulness.eq(1).Or(usefulness.eq(2)))
                                       .And(qa.rightShift(6).bitwiseAnd(3).eq(2)))
            mask = (accepted.And(value.gte(-2000)).And(value.lte(10000))
                    .And(qa.rightShift(11).bitwiseAnd(7).eq(1))
                    .And(qa.rightShift(8).bitwiseAnd(1).eq(0))
                    .And(qa.rightShift(10).bitwiseAnd(1).eq(0))
                    .And(qa.rightShift(14).bitwiseAnd(3).eq(0)))
            if pixel_date:
                mask = mask.And(im.select('DayOfYear').gte(first_day)).And(im.select('DayOfYear').lt(end_day))
            return value.multiply(0.0001).rename('ndvi').updateMask(mask)

        def lst(im):
            qa = im.select('QC_Day')
            mask = (qa.bitwiseAnd(3).eq(0).And(qa.rightShift(2).bitwiseAnd(3).eq(0))
                    .And(qa.rightShift(6).bitwiseAnd(3).eq(0)))
            return im.select('LST_Day_1km').multiply(0.02).rename('lst_k').updateMask(mask)

        nc = ns.map(ndvi)
        ts = (self.td if daily else self.t8).filterDate(start, end)
        tc = ts.map(lst)
        return (nc.mean().addBands(tc.mean()).addBands(nc.count().rename('ndvi_observations'))
                .addBands(tc.count().rename('lst_observations')).setDefaultProjection(self.grid)
                .set({'ndvi_source_images': ns.size(), 'lst_source_images': ts.size(),
                      'date': start.format('YYYY-MM'), 'year': year, 'month': month}))

    @lru_cache(maxsize=None)
    def reference(self, month, scenario):
        collection = ee.ImageCollection.fromImages([
            self.monthly(y, month, scenario).select(['ndvi', 'lst_k']) for y in range(2001, 2020)])
        return collection.min(), collection.max(), collection.count()

    def indices(self, year, month, scenario):
        current = self.monthly(year, month, scenario)
        lo, hi, count = self.reference(month, scenario)
        span = hi.subtract(lo)
        vci = (current.select('ndvi').subtract(lo.select('ndvi')).divide(span.select('ndvi'))
               .multiply(100).rename('vci').updateMask(span.select('ndvi').gt(0))
               .updateMask(count.select('ndvi').gte(15)))
        tci = (hi.select('lst_k').subtract(current.select('lst_k')).divide(span.select('lst_k'))
               .multiply(100).rename('tci').updateMask(span.select('lst_k').gt(0))
               .updateMask(count.select('lst_k').gte(15)))
        vhi = vci.multiply(0.5).add(tci.multiply(0.5)).rename('vhi')
        return (current.addBands(vci).addBands(tci).addBands(vhi)
                .addBands(count.rename(['ndvi_reference_years', 'lst_reference_years']))
                .addBands(span.rename(['ndvi_reference_span', 'lst_reference_span']))
                .setDefaultProjection(self.grid))

    @staticmethod
    def classes(vhi):
        return vhi.gte(10).add(vhi.gte(20)).add(vhi.gte(30)).add(vhi.gte(40)).rename('class')

    def history(self, year, month):
        rows = []
        for i, scenario in enumerate(SCENARIOS):
            current = self.monthly(year, month, i)
            nm, tm = current.select('ndvi').mask(), current.select('lst_k').mask()
            rows.append(ee.Feature(None, self.means(current.select('ndvi'), nm)).set({
                'year': year, 'month': month, 'scenario': scenario, 'date': current.get('date'),
                'ndvi_valid_fraction': self.sum(nm).divide(self.area),
                'lst_valid_fraction': self.sum(tm).divide(self.area),
                'ndvi_source_images': current.get('ndvi_source_images'),
                'lst_source_images': current.get('lst_source_images'), 'boundary_code': 70179}))
        return rows

    def comparison(self, year, month):
        images = [self.indices(year, month, i) for i in range(4)]
        shared = ee.Image.constant(1)
        for im in images:
            shared = shared.And(im.select('vhi').mask().unmask(0).gt(0))
        rows = []
        for i, im in enumerate(images):
            for support in ('own', 'all_variants_common'):
                mask = im.select('vhi').mask() if support == 'own' else shared
                area = self.sum(mask)
                class_image = self.classes(im.select('vhi'))
                props = self.means(im.select([
                    'ndvi', 'lst_k', 'vci', 'tci', 'vhi', 'ndvi_observations', 'lst_observations',
                    'ndvi_reference_years', 'lst_reference_years', 'ndvi_reference_span', 'lst_reference_span']), mask)
                f = ee.Feature(None, props).set({
                    'date': im.get('date'), 'year': year, 'month': month, 'scenario': SCENARIOS[i],
                    'support': support, 'alpha': 0.5, 'valid_area_km2': area.divide(1e6),
                    'district_area_km2': self.area.divide(1e6), 'valid_fraction': area.divide(self.area),
                    'unknown_fraction': ee.Number(1).subtract(area.divide(self.area)),
                    'baseline_start': 2001, 'baseline_end': 2019, 'min_ndvi_years': 15, 'min_lst_years': 15,
                    'boundary_code': 70179, 'boundary_source': 'FAO/GAUL/2015/level2',
                    'method': 'controlled_reconstruction_v0.2',
                    'lst_product': 'MOD11A1_061' if i == 3 else 'MOD11A2_061',
                    'lst_min_current_observations': 1, 'ndvi_source_images': im.get('ndvi_source_images'),
                    'lst_source_images': im.get('lst_source_images')})
                for c in range(5):
                    ca = self.sum(mask.And(class_image.eq(c)))
                    f = f.set(f'class_{c}_fraction_valid', ee.Algorithms.If(area.gt(0), ca.divide(area), None))
                outside = self.sum(mask.And(im.select('vhi').lt(0).Or(im.select('vhi').gt(100))))
                pair_mask = mask.And(images[0].select('vhi').mask())
                pair_area = self.sum(pair_mask)
                disagreement = self.sum(pair_mask.And(class_image.neq(self.classes(images[0].select('vhi')))))
                rows.append(f.set({
                    'vhi_outside_0_100_fraction_valid': ee.Algorithms.If(area.gt(0), outside.divide(area), None),
                    'pair_A_valid_fraction': pair_area.divide(self.area),
                    'class_disagreement_vs_A': ee.Algorithms.If(pair_area.gt(0), disagreement.divide(pair_area), None)}))
        return rows

    def rainfall(self, year, month):
        start = ee.Date.fromYMD(year, month, 1)
        end = start.advance(1, 'month')
        source = self.rain.filterDate(start, end)
        expected = end.difference(start, 'day')
        total = source.sum().updateMask(source.count().eq(ee.Image.constant(expected)))
        area = self.sum(total.mask(), self.rain_grid)
        weighted = ee.Number(total.multiply(self.pixel_area).rename('weighted').unmask(0).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=self.aoi, crs=self.rain_grid,
            maxPixels=1e8, tileScale=4).get('weighted', 0))
        return [ee.Feature(None, {
            'date': start.format('YYYY-MM'), 'year': year, 'month': month,
            'rain_mm': ee.Algorithms.If(area.gt(0), weighted.divide(area), None),
            'rain_days': source.size(), 'expected_days': expected,
            'rain_valid_fraction': area.divide(self.rain_area), 'rain_area_km2': area.divide(1e6),
            'district_area_rain_grid_km2': self.rain_area.divide(1e6), 'boundary_code': 70179,
            'boundary_source': 'FAO/GAUL/2015/level2', 'dataset': 'UCSB-CHG/CHIRPS/DAILY',
            'aggregation': 'district_area_weighted_monthly_total'})]


def periods(stage):
    years = range(1981, 2025) if stage == 'rainfall' else range(2001 if stage == 'history' else 2020, 2025)
    months = range(1, 13) if stage == 'rainfall' else (10, 11, 12)
    return [(y, m) for y in years for m in months]


def compute(rows, retries=3):
    for attempt in range(retries):
        try:
            result = ee.data.computeFeatures({'expression': ee.FeatureCollection(rows), 'pageSize': 1000})
            if result.get('nextPageToken'):
                raise ValueError('Unexpected pagination in a small checkpoint')
            return [f['properties'] for f in result['features']]
        except ee.EEException:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--stage', choices=['all', *NAMES], default='all')
    parser.add_argument('--mode', choices=['direct', 'batch', 'preflight'], default='direct')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data/study')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    ee.Initialize(project=args.project)
    ee.data.setDeadline(180000)
    assert ee.Number(1).getInfo() == 1
    study = Study()
    if args.mode == 'preflight':
        # A alone avoids computing the other three reference policies just to verify A.
        im = study.indices(2020, 10, 0)
        mask = im.select('vhi').mask()
        result = ee.Dictionary({
            'district_area_km2': study.area.divide(1e6),
            'valid_fraction': study.sum(mask).divide(study.area),
            'metrics': study.means(im.select(['ndvi', 'lst_k', 'vci', 'tci', 'vhi']), mask),
            'boundary': study.boundary.first().toDictionary()}).getInfo()
        atomic_json(args.output_dir / 'preflight.json', result)
        print(json.dumps(result, indent=2), flush=True)
        return
    stages = list(NAMES) if args.stage == 'all' else [args.stage]
    fingerprint = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for stage in stages:
        destination = args.output_dir / (NAMES[stage] + '.csv')
        if destination.exists():
            print(f'Preserving existing {destination}', flush=True)
            continue
        if args.mode == 'batch':
            manifest = args.output_dir / 'tasks' / (NAMES[stage] + '.json')
            if manifest.exists():
                task_id = json.loads(manifest.read_text())['task_id']
                print(json.dumps(ee.data.getTaskStatus(task_id)), flush=True)
                continue
            rows = [row for y, m in periods(stage) for row in getattr(study, stage)(y, m)]
            task = ee.batch.Export.table.toDrive(
                collection=ee.FeatureCollection(rows), description=NAMES[stage],
                folder='gnr605_andure', fileNamePrefix=NAMES[stage], fileFormat='CSV')
            task.start()
            atomic_json(manifest, {'task_id': task.id, 'project': args.project, 'stage': stage,
                                  'script_sha256': fingerprint, 'submitted_utc': datetime.now(timezone.utc).isoformat()})
            print(f'Submitted {stage}: {task.id}', flush=True)
            continue
        all_rows = []
        for y, m in periods(stage):
            checkpoint = args.output_dir / 'checkpoints' / stage / f'{y}-{m:02d}.json'
            if checkpoint.exists():
                saved = json.loads(checkpoint.read_text())
                if saved['script_sha256'] != fingerprint:
                    raise ValueError(f'Checkpoint implementation changed; review before reuse: {checkpoint}')
                rows = saved['rows']
            else:
                rows = compute(getattr(study, stage)(y, m))
                atomic_json(checkpoint, {'rows': rows, 'script_sha256': fingerprint,
                                        'retrieved_utc': datetime.now(timezone.utc).isoformat()})
            all_rows.extend(rows)
            print(f'{stage} {y}-{m:02d}: {len(all_rows)}/{EXPECTED[stage]} real rows', flush=True)
        if len(all_rows) != EXPECTED[stage]:
            raise ValueError(f'Unexpected row count in {stage}')
        fields = sorted(set().union(*(row.keys() for row in all_rows)))
        temporary = destination.with_suffix('.csv.tmp')
        with temporary.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(all_rows)
        temporary.replace(destination)
        print(f'Completed {destination}', flush=True)


if __name__ == '__main__':
    main()
