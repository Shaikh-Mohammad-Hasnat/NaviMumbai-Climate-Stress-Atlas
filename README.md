# Navi Mumbai Climate Stress Atlas

A ward-level climate stress atlas for Navi Mumbai (Maharashtra, India), built with QGIS and Google Earth Engine. The goal is to rank the city's **111 municipal wards** by how exposed they are to climate stress, starting with urban heat.

> **Status: work in progress.** The ward base layer and boundary are done and checked. The stress indicators and the composite index (below) are the next step. Nothing here is a finished analysis yet.

## What's in the repo

| Path | Content |
|---|---|
| `NaviMumbai_Atlas.gpkg` | GeoPackage with the cleaned layers: `wards_32643` (111 ward polygons, UTM 43N), `nmmc_boundary_32643` (the city boundary, a plain union of the 111 wards, about 122.9 km²; it is not an official NMMC dataset) and two raw ward layers in EPSG:4326, one from each source, kept for cross-checking. |
| `qa_maps/` | Quality-check maps of the wards and boundary, including an overlay on satellite imagery. |

## Method (planned)

1. **Base layer:** 111 NMMC wards, reprojected to EPSG:32643 so that areas are in metres.
2. **Indicators from Google Earth Engine:** satellite-derived heat, vegetation and built-up measures per ward (final indicator list to be decided).
3. **Urban Climate Stress Index (UCSI):** each indicator is normalised per ward and combined with weights into one score, then mapped and ranked by ward.
4. **Atlas:** print-ready QGIS layouts and a short write-up of the highest-stress wards.

## Data sources

- Ward boundaries: Bharatlas (GeoJSON) and OpenCity (Navi Mumbai wards 2024, KML). Both contain 111 wards, which is how the count was cross-checked. The Bharatlas layer traces back to OpenCity / Oorvani and the ESRI Living Atlas India. The raw downloads are not republished here, so fetch them from the source sites and check their licences before reuse.

## Tools
QGIS 3, Google Earth Engine, GeoPackage / SQLite, EPSG:32643.

## Author
Shaikh Mohammad Hasnat, [GitHub](https://github.com/Shaikh-Mohammad-Hasnat)
