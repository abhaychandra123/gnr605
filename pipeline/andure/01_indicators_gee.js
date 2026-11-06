/* Paste into https://code.earthengine.google.com/ .
 * Andure-inspired reconstruction, NOT the authors' code or exact replication.
 * See README.md in this directory for assumptions and execution status.
 */
var CFG = {
  previewYear: 2020,
  previewMonth: 10,
  batch: false, // First inspect one month; true exports 60 district-month rows.
  startYear: 2020,
  endYear: 2024,
  baselineStart: 2001,
  baselineEnd: 2019,
  minBaselineYears: 15,
  alpha: 0.5,
  boundaryAsset: null, // Optional verified Beed FeatureCollection asset ID.
  exportFolder: 'gnr605_andure'
};

if (CFG.baselineEnd >= CFG.startYear) {
  throw new Error('Keep the reference period before the analysis period.');
}
var ndviRaw = ee.ImageCollection('MODIS/061/MOD13A2');
var lstRaw = ee.ImageCollection('MODIS/061/MOD11A2');
var rainRaw = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY');
var grid = ee.Image(ndviRaw.first()).select('NDVI').projection();
var rainGrid = ee.Image(rainRaw.first()).select('precipitation').projection();
var districts = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.eq('ADM0_NAME', 'India'))
  .filter(ee.Filter.eq('ADM1_NAME', 'Maharashtra'));
// Historical GAUL is an explicit provisional geometry, not a verified modern AOI.
var boundary = CFG.boundaryAsset ? ee.FeatureCollection(CFG.boundaryAsset) :
  districts.filter(ee.Filter.inList('ADM2_NAME', ['Bid', 'Beed', 'Bhir']));
print('Available district names (if matching fails)', districts.aggregate_array('ADM2_NAME'));

function cleanNDVI(image) {
  var qa = image.select('DetailedQA');
  var raw = image.select('NDVI');
  var good = image.select('SummaryQA').eq(0)
    .and(qa.rightShift(11).bitwiseAnd(7).eq(1)) // Land only; not a cropland mask.
    .and(qa.rightShift(8).bitwiseAnd(1).eq(0))
    .and(qa.rightShift(10).bitwiseAnd(1).eq(0))
    .and(qa.rightShift(14).bitwiseAnd(3).eq(0))
    .and(raw.gte(-2000)).and(raw.lte(10000));
  return ee.Image(raw.multiply(0.0001).rename('ndvi').updateMask(good)
    .copyProperties(image, ['system:time_start']));
}
function cleanLST(image) {
  var qa = image.select('QC_Day');
  var good = qa.bitwiseAnd(3).eq(0)
    .and(qa.rightShift(2).bitwiseAnd(3).eq(0))
    .and(qa.rightShift(6).bitwiseAnd(3).eq(0)); // Reported LST error <=1 K.
  return ee.Image(image.select('LST_Day_1km').multiply(0.02).rename('lst_k')
    .updateMask(good).copyProperties(image, ['system:time_start']));
}
var ndvi = ndviRaw.map(cleanNDVI);
var lst = lstRaw.map(cleanLST);

function monthly(year, month) {
  var start = ee.Date.fromYMD(year, month, 1);
  var end = start.advance(1, 'month');
  var n = ndvi.filterDate(start, end);
  var t = lst.filterDate(start, end);
  // Mean of composites whose START timestamp is in the month. Not daily means.
  return n.mean().addBands(t.mean())
    .addBands(n.count().rename('ndvi_n'))
    .addBands(t.count().rename('lst_n'))
    .setDefaultProjection(grid)
    .set({date: start.format('YYYY-MM'), month: month, year: year,
      ndvi_source_images: n.size(), lst_source_images: t.size()});
}
function indices(year, month) {
  var current = monthly(year, month);
  var reference = ee.ImageCollection.fromImages(
    ee.List.sequence(CFG.baselineStart, CFG.baselineEnd).map(function(y) {
      return monthly(y, month).select(['ndvi', 'lst_k']);
    }));
  var lo = reference.min();
  var hi = reference.max();
  var span = hi.subtract(lo);
  var count = reference.count();
  var vci = current.select('ndvi').subtract(lo.select('ndvi'))
    .divide(span.select('ndvi')).multiply(100).rename('vci')
    .updateMask(span.select('ndvi').gt(0))
    .updateMask(count.select('ndvi').gte(CFG.minBaselineYears));
  var tci = hi.select('lst_k').subtract(current.select('lst_k'))
    .divide(span.select('lst_k')).multiply(100).rename('tci')
    .updateMask(span.select('lst_k').gt(0))
    .updateMask(count.select('lst_k').gte(CFG.minBaselineYears));
  var vhi = vci.multiply(CFG.alpha).add(tci.multiply(1 - CFG.alpha)).rename('vhi');
  // Identical spatial support preserves the identity in district means.
  var joint = vhi.mask();
  // copyProperties returns an Element; restore Image methods for all callers.
  return ee.Image(current.select(['ndvi', 'lst_k']).addBands([vci, tci, vhi])
    .updateMask(joint)
    .addBands(current.select(['ndvi_n', 'lst_n']))
    .addBands(count.rename(['ndvi_baseline_n', 'lst_baseline_n']))
    .addBands(span.rename(['ndvi_baseline_span', 'lst_baseline_span']))
    .setDefaultProjection(grid).copyProperties(current));
}

function run() {
  var aoi = boundary.geometry();
  Map.centerObject(boundary, 9);
  Map.addLayer(ee.Image().byte().paint(boundary, 1, 2),
    {palette: ['000000']}, 'Provisional Beed boundary outline');
  print('Boundary metadata: verify before scientific interpretation', boundary);
  var areaImage = ee.Image.pixelArea().rename('area');
  function sumArea(mask) {
    return ee.Number(areaImage.updateMask(mask).unmask(0).reduceRegion({
      reducer: ee.Reducer.sum(), geometry: aoi, crs: grid,
      maxPixels: 1e8, tileScale: 4
    }).get('area', 0));
  }
  var districtArea = sumArea(ee.Image.constant(1));
  function rainMean(start, end) {
    var source = rainRaw.filterDate(start, end);
    var days = end.difference(start, 'day');
    // Missing daily inputs mask the total, rather than creating a dry anomaly.
    var total = source.sum().updateMask(source.count().eq(days));
    var weights = ee.Image.pixelArea().updateMask(total.mask());
    var sums = total.multiply(weights).rename('rain_area')
      .addBands(weights.rename('valid_area')).unmask(0).reduceRegion({
        reducer: ee.Reducer.sum(), geometry: aoi, crs: rainGrid,
        maxPixels: 1e8, tileScale: 4
      });
    var valid = ee.Number(sums.get('valid_area', 0));
    var result = ee.Algorithms.If(valid.gt(0),
      ee.Number(sums.get('rain_area', 0)).divide(valid), null);
    return {value: result, images: source.size(), expected: days};
  }
  function row(year, month) {
    var im = indices(year, month);
    var bands = ['ndvi', 'lst_k', 'vci', 'tci', 'vhi'];
    var validArea = sumArea(im.select('vhi').mask());
    var totals = im.select(bands).multiply(areaImage).unmask(0).reduceRegion({
      reducer: ee.Reducer.sum(), geometry: aoi, crs: grid,
      maxPixels: 1e8, tileScale: 4
    });
    var means = ee.Dictionary.fromLists(bands, bands.map(function(band) {
      return ee.Algorithms.If(validArea.gt(0),
        ee.Number(totals.get(band, 0)).divide(validArea), null);
    }));
    var start = ee.Date.fromYMD(year, month, 1);
    var end = start.advance(1, 'month');
    var rain = rainMean(start, end);
    var rain3 = rainMean(start.advance(-2, 'month'), end);
    return ee.Feature(null, means).set({
      date: start.format('YYYY-MM'), alpha: CFG.alpha,
      valid_area_km2: validArea.divide(1e6),
      district_area_km2: districtArea.divide(1e6),
      valid_fraction: validArea.divide(districtArea),
      rain_mm: rain.value, rain_3month_mm: rain3.value,
      rain_days: rain.images, rain_expected_days: rain.expected,
      rain_3month_days: rain3.images, rain_3month_expected_days: rain3.expected,
      ndvi_source_images: im.get('ndvi_source_images'),
      lst_source_images: im.get('lst_source_images'),
      baseline_start: CFG.baselineStart, baseline_end: CFG.baselineEnd,
      min_baseline_years: CFG.minBaselineYears,
      boundary_source: CFG.boundaryAsset || 'FAO/GAUL/2015/level2',
      boundary_name: boundary.first().get('ADM2_NAME'),
      boundary_code: boundary.first().get('ADM2_CODE'),
      method: 'andure_reconstruction_v0.1', land_mask: 'MODIS_QA_land_only'
    });
  }
  var preview = indices(CFG.previewYear, CFG.previewMonth).clip(aoi);
  var currentPreview = monthly(CFG.previewYear, CFG.previewMonth).clip(aoi);
  var colors = ['8c2d04', 'fec44f', 'ffffcc', '78c679', '006837'];
  Map.addLayer(preview.select('ndvi'), {min: 0, max: 0.8, palette: colors}, 'NDVI on VHI-valid pixels', false);
  Map.addLayer(preview.select('vhi'), {min: 0, max: 100, palette: colors}, 'VHI on valid pixels');
  Map.addLayer(currentPreview.select('ndvi'), {min: 0, max: 0.8, palette: colors},
    'NDVI before LST and reference requirements', false);
  Map.addLayer(currentPreview.select('lst_k'), {min: 290, max: 320,
    palette: ['2166ac', 'f7f7f7', 'b2182b']}, 'LST before NDVI and reference requirements', false);
  Map.addLayer(preview.select('ndvi_n'), {min: 0, max: 3}, 'Valid NDVI composites', false);
  Map.addLayer(preview.select('lst_n'), {min: 0, max: 4}, 'Valid LST composites', false);
  var referenceYears = CFG.baselineEnd - CFG.baselineStart + 1;
  Map.addLayer(preview.select('ndvi_baseline_n').unmask(0).clip(aoi),
    {min: 0, max: referenceYears}, 'NDVI reference years', false);
  Map.addLayer(preview.select('lst_baseline_n').unmask(0).clip(aoi),
    {min: 0, max: referenceYears}, 'LST reference years', false);

  // Diagnose coverage without altering QA, reference thresholds or index values.
  // These zero-filled BINARY masks are only for counting area, never index data.
  var nCurrent = currentPreview.select('ndvi').mask().unmask(0).gt(0);
  var tCurrent = currentPreview.select('lst_k').mask().unmask(0).gt(0);
  var nReference = preview.select('ndvi_baseline_n').unmask(0).gte(CFG.minBaselineYears);
  var tReference = preview.select('lst_baseline_n').unmask(0).gte(CFG.minBaselineYears);
  var rangesOK = preview.select('ndvi_baseline_span').unmask(0).gt(0)
    .and(preview.select('lst_baseline_span').unmask(0).gt(0));
  var bothCurrent = nCurrent.and(tCurrent);
  var withNReference = bothCurrent.and(nReference);
  var withBothReferences = withNReference.and(tReference);
  var gates = [
    ['01_current_NDVI', nCurrent],
    ['02_current_LST', tCurrent],
    ['03_current_both', bothCurrent],
    ['04_current_both_plus_NDVI_reference', withNReference],
    ['05_current_both_plus_both_references', withBothReferences],
    ['06_above_plus_nonzero_ranges', withBothReferences.and(rangesOK)],
    ['07_actual_VHI', preview.select('vhi').mask()],
    ['08_NDVI_reference_alone', nReference],
    ['09_LST_reference_alone', tReference]
  ];
  var diagnostics = ee.FeatureCollection(gates.map(function(gate) {
    var area = sumArea(gate[1]);
    return ee.Feature(null, {stage: gate[0], area_km2: area.divide(1e6),
      fraction_of_district: area.divide(districtArea),
      date: ee.Date.fromYMD(CFG.previewYear, CFG.previewMonth, 1).format('YYYY-MM'),
      min_baseline_years: CFG.minBaselineYears});
  }));
  print('Coverage diagnostics: compare fractions; stages 03-06 are cumulative', diagnostics);
  print('Coverage fractions by stage', ee.Dictionary.fromLists(
    diagnostics.aggregate_array('stage'), diagnostics.aggregate_array('fraction_of_district')));
  Export.table.toDrive({collection: diagnostics, description: 'beed_preview_coverage_diagnostics',
    folder: CFG.exportFolder, fileFormat: 'CSV'});
  print('Preview summary', row(CFG.previewYear, CFG.previewMonth));
  var rows = CFG.batch ? ee.List.sequence(CFG.startYear, CFG.endYear).map(function(y) {
    return ee.List.sequence(1, 12).map(function(m) { return row(y, m); });
  }).flatten() : ee.List([row(CFG.previewYear, CFG.previewMonth)]);
  Export.table.toDrive({collection: ee.FeatureCollection(rows),
    description: CFG.batch ? 'beed_monthly_2020_2024' : 'beed_preview_2020_10',
    folder: CFG.exportFolder, fileFormat: 'CSV'});
}
// Fail clearly on missing/ambiguous AOI; do not silently select the first match.
boundary.size().evaluate(function(count, error) {
  if (error) { print('Boundary lookup failed', error); return; }
  if (count !== 1) { print('STOP: expected one boundary; found', count); return; }
  run();
});
