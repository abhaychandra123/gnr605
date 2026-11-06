/* Beed controlled reconstruction, v0.2. Paste this entire file into GEE.
 * Creates three CSV Tasks in one run: policy comparisons, historical NDVI,
 * and monthly CHIRPS. No export is automatically submitted by this script.
 * Implementation choices and unresolved validation are in README.md.
 * Original script 01 is preserved. No architecture or predictive score is claimed.
 */
var CFG = {baselineStart: 2001, baselineEnd: 2019, minYears: 15,
  startYear: 2020, endYear: 2024, months: [10, 11, 12], alpha: 0.5,
  rainfallStart: 1981, rainfallEnd: 2024,
  exportFolder: 'gnr605_andure', boundaryAsset: null};
var scenarios = [
  {id: 'A_start_strict_8day', pixelDate: false, marginal: false, daily: false},
  {id: 'B_pixel_strict_8day', pixelDate: true, marginal: false, daily: false},
  {id: 'C_pixel_screened_8day', pixelDate: true, marginal: true, daily: false},
  {id: 'D_pixel_screened_daily', pixelDate: true, marginal: true, daily: true}
];
if (CFG.baselineEnd >= CFG.startYear) throw new Error('Evaluation must follow reference period.');
if (CFG.minYears > CFG.baselineEnd - CFG.baselineStart + 1) throw new Error('Invalid reference count.');
CFG.months.forEach(function(m) {
  if (m < 2 || m > 12) throw new Error('Pixel DayOfYear selection here excludes January/year wrap.');
});
var nRaw = ee.ImageCollection('MODIS/061/MOD13A2');
var t8 = ee.ImageCollection('MODIS/061/MOD11A2');
var td = ee.ImageCollection('MODIS/061/MOD11A1');
var rain = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY');
var grid = ee.Image(nRaw.first()).select('NDVI').projection();
var rainGrid = ee.Image(rain.first()).select('precipitation').projection();
var boundary = CFG.boundaryAsset ? ee.FeatureCollection(CFG.boundaryAsset) :
  ee.FeatureCollection('FAO/GAUL/2015/level2')
    .filter(ee.Filter.eq('ADM0_NAME', 'India')).filter(ee.Filter.eq('ADM2_CODE', 70179));
var monthlyCache = {}, referenceCache = {};

function monthly(year, month, scenario) {
  var key = scenario.id + '_' + year + '_' + month;
  if (monthlyCache[key]) return monthlyCache[key];
  var start = ee.Date.fromYMD(year, month, 1), end = start.advance(1, 'month');
  var firstDay = ee.Image.constant(start.getRelative('day', 'year').add(1));
  // December end belongs to next year; use days in year + 1, not January DOY 1.
  var endDay = ee.Image.constant(end.difference(ee.Date.fromYMD(year, 1, 1), 'day').add(1));
  var ns = nRaw.filterDate(scenario.pixelDate ? start.advance(-15, 'day') : start, end);
  var nc = ns.map(function(im) {
    var qa = im.select('DetailedQA'), summary = im.select('SummaryQA'), value = im.select('NDVI');
    var accepted = summary.eq(0);
    if (scenario.marginal) {
      var usefulness = qa.rightShift(2).bitwiseAnd(15);
      accepted = accepted.or(summary.eq(1).and(qa.bitwiseAnd(3).eq(1))
        .and(usefulness.eq(1).or(usefulness.eq(2)))
        .and(qa.rightShift(6).bitwiseAnd(3).eq(2)));
    }
    var mask = accepted.and(value.gte(-2000)).and(value.lte(10000))
      .and(qa.rightShift(11).bitwiseAnd(7).eq(1))
      .and(qa.rightShift(8).bitwiseAnd(1).eq(0))
      .and(qa.rightShift(10).bitwiseAnd(1).eq(0))
      .and(qa.rightShift(14).bitwiseAnd(3).eq(0));
    if (scenario.pixelDate) mask = mask.and(im.select('DayOfYear').gte(firstDay))
      .and(im.select('DayOfYear').lt(endDay));
    return value.multiply(0.0001).rename('ndvi').updateMask(mask);
  });
  var ts = (scenario.daily ? td : t8).filterDate(start, end);
  var tc = ts.map(function(im) {
    var qa = im.select('QC_Day');
    var mask = qa.bitwiseAnd(3).eq(0).and(qa.rightShift(2).bitwiseAnd(3).eq(0))
      .and(qa.rightShift(6).bitwiseAnd(3).eq(0));
    return im.select('LST_Day_1km').multiply(0.02).rename('lst_k').updateMask(mask);
  });
  var result = nc.mean().addBands(tc.mean())
    .addBands(nc.count().rename('ndvi_observations'))
    .addBands(tc.count().rename('lst_observations')).setDefaultProjection(grid)
    .set({ndvi_source_images: ns.size(), lst_source_images: ts.size(),
      date: start.format('YYYY-MM'), year: year, month: month});
  monthlyCache[key] = result;
  return result;
}

function reference(month, scenario) {
  var key = scenario.id + '_' + month;
  if (referenceCache[key]) return referenceCache[key];
  var images = [];
  for (var y = CFG.baselineStart; y <= CFG.baselineEnd; y++) {
    images.push(monthly(y, month, scenario).select(['ndvi', 'lst_k']));
  }
  var collection = ee.ImageCollection.fromImages(images);
  var result = {lo: collection.min(), hi: collection.max(), count: collection.count()};
  referenceCache[key] = result;
  return result;
}

function indices(year, month, scenario) {
  var current = monthly(year, month, scenario), ref = reference(month, scenario);
  var span = ref.hi.subtract(ref.lo), threshold = ee.Image.constant(CFG.minYears);
  var vci = current.select('ndvi').subtract(ref.lo.select('ndvi'))
    .divide(span.select('ndvi')).multiply(100).rename('vci')
    .updateMask(span.select('ndvi').gt(0)).updateMask(ref.count.select('ndvi').gte(threshold));
  var tci = ref.hi.select('lst_k').subtract(current.select('lst_k'))
    .divide(span.select('lst_k')).multiply(100).rename('tci')
    .updateMask(span.select('lst_k').gt(0)).updateMask(ref.count.select('lst_k').gte(threshold));
  var vhi = vci.multiply(CFG.alpha).add(tci.multiply(1 - CFG.alpha)).rename('vhi');
  return current.addBands([vci, tci, vhi])
    .addBands(ref.count.rename(['ndvi_reference_years', 'lst_reference_years']))
    .addBands(span.rename(['ndvi_reference_span', 'lst_reference_span']))
    .setDefaultProjection(grid);
}

// Exclusive literature-inspired bins. Not locally calibrated drought truth.
function classes(vhi) {
  return vhi.gte(10).add(vhi.gte(20)).add(vhi.gte(30)).add(vhi.gte(40)).rename('class');
}

boundary.size().evaluate(function(count, error) {
  if (error || count !== 1) { print('STOP: boundary must contain one feature', error, count); return; }
  var aoi = boundary.geometry(), pixelArea = ee.Image.pixelArea();
  function sum(mask, projection) {
    return ee.Number(pixelArea.rename('area').updateMask(mask).unmask(0).reduceRegion({
      reducer: ee.Reducer.sum(), geometry: aoi, crs: projection || grid,
      maxPixels: 1e8, tileScale: 4}).get('area', 0));
  }
  var districtArea = sum(ee.Image.constant(1));
  function means(image, mask) {
    var denominator = sum(mask);
    var totals = image.updateMask(mask).multiply(pixelArea).unmask(0).reduceRegion({
      reducer: ee.Reducer.sum(), geometry: aoi, crs: grid, maxPixels: 1e8, tileScale: 4});
    return totals.map(function(key, value) {
      return ee.Algorithms.If(denominator.gt(0), ee.Number(value).divide(denominator), null);
    });
  }
  var rows = [], history = [];
  CFG.months.forEach(function(month) {
    scenarios.forEach(function(scenario) {
      for (var y = CFG.baselineStart; y <= CFG.endYear; y++) {
        var current = monthly(y, month, scenario), nm = current.select('ndvi').mask();
        var tm = current.select('lst_k').mask();
        history.push(ee.Feature(null, means(current.select('ndvi'), nm)).set({
          year: y, month: month, scenario: scenario.id, date: current.get('date'),
          ndvi_valid_fraction: sum(nm).divide(districtArea),
          lst_valid_fraction: sum(tm).divide(districtArea),
          ndvi_source_images: current.get('ndvi_source_images'),
          lst_source_images: current.get('lst_source_images'), boundary_code: boundary.first().get('ADM2_CODE')}));
      }
    });
    for (var year = CFG.startYear; year <= CFG.endYear; year++) {
      var images = scenarios.map(function(s) { return indices(year, month, s); });
      var shared = ee.Image.constant(1);
      images.forEach(function(im) { shared = shared.and(im.select('vhi').mask().unmask(0).gt(0)); });
      images.forEach(function(im, i) {
        var scenario = scenarios[i], own = im.select('vhi').mask();
        ['own', 'all_variants_common'].forEach(function(support) {
          var mask = support === 'own' ? own : shared;
          var area = sum(mask), classImage = classes(im.select('vhi'));
          var props = means(im.select(['ndvi', 'lst_k', 'vci', 'tci', 'vhi',
            'ndvi_observations', 'lst_observations', 'ndvi_reference_years',
            'lst_reference_years', 'ndvi_reference_span', 'lst_reference_span']), mask);
          var f = ee.Feature(null, props).set({date: im.get('date'), year: year, month: month,
            scenario: scenario.id, support: support, alpha: CFG.alpha,
            valid_area_km2: area.divide(1e6), district_area_km2: districtArea.divide(1e6),
            valid_fraction: area.divide(districtArea), unknown_fraction: ee.Number(1).subtract(area.divide(districtArea)),
            baseline_start: CFG.baselineStart, baseline_end: CFG.baselineEnd,
            min_ndvi_years: CFG.minYears, min_lst_years: CFG.minYears,
            boundary_code: boundary.first().get('ADM2_CODE'),
            boundary_source: CFG.boundaryAsset || 'FAO/GAUL/2015/level2',
            method: 'controlled_reconstruction_v0.2',
            lst_product: scenario.daily ? 'MOD11A1_061' : 'MOD11A2_061',
            lst_min_current_observations: 1,
            ndvi_source_images: im.get('ndvi_source_images'), lst_source_images: im.get('lst_source_images')});
          for (var c = 0; c < 5; c++) {
            var ca = sum(mask.and(classImage.eq(c)));
            f = f.set('class_' + c + '_fraction_valid', ee.Algorithms.If(area.gt(0), ca.divide(area), null));
          }
          var outside = sum(mask.and(im.select('vhi').lt(0).or(im.select('vhi').gt(100))));
          f = f.set('vhi_outside_0_100_fraction_valid', ee.Algorithms.If(area.gt(0), outside.divide(area), null));
          var pairMask = mask.and(images[0].select('vhi').mask()), pairArea = sum(pairMask);
          var disagreement = sum(pairMask.and(classImage.neq(classes(images[0].select('vhi')))));
          f = f.set('pair_A_valid_fraction', pairArea.divide(districtArea))
            .set('class_disagreement_vs_A', ee.Algorithms.If(pairArea.gt(0), disagreement.divide(pairArea), null));
          rows.push(f);
        });
      });
    }
  });
  Export.table.toDrive({collection: ee.FeatureCollection(rows),
    description: 'beed_controlled_seasonal_2020_2024', folder: CFG.exportFolder, fileFormat: 'CSV'});
  Export.table.toDrive({collection: ee.FeatureCollection(history),
    description: 'beed_policy_history_2001_2024', folder: CFG.exportFolder, fileFormat: 'CSV'});

  // Complete daily coverage per pixel is required for a monthly rainfall total.
  var rainArea = sum(ee.Image.constant(1), rainGrid), rainRows = [];
  for (var ry = CFG.rainfallStart; ry <= CFG.rainfallEnd; ry++) {
    for (var rm = 1; rm <= 12; rm++) {
      var rs = ee.Date.fromYMD(ry, rm, 1), re = rs.advance(1, 'month');
      var source = rain.filterDate(rs, re), expectedDays = re.difference(rs, 'day');
      var total = source.sum().updateMask(source.count().eq(ee.Image.constant(expectedDays)));
      var ra = sum(total.mask(), rainGrid);
      var weighted = ee.Number(total.multiply(pixelArea).rename('weighted').unmask(0).reduceRegion({
        reducer: ee.Reducer.sum(), geometry: aoi, crs: rainGrid, maxPixels: 1e8, tileScale: 4}).get('weighted', 0));
      rainRows.push(ee.Feature(null, {date: rs.format('YYYY-MM'), year: ry, month: rm,
        rain_mm: ee.Algorithms.If(ra.gt(0), weighted.divide(ra), null),
        rain_days: source.size(), expected_days: expectedDays,
        rain_valid_fraction: ra.divide(rainArea), rain_area_km2: ra.divide(1e6),
        district_area_rain_grid_km2: rainArea.divide(1e6),
        boundary_code: boundary.first().get('ADM2_CODE'),
        boundary_source: CFG.boundaryAsset || 'FAO/GAUL/2015/level2',
        dataset: 'UCSB-CHG/CHIRPS/DAILY', aggregation: 'district_area_weighted_monthly_total'}));
    }
  }
  Export.table.toDrive({collection: ee.FeatureCollection(rainRows),
    description: 'beed_chirps_monthly_1981_2024', folder: CFG.exportFolder, fileFormat: 'CSV'});
  print('Prepared row counts', {comparison: rows.length, history: history.length, rainfall: rainRows.length});
  print('Boundary remains provisional', boundary);
  Map.centerObject(boundary, 9);
  scenarios.forEach(function(scenario) {
    Map.addLayer(indices(2023, 10, scenario).select('vhi').clip(aoi),
      {min: 0, max: 100, palette: ['8c2d04', 'fec44f', 'ffffcc', '78c679', '006837']}, scenario.id, false);
  });
  Map.addLayer(ee.Image().byte().paint(boundary, 1, 2), {palette: ['000000']}, 'Provisional boundary');
});
