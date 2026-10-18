// ============================================================================
// 01  Land Surface Temperature (LST), Navi Mumbai, April 2026
// Data: Landsat 8 + 9 Collection 2 Level 2, band ST_B10 (surface temperature)
// Output: LST_Apr2026_C.tif (30 m, EPSG:32643) in Google Drive folder NaviMumbai_GEE
// BEFORE RUNNING: upload the ward polygons as an Earth Engine asset (see README.txt)
// ============================================================================
var wards = ee.FeatureCollection('projects/YOUR_PROJECT/assets/navi_mumbai_wards'); // <-- change to your asset path
var region = wards.geometry().dissolve(50);
Map.centerObject(region, 11);

// Clear April 2026 scenes: 13, 22 and 30 April (cloud cover < 20%)
var start = '2026-04-10', end = '2026-05-01';   // end date is exclusive

function prepLandsat(img) {
  // QA_PIXEL bits: 1 = dilated cloud, 2 = cirrus, 3 = cloud, 4 = cloud shadow
  var qa = img.select('QA_PIXEL');
  var clear = qa.bitwiseAnd(1 << 1).eq(0)
      .and(qa.bitwiseAnd(1 << 2).eq(0))
      .and(qa.bitwiseAnd(1 << 3).eq(0))
      .and(qa.bitwiseAnd(1 << 4).eq(0));
  // Scale factors from the Earth Engine catalog: ST = DN * 0.00341802 + 149.0 (Kelvin)
  var lstC = img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('LST_C');
  return lstC.updateMask(clear).copyProperties(img, ['system:time_start']);
}

var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2');
var l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2');
var scenes = l8.merge(l9).filterBounds(region).filterDate(start, end)
    .filter(ee.Filter.lt('CLOUD_COVER', 20));
print('Landsat scenes used (expect about 3):', scenes.size());
print('Scene dates:', scenes.aggregate_array('DATE_ACQUIRED'));

var lst = scenes.map(prepLandsat).median().clip(region);
lst = lst.updateMask(lst.gt(10).and(lst.lt(70)));   // remove impossible values

Map.addLayer(lst, {min: 32, max: 48, palette: ['#FFF4D6', '#FDD28A', '#F59E42', '#DC5A2B', '#8E1B1F']}, 'LST (C) April 2026');

// Quick check: mean LST inside the study area (the delivered raster gives about 41.0 C)
print('Mean LST (C):', lst.reduceRegion({reducer: ee.Reducer.mean(), geometry: region, scale: 30, maxPixels: 1e9}));

Export.image.toDrive({image: lst, description: 'LST_Apr2026_C', folder: 'NaviMumbai_GEE',
  region: region, scale: 30, crs: 'EPSG:32643', maxPixels: 1e9});
