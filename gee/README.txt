GOOGLE EARTH ENGINE SCRIPTS: how to run them (about 30 minutes)
================================================================

WHAT THESE SCRIPTS DO
Five Code Editor scripts (JavaScript) that collect the satellite data for the project:
  01 LST (Landsat 8/9)  ->  LST_Apr2026_C.tif
  02 NDVI (Sentinel-2)  ->  NDVI_Apr2026.tif
  03 Built-up (Dynamic World + WorldCover)
  04 Elevation, slope, distance to water
  05 Ward statistics (CSV tables)
They use the same datasets and the same dates as the rasters delivered in data/rasters.
The delivered rasters were produced with an equivalent workflow outside Earth Engine
(same public datasets). Run these scripts under your own account and compare the numbers
(see "Check your results" below). Report honestly in your write-up which results came from Earth Engine.

STEP 1  Register (free)
  - Open https://code.earthengine.google.com and sign in.
  - Register a Google Cloud project for NON-COMMERCIAL use (Community tier, no billing account needed).

STEP 2  Upload the wards as an asset
  - In QGIS: right-click layer "wards" > Export > Save Features As... > ESRI Shapefile, CRS EPSG:4326,
    keep fields Ward_ID and Ward_Name.  Zip the .shp/.dbf/.shx/.prj files.
  - Earth Engine Code Editor > Assets > NEW > Shape files > upload the zip.
    Asset name: navi_mumbai_wards   (path looks like projects/<your-project>/assets/navi_mumbai_wards)
  - In every script replace 'projects/YOUR_PROJECT/assets/navi_mumbai_wards' with your path.

STEP 3  Run
  - Paste a script, press Run, read the Console, then open the Tasks tab and press RUN on each export.
  - Files appear in Google Drive > NaviMumbai_GEE. Download them into data/rasters_gee/.

CHECK YOUR RESULTS (expected values from the delivered project)
  - Landsat scenes: about 3 (13, 22, 30 April 2026); mean LST inside the study area about 41 C.
  - Sentinel-2 scenes: about 2 (8 and 11 April 2026); mean NDVI about 0.30.
  - Built-up share: WorldCover about 33%; Dynamic World gives a similar value (write down both).
  - Ward 70 should be the hottest ward (about 47-48 C).
  If your numbers differ by more than 1-2 C (LST) or 0.03 (NDVI), check dates, cloud filters and the asset.

IF EARTH ENGINE IS NOT AVAILABLE
  The delivered rasters in data/rasters can be used directly; say so in the report.

NOTES
  - Scripts were written from the official dataset pages (dataset IDs and band names checked on 26 Sep 2026):
    LANDSAT/LC08/C02/T1_L2, LANDSAT/LC09/C02/T1_L2 (ST_B10 scale 0.00341802, offset 149.0),
    COPERNICUS/S2_SR_HARMONIZED (B4, B8, SCL), GOOGLE/DYNAMICWORLD/V1 (label 6 = built),
    ESA/WorldCover/v200, USGS/SRTMGL1_003.
  - The scripts were not executed by their author (no Earth Engine account was available); test them before submitting.
