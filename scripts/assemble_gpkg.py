# Build NaviMumbai_UCSI.gpkg with declared field types (Integer, Text, Decimal, Date). Run with QGIS Python.
import os, csv, datetime, shutil
from osgeo import ogr, osr
ogr.UseExceptions()
B = "C:/Users/farha/AppData/Local/Temp/claude/G--5-Claude-Chats-college/081d4375-70ed-43ee-a64d-1d2d6cb50bb2/scratchpad/hasnat/build/"
OUT = "G:/1 Programming/College/GIS-CA3-Hasnat/CA4_Project/data/"
os.makedirs(OUT + "rasters", exist_ok=True)
gpkg = OUT + "NaviMumbai_UCSI.gpkg"
if os.path.exists(gpkg): os.remove(gpkg)
drv = ogr.GetDriverByName("GPKG"); ds = drv.CreateDataSource(gpkg)
srs = osr.SpatialReference(); srs.ImportFromEPSG(32643); srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
I, S, R, D = ogr.OFTInteger, ogr.OFTString, ogr.OFTReal, ogr.OFTDate

SPEC = {
    "study_boundary": ("vectors/study_boundary.geojson", ogr.wkbMultiPolygon, [("Boundary_ID", I), ("Name", S), ("N_Wards", I), ("Area_km2", R), ("Source", S), ("Created", D)]),
    "wards": ("vectors/wards.geojson", ogr.wkbMultiPolygon, [("Ward_ID", I), ("Ward_Name", S), ("LGD_Code", I), ("Area_km2", R), ("LST_C", R), ("NDVI", R), ("BuiltUp_Pct", R), ("GreenCover_Pct", R), ("Water_Pct", R), ("Elev_m", R),
              ("Slope_Pct", R), ("DistWater_m", R), ("F_Elev", I), ("F_Slope", I), ("F_Water", I), ("F_BuiltUp", I), ("Heat_Score", R), ("GreenDef_Score", R), ("Flood_Score", R), ("UCSI", R), ("UCSI_Class", S), ("UCSI_Rank", I), ("Period_Start", D), ("Period_End", D)]),
    "water_bodies": ("vectors/water_bodies2.geojson", ogr.wkbMultiPolygon, [("Water_ID", I), ("Water_Type", S), ("Area_ha", R), ("Source", S)]),
    "major_roads": ("vectors/major_roads.geojson", ogr.wkbMultiLineString, [("Road_ID", I), ("Road_Name", S), ("Road_Type", S), ("Ref", S), ("Length_km", R), ("Flooded_2025", S), ("Source", S)]),
    "hospitals": ("vectors/hospitals.geojson", ogr.wkbPoint, [("Hosp_ID", I), ("Name", S), ("Type", S), ("Ward_ID", I), ("Source", S)]),
    "flood_reports": ("vectors/flood_reports.geojson", ogr.wkbPoint, [("Report_ID", I), ("Site", S), ("Report_Type", S), ("Event_Date", D), ("Rain_mm", R), ("Note", S), ("Source", S)]),
    "hot_lowgreen_zones": ("vectors/hot_lowgreen_zones2.geojson", ogr.wkbMultiPolygon, [("Zone_ID", I), ("Area_ha", R), ("Mean_LST_C", R), ("Mean_NDVI", R), ("Rule", S)]),
}
def setval(feat, name, typ, val):
    if val is None or val == "" or (isinstance(val, float) and val != val): feat.SetFieldNull(name); return
    if typ == D:
        y, m, d = [int(x) for x in str(val)[:10].replace("/", "-").split("-")]; feat.SetField(name, y, m, d, 0, 0, 0, 0)
    elif typ == I: feat.SetField(name, int(val))
    elif typ == R: feat.SetField(name, float(val))
    else: feat.SetField(name, str(val))
for lname, (src, gtype, fields) in SPEC.items():
    lyr = ds.CreateLayer(lname, srs, gtype, options=["SPATIAL_INDEX=YES", "GEOMETRY_NAME=geom", "FID=fid"])
    for n, t in fields: lyr.CreateField(ogr.FieldDefn(n, t))
    sds = ogr.Open(B + src); slyr = sds.GetLayer(0); cnt = 0
    for sf in slyr:
        nf = ogr.Feature(lyr.GetLayerDefn()); g = sf.GetGeometryRef().Clone()
        g = ogr.ForceTo(g, gtype); g.AssignSpatialReference(srs); nf.SetGeometry(g)
        for n, t in fields: setval(nf, n, t, sf.GetField(n) if sf.GetFieldIndex(n) >= 0 else None)
        lyr.CreateFeature(nf); cnt += 1
    print(lname, cnt, "features")
# attribute table without geometry (one ward has many dates)
tb = ds.CreateLayer("ward_lst_by_date", None, ogr.wkbNone, options=["FID=fid"])
tfields = [("Ward_ID", I), ("Scene_ID", S), ("Scene_Date", D), ("Platform", S), ("LST_Mean_C", R), ("Valid_Pixels", I)]
for n, t in tfields: tb.CreateField(ogr.FieldDefn(n, t))
n = 0
for row in csv.DictReader(open(B + "tables/ward_lst_by_date.csv", encoding="utf8")):
    f = ogr.Feature(tb.GetLayerDefn())
    for nm, t in tfields: setval(f, nm, t, row[nm])
    tb.CreateFeature(f); n += 1
print("ward_lst_by_date", n, "rows")
ds = None
for f in os.listdir(B + "rasters"): shutil.copy2(B + "rasters/" + f, OUT + "rasters/" + f)
print("gpkg written:", os.path.getsize(gpkg) // 1024, "KB; rasters copied:", len(os.listdir(OUT + "rasters")))
