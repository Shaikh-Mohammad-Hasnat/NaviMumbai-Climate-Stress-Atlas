// ============================================================================
// 04  Flood-factor rasters: elevation, slope (%), distance to water/mangrove
// Data: SRTM 30 m (USGS/SRTMGL1_003), ESA WorldCover v200 (water = 80, mangrove = 95)
// Output: Elevation_SRTM_m.tif, Slope_SRTM_pct.tif (30 m); Distance_to_Water_m.tif (10 m)
// ============================================================================
var wards = ee.FeatureCollection('projects/YOUR_PROJECT/assets/navi_mumbai_wards'); // <-- change to your asset path
var region = wards.geometry().dissolve(50);
Map.centerObject(region, 11);

var srtm = ee.Image('USGS/SRTMGL1_003').select('elevation');
var elevation = srtm.clip(region).rename('Elev_m');
var slopeDeg = ee.Terrain.slope(srtm);                                        // degrees
var slopePct = slopeDeg.multiply(Math.PI / 180).tan().multiply(100).clip(region).rename('Slope_pct');

var wc = ee.ImageCollection('ESA/WorldCover/v200').first().select('Map');
var wet = wc.eq(80).or(wc.eq(95));                                            // water or mangrove
// fastDistanceTransform gives the squared distance (in pixels) from each non-zero pixel to the nearest zero pixel,
// so we apply it to the "not wet" image. The pixel size is 10 m.
var distWater = wet.not().fastDistanceTransform(256).sqrt().multiply(10).clip(region).rename('DistWater_m');

Map.addLayer(elevation, {min: 0, max: 60, palette: ['#DDEBD5', '#E9E3B5', '#E2C58A', '#CF9A62', '#A9683A']}, 'Elevation (m)');
Map.addLayer(distWater, {min: 0, max: 1500, palette: ['#2563EB', '#93C5FD', '#FFFFFF']}, 'Distance to water (m)', false);

Export.image.toDrive({image: elevation, description: 'Elevation_SRTM_m', folder: 'NaviMumbai_GEE', region: region, scale: 30, crs: 'EPSG:32643', maxPixels: 1e9});
Export.image.toDrive({image: slopePct, description: 'Slope_SRTM_pct', folder: 'NaviMumbai_GEE', region: region, scale: 30, crs: 'EPSG:32643', maxPixels: 1e9});
Export.image.toDrive({image: distWater, description: 'Distance_to_Water_m', folder: 'NaviMumbai_GEE', region: region, scale: 10, crs: 'EPSG:32643', maxPixels: 1e9});
