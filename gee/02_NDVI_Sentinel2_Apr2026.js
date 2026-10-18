// ============================================================================
// 02  Vegetation index (NDVI), Navi Mumbai, April 2026
// Data: Sentinel-2 Level-2A surface reflectance (harmonized), bands B8 (NIR) and B4 (red)
// Output: NDVI_Apr2026.tif (10 m, EPSG:32643)
// ============================================================================
var wards = ee.FeatureCollection('projects/YOUR_PROJECT/assets/navi_mumbai_wards'); // <-- change to your asset path
var region = wards.geometry().dissolve(50);
Map.centerObject(region, 11);

// Clear scenes on 8 and 11 April 2026 (cloud < 10%)
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(region)
    .filterDate('2026-04-08', '2026-04-13')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10));
print('Sentinel-2 scenes used (expect about 2):', s2.size());

function ndviClear(img) {
  var scl = img.select('SCL');
  // remove cloud shadow (3), cloud medium/high (8, 9) and cirrus (10)
  var bad = scl.eq(3).or(scl.eq(8)).or(scl.eq(9)).or(scl.eq(10));
  return img.normalizedDifference(['B8', 'B4']).rename('NDVI').updateMask(bad.not());
}
var ndvi = s2.map(ndviClear).median().clip(region);

Map.addLayer(ndvi, {min: 0, max: 0.7, palette: ['#D8C9A3', '#EAE7B0', '#AAD38C', '#4E9F50', '#1B6B3A']}, 'NDVI April 2026');
print('Mean NDVI (the delivered raster gives about 0.30):', ndvi.reduceRegion({reducer: ee.Reducer.mean(), geometry: region, scale: 10, maxPixels: 1e9}));

Export.image.toDrive({image: ndvi, description: 'NDVI_Apr2026', folder: 'NaviMumbai_GEE',
  region: region, scale: 10, crs: 'EPSG:32643', maxPixels: 1e9});
