/* Standalone diagnostic, not a replacement production mask.
 * Paste into a NEW Earth Engine script. Run the prepared table export in Tasks.
 * Date selection matches 02; QA stages locate remaining NDVI exclusions.
 * The marginal-data branch is exploratory, not approved for drought inference.
 * Documentation: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A2
 */
var raw = ee.ImageCollection('MODIS/061/MOD13A2');
var grid = ee.Image(raw.first()).select('NDVI').projection();
var boundary = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.eq('ADM0_NAME', 'India'))
  .filter(ee.Filter.eq('ADM2_CODE', 70179));
var stages = ['01_date_and_value', '02_plus_land', '03_plus_SummaryQA_good',
  '04_plus_no_adjacent_cloud', '05_plus_no_mixed_cloud', '06_strict_final',
  '07_land_marginal_only', '08_good_or_marginal_all_original_flags'];

function masks(year) {
  var start = ee.Date.fromYMD(year, 10, 1);
  var end = start.advance(1, 'month');
  var firstDay = ee.Image.constant(start.getRelative('day', 'year').add(1));
  var endDay = ee.Image.constant(end.getRelative('day', 'year').add(1));
  return raw.filterDate(start.advance(-15, 'day'), end).map(function(im) {
    var value = im.select('NDVI');
    var qa = im.select('DetailedQA');
    var summary = im.select('SummaryQA');
    var doy = im.select('DayOfYear');
    var dateValue = value.gte(-2000).and(value.lte(10000))
      .and(doy.gte(firstDay)).and(doy.lt(endDay));
    var land = dateValue.and(qa.rightShift(11).bitwiseAnd(7).eq(1));
    var good = land.and(summary.eq(0));
    var noAdjacent = qa.rightShift(8).bitwiseAnd(1).eq(0);
    var noMixed = qa.rightShift(10).bitwiseAnd(1).eq(0);
    var noSnowShadow = qa.rightShift(14).bitwiseAnd(3).eq(0);
    var adjacent = good.and(noAdjacent);
    var mixed = adjacent.and(noMixed);
    var strict = mixed.and(noSnowShadow);
    var marginal = land.and(summary.eq(1));
    var expanded = land.and(summary.eq(0).or(summary.eq(1)))
      .and(noAdjacent).and(noMixed).and(noSnowShadow);
    return dateValue.addBands([land, good, adjacent, mixed, strict, marginal, expanded])
      .rename(stages).unmask(0);
  });
}

boundary.size().evaluate(function(count, error) {
  if (error || count !== 1) { print('STOP: boundary lookup failed', error, count); return; }
  var aoi = boundary.geometry();
  var area = ee.Image.pixelArea();
  var options = {reducer: ee.Reducer.sum(), geometry: aoi, crs: grid,
    maxPixels: 1e8, tileScale: 4};
  var districtArea = ee.Number(area.rename('area').reduceRegion(options).get('area'));
  function row(year) {
    var candidates = masks(year);
    // max = any accepted selected observation at this location in October.
    var union = candidates.max();
    var fractions = union.multiply(area).reduceRegion(options).map(function(key, value) {
      return ee.Number(value).divide(districtArea);
    });
    return ee.Feature(null, fractions).set({year: year, month: 10,
      boundary_code: 70179, boundary_source: 'FAO/GAUL/2015/level2',
      district_area_km2: districtArea.divide(1e6),
      candidate_source_count: candidates.size(),
      experiment: 'October_selected_pixel_date_QA_stages',
      interpretation: '01_to_06_cumulative_07_and_08_separate_branches'});
  }
  var table = ee.FeatureCollection(ee.List.sequence(2001, 2024).map(row));
  print('QA preview: October 2024', row(2024));
  print('Check: stage 06 must match pixel_date_valid_fraction in the date audit.');
  print('Stages 07/08 are separate branches. Do not add their fractions to stage 06.');
  Export.table.toDrive({collection: table,
    description: 'beed_october_pixel_date_qa_audit_2001_2024',
    folder: 'gnr605_andure', fileFormat: 'CSV'});
  Map.centerObject(boundary, 9);
  Map.addLayer(masks(2024).max().select('06_strict_final').selfMask().clip(aoi),
    {palette: ['006837']}, '2024 strict valid footprint');
  Map.addLayer(ee.Image().byte().paint(boundary, 1, 2),
    {palette: ['000000']}, 'Provisional boundary');
});
