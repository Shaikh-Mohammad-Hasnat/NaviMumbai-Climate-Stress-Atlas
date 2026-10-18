// ============================================================================
// 05  Ward-level statistics (zonal mean) for all 111 wards
// Output: two CSV tables in Drive: Ward_stats_30m.csv (LST, elevation, slope) and
//         Ward_stats_10m.csv (NDVI, built-up, green, water, distance to water)
// Join them to the wards layer in QGIS on the field Ward_ID, then run the Field Calculator
// formulas given in the report (Heat_Score, GreenDef_Score, Flood_Score, UCSI).
// ============================================================================
var wards = ee.FeatureCollection('projects/YOUR_PROJECT/assets/navi_mumbai_wards'); // must contain the field Ward_ID
var region = wards.geometry().dissolve(50);

// ---- LST (same steps as script 01)
function prepLandsat(img) {
  var qa = img.select('QA_PIXEL');
  var clear = qa.bitwiseAnd(1 << 1).eq(0).and(qa.bitwiseAnd(1 << 2).eq(0)).and(qa.bitwiseAnd(1 << 3).eq(0)).and(qa.bitwiseAnd(1 << 4).eq(0));
  return img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('LST_C').updateMask(clear);
}
var lst = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2'))
    .filterBounds(region).filterDate('2026-04-10', '2026-05-01').filter(ee.Filter.lt('CLOUD_COVER', 20))
    .map(prepLandsat).median();
lst = lst.updateMask(lst.gt(10).and(lst.lt(70)));

// ---- Elevation and slope (%)
var srtm = ee.Image('USGS/SRTMGL1_003').select('elevation');
var elev = srtm.rename('Elev_m');
var slopePct = ee.Terrain.slope(srtm).multiply(Math.PI / 180).tan().multiply(100).rename('Slope_pct');

// ---- NDVI (same steps as script 02)
function ndviClear(img) {
  var scl = img.select('SCL');
  var bad = scl.eq(3).or(scl.eq(8)).or(scl.eq(9)).or(scl.eq(10));
  return img.normalizedDifference(['B8', 'B4']).rename('NDVI').updateMask(bad.not());
}
var ndvi = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(region).filterDate('2026-04-08', '2026-04-13')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)).map(ndviClear).median();

// ---- WorldCover: built-up %, green %, water %, distance to water
var wc = ee.ImageCollection('ESA/WorldCover/v200').first().select('Map');
var builtPct = wc.eq(50).multiply(100).rename('BuiltUp_Pct');
var greenPct = wc.eq(10).or(wc.eq(20)).or(wc.eq(30)).or(wc.eq(95)).multiply(100).rename('GreenCover_Pct');
var waterPct = wc.eq(80).or(wc.eq(90)).or(wc.eq(95)).multiply(100).rename('Water_Pct');
var wet = wc.eq(80).or(wc.eq(95));
var distWater = wet.not().fastDistanceTransform(256).sqrt().multiply(10).rename('DistWater_m');

var stack30 = lst.addBands(elev).addBands(slopePct);
var stack10 = ndvi.addBands(builtPct).addBands(greenPct).addBands(waterPct).addBands(distWater);

var stats30 = stack30.reduceRegions({collection: wards, reducer: ee.Reducer.mean(), scale: 30, crs: 'EPSG:32643'});
var stats10 = stack10.reduceRegions({collection: wards, reducer: ee.Reducer.mean(), scale: 10, crs: 'EPSG:32643'});

print('First rows (30 m):', stats30.limit(3));
print('First rows (10 m):', stats10.limit(3));

Export.table.toDrive({collection: stats30, description: 'Ward_stats_30m', folder: 'NaviMumbai_GEE', fileFormat: 'CSV',
  selectors: ['Ward_ID', 'LST_C', 'Elev_m', 'Slope_pct']});
Export.table.toDrive({collection: stats10, description: 'Ward_stats_10m', folder: 'NaviMumbai_GEE', fileFormat: 'CSV',
  selectors: ['Ward_ID', 'NDVI', 'BuiltUp_Pct', 'GreenCover_Pct', 'Water_Pct', 'DistWater_m']});
