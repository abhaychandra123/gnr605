/* Profile the observations added by the good-or-marginal QA experiment.
 * Diagnostic only: no production QA threshold is changed.
 * One export, rows grouped by source composite and joint quality-code values.
 * Area refers to observations in EACH composite. Never sum over dates and
 * interpret the result as unique district area.
 * https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A2
 */
var raw = ee.ImageCollection('MODIS/061/MOD13A2');
var grid = ee.Image(raw.first()).select('NDVI').projection();
var boundary = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.eq('ADM0_NAME', 'India'))
  .filter(ee.Filter.eq('ADM2_CODE', 70179));

boundary.size().evaluate(function(count, error) {
  if (error || count !== 1) { print('STOP: boundary lookup failed', error, count); return; }
  var aoi = boundary.geometry();
  var area = ee.Image.pixelArea().rename('area_m2');
  var districtArea = ee.Number(area.reduceRegion({reducer: ee.Reducer.sum(),
    geometry: aoi, crs: grid, maxPixels: 1e8, tileScale: 4}).get('area_m2'));

  function yearRows(year) {
    var start = ee.Date.fromYMD(year, 10, 1);
    var end = start.advance(1, 'month');
    var firstDay = ee.Image.constant(start.getRelative('day', 'year').add(1));
    var endDay = ee.Image.constant(end.getRelative('day', 'year').add(1));
    var candidates = raw.filterDate(start.advance(-15, 'day'), end);
    return candidates.toList(candidates.size()).map(function(element) {
      var im = ee.Image(element);
      var qa = im.select('DetailedQA');
      var summary = im.select('SummaryQA');
      var value = im.select('NDVI');
      var doy = im.select('DayOfYear');
      var common = value.gte(-2000).and(value.lte(10000))
        .and(doy.gte(firstDay)).and(doy.lt(endDay))
        .and(qa.rightShift(11).bitwiseAnd(7).eq(1))
        .and(qa.rightShift(8).bitwiseAnd(1).eq(0))
        .and(qa.rightShift(10).bitwiseAnd(1).eq(0))
        .and(qa.rightShift(14).bitwiseAnd(3).eq(0));
      // Same observations as stage 08 in audit 03. Preserve both summary classes
      // so the detailed-code distribution of good vs marginal can be compared.
      var selected = common.and(summary.eq(0).or(summary.eq(1)));
      // Exact joint code: low 8 DetailedQA bits + 256 * SummaryQA.
      var code = qa.bitwiseAnd(255).add(summary.multiply(256)).toInt().rename('code');
      var totals = area.addBands(code).updateMask(selected).reduceRegion({
        reducer: ee.Reducer.sum().group({groupField: 1, groupName: 'code'}),
        geometry: aoi, crs: grid, maxPixels: 1e8, tileScale: 4});
      var groups = ee.List(totals.get('groups', ee.List([])));
      var records = groups.map(function(element) {
        var group = ee.Dictionary(element);
        var jointCode = ee.Number(group.get('code')).toInt();
        var bits = jointCode.mod(256);
        var areaM2 = ee.Number(group.get('sum'));
        return ee.Feature(null, {year: year, month: 10,
          source_start: im.date().format('YYYY-MM-dd'),
          source_id: im.get('system:index'),
          summary_qa: jointCode.divide(256).floor(),
          modland_qa: bits.mod(4),
          vi_usefulness: bits.divide(4).floor().mod(16),
          aerosol: bits.divide(64).floor().mod(4),
          joint_quality_code: jointCode, area_km2: areaM2.divide(1e6),
          fraction_of_district: areaM2.divide(districtArea),
          district_area_km2: districtArea.divide(1e6), boundary_code: 70179,
          record_type: 'quality_group',
          experiment: 'October_good_and_marginal_detailed_quality_profile'});
      });
      // Keep a record of completely empty composites rather than silently omit.
      return ee.List(ee.Algorithms.If(groups.size().gt(0), records,
        ee.List([ee.Feature(null, {year: year, month: 10,
          source_start: im.date().format('YYYY-MM-dd'), source_id: im.get('system:index'),
          area_km2: 0, fraction_of_district: 0, boundary_code: 70179,
          district_area_km2: districtArea.divide(1e6), record_type: 'no_selected_observations',
          experiment: 'October_good_and_marginal_detailed_quality_profile'})])));
    }).flatten();
  }
  var rows = ee.List.sequence(2001, 2024).map(yearRows).flatten();
  Export.table.toDrive({collection: ee.FeatureCollection(rows),
    description: 'beed_october_detailed_quality_profile_2001_2024',
    folder: 'gnr605_andure', fileFormat: 'CSV'});
  print('Prepared one export: beed_october_detailed_quality_profile_2001_2024');
  print('Coverage has already been audited. This export identifies detailed QA categories.');
});
