// ============================================================================
// 03  Built-up land and land cover, Navi Mumbai
// Data: Dynamic World V1 (built probability, label 6 = built area) for March-April 2026
//       ESA WorldCover v200 (2021), class 50 = built-up  (used for the delivered rasters)
// Output: BuiltUp_DynamicWorld.tif and LandCover_WorldCover2021.tif (10 m, EPSG:32643)
// ============================================================================
var wards = ee.FeatureCollection('projects/YOUR_PROJECT/assets/navi_mumbai_wards'); // <-- change to your asset path
var region = wards.geometry().dissolve(50);
Map.centerObject(region, 11);

// --- Dynamic World: most frequent class per pixel over March-April 2026
var dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1').filterBounds(region).filterDate('2026-03-01', '2026-05-01');
var dwBuilt = dw.select('label').mode().eq(6).rename('Built').clip(region);          // 1 = built, 0 = other
var dwBuiltProb = dw.select('built').mean().rename('Built_Prob').clip(region);       // 0-1 probability

// --- ESA WorldCover 2021 (this product is what the delivered project uses)
var wc = ee.ImageCollection('ESA/WorldCover/v200').first().select('Map').clip(region);
var wcBuilt = wc.eq(50).rename('Built');

Map.addLayer(dwBuiltProb, {min: 0, max: 1, palette: ['#FFFFFF', '#4B5563']}, 'Dynamic World: built probability', false);
Map.addLayer(dwBuilt.selfMask(), {palette: ['#4B5563']}, 'Dynamic World: built (mode)');
Map.addLayer(wcBuilt.selfMask(), {palette: ['#B91C1C']}, 'WorldCover: built-up', false);

// Share of the study area that is built-up (delivered WorldCover result: about 33%)
function share(img) {
  return img.reduceRegion({reducer: ee.Reducer.mean(), geometry: region, scale: 10, maxPixels: 1e9}).get('Built');
}
print('Built-up share, Dynamic World (0-1):', share(dwBuilt));
print('Built-up share, WorldCover (0-1):', share(wcBuilt));

Export.image.toDrive({image: dwBuilt, description: 'BuiltUp_DynamicWorld', folder: 'NaviMumbai_GEE', region: region, scale: 10, crs: 'EPSG:32643', maxPixels: 1e9});
Export.image.toDrive({image: wc, description: 'LandCover_WorldCover2021', folder: 'NaviMumbai_GEE', region: region, scale: 10, crs: 'EPSG:32643', maxPixels: 1e9});
