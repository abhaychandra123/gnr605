/* Standalone experiment. Paste into a NEW Earth Engine script.
 * Compare composite-start selection with selected-pixel dates for October.
 * Does not change the original index pipeline, QA, or adopt a new threshold.
 * MOD13A2 DayOfYear: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A2
 */
var raw = ee.ImageCollection('MODIS/061/MOD13A2');
var grid = ee.Image(raw.first()).select('NDVI').projection();
var boundary = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.eq('ADM2_CODE', 70179))
  .filter(ee.Filter.eq('ADM0_NAME', 'India'));
var firstYear = 2001;
var lastYear = 2024;

function clean(image) {
  var qa = image.select('DetailedQA');
  var value = image.select('NDVI');
  var good = image.select('SummaryQA').eq(0)
    .and(qa.rightShift(11).bitwiseAnd(7).eq(1))
    .and(qa.rightShift(8).bitwiseAnd(1).eq(0))
    .and(qa.rightShift(10).bitwiseAnd(1).eq(0))
    .and(qa.rightShift(14).bitwiseAnd(3).eq(0))
    .and(value.gte(-2000)).and(value.lte(10000));
  return ee.Image(value.multiply(0.0001).rename('ndvi').updateMask(good)
    .copyProperties(image, ['system:time_start']));
}

function collections(year) {
  // October only: DayOfYear comparisons do not cross the year boundary.
  var start = ee.Date.fromYMD(year, 10, 1);
  var end = start.advance(1, 'month');
  var firstDay = ee.Image.constant(start.getRelative('day', 'year').add(1));
  var endDay = ee.Image.constant(end.getRelative('day', 'year').add(1));
  var oldRaw = raw.filterDate(start, end);
  // Include every 16-day composite that could contain an October observation.
  var candidates = raw.filterDate(start.advance(-15, 'day'), end);
  var selected = candidates.map(function(image) {
    var doy = image.select('DayOfYear');
    return clean(image).updateMask(doy.gte(firstDay).and(doy.lt(endDay)));
  });
  return {oldRaw: oldRaw, candidates: candidates,
    old: oldRaw.map(clean), selected: selected};
}

boundary.size().evaluate(function(count, error) {
  if (error || count !== 1) { print('STOP: boundary lookup failed', error, count); return; }
  var aoi = boundary.geometry();
  function area(mask) {
    return ee.Number(ee.Image.pixelArea().rename('area').updateMask(mask).unmask(0)
      .reduceRegion({reducer: ee.Reducer.sum(), geometry: aoi, crs: grid,
        maxPixels: 1e8, tileScale: 4}).get('area', 0));
  }
  var districtArea = area(ee.Image.constant(1));
  function dates(collection) {
    return collection.aggregate_array('system:time_start').map(function(ms) {
      return ee.Date(ms).format('YYYY-MM-dd');
    });
  }
  function row(year) {
    var c = collections(year);
    var oldMask = c.old.mean().mask().unmask(0).gt(0);
    var selectedMask = c.selected.mean().mask().unmask(0).gt(0);
    return ee.Feature(null, {year: year, month: 10,
      boundary_code: 70179, boundary_source: 'FAO/GAUL/2015/level2',
      district_area_km2: districtArea.divide(1e6),
      old_source_count: c.oldRaw.size(), candidate_source_count: c.candidates.size(),
      old_source_start_dates: dates(c.oldRaw), candidate_start_dates: dates(c.candidates),
      old_valid_fraction: area(oldMask).divide(districtArea),
      pixel_date_valid_fraction: area(selectedMask).divide(districtArea),
      common_fraction: area(oldMask.and(selectedMask)).divide(districtArea),
      gained_fraction: area(selectedMask.and(oldMask.not())).divide(districtArea),
      lost_fraction: area(oldMask.and(selectedMask.not())).divide(districtArea),
      qa: 'unchanged_strict', experiment: 'October_start_date_vs_selected_pixel_date'});
  }
  var table = ee.FeatureCollection(ee.List.sequence(firstYear, lastYear).map(row));
  print('Date-audit preview, 2024', row(2024));
  Export.table.toDrive({collection: table, description: 'beed_october_pixel_date_audit_2001_2024',
    folder: 'gnr605_andure', fileFormat: 'CSV'});
  Map.centerObject(boundary, 9);
  var c = collections(2024);
  var vis = {min: 0, max: 0.8, palette: ['8c2d04', 'fec44f', 'ffffcc', '78c679', '006837']};
  Map.addLayer(c.old.mean().setDefaultProjection(grid).clip(aoi), vis,
    '2024 NDVI: composite starts in October', false);
  Map.addLayer(c.selected.mean().setDefaultProjection(grid).clip(aoi), vis,
    '2024 NDVI: selected pixel date in October');
  Map.addLayer(ee.Image().byte().paint(boundary, 1, 2),
    {palette: ['000000']}, 'Provisional boundary');
});
