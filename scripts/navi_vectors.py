# Stage 2: vector layers for the GeoPackage (EPSG:32643). Reads OSM downloads + stage-1 outputs.
import json, numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

GPKG = "C:/Users/farha/Downloads/hasnat gsi ca/NaviMumbai_Atlas/NaviMumbai_Atlas/NaviMumbai_Atlas.gpkg"
CRS = 32643
wards0 = gpd.read_file(GPKG, layer="wards_32643"); wards0["Ward_ID"] = wards0["sourcewardcode"].astype(int)
wards0 = wards0.sort_values("Ward_ID").reset_index(drop=True)
df = pd.read_csv("build/tables/ward_stats_full.csv").sort_values("ward_no").reset_index(drop=True)
assert (df.ward_no.values == wards0.Ward_ID.values).all()
labels = ["Lowest", "Low", "Medium", "High", "Highest"]
W = wards0[["Ward_ID", "ward_lgd_code", "geometry"]].copy()
W["Ward_Name"] = ["Ward " + str(i) for i in W.Ward_ID]
W["LGD_Code"] = W.ward_lgd_code.fillna(0).astype(int); W = W.drop(columns="ward_lgd_code")
W["Area_km2"] = df.area_km2.round(4)
for src, dst, nd in [("lst_c", "LST_C", 3), ("ndvi", "NDVI", 4), ("builtup_pct", "BuiltUp_Pct", 2), ("green_pct", "GreenCover_Pct", 1), ("water_pct", "Water_Pct", 1), ("elev_m", "Elev_m", 2),
                     ("slope_pct", "Slope_Pct", 3), ("dist_water_m", "DistWater_m", 1), ("f_elev", "F_Elev", 0), ("f_slope", "F_Slope", 0), ("f_dist", "F_Water", 0), ("f_bu", "F_BuiltUp", 0),
                     ("heat", "Heat_Score", 2), ("green_def", "GreenDef_Score", 2), ("flood", "Flood_Score", 2), ("ucsi", "UCSI", 2)]:
    W[dst] = df[src].round(nd)
W["UCSI_Class"] = [labels[i] for i in df.ucls]; W["UCSI_Rank"] = df["rank"].astype(int)
W["Period_Start"] = "2026-04-08"; W["Period_End"] = "2026-04-30"
W.to_file("build/vectors/wards.geojson", driver="GeoJSON")
union = unary_union(wards0.geometry)

# ---- boundary
B = gpd.read_file(GPKG, layer="nmmc_boundary_32643")
B = gpd.GeoDataFrame({"Boundary_ID": [1], "Name": ["Navi Mumbai study area (dissolved from 111 wards)"], "N_Wards": [111], "Area_km2": [round(float(B.geometry.area.sum() / 1e6), 4)],
                      "Source": ["OpenCity / BharatLAS ward polygons (not an official NMMC dataset)"], "Created": ["2026-09-25"]}, geometry=[B.geometry.iloc[0]], crs=CRS)
B.to_file("build/vectors/study_boundary.geojson", driver="GeoJSON")

# ---- major roads (OSM)
R = json.load(open("build/osm_roads.json"))["elements"]
rows = []
for e in R:
    if "geometry" not in e or len(e["geometry"]) < 2: continue
    t = e.get("tags", {}); nm = t.get("name") or "Unnamed road"
    rows.append({"Road_Name": nm, "Road_Type": t.get("highway"), "Ref": t.get("ref"), "geometry": LineString([(p["lon"], p["lat"]) for p in e["geometry"]])})
G = gpd.GeoDataFrame(rows, crs=4326).to_crs(CRS)
G = G[G.intersects(union.buffer(300))].reset_index(drop=True)
G["Length_km"] = (G.geometry.length / 1000).round(3); G["Road_ID"] = G.index + 1
G["Flooded_2025"] = np.where(G.Road_Name.isin(["Thane Belapur Road", "Sion-Panvel Highway"]), "Yes", "No")
G["Source"] = "OpenStreetMap"
G = G[["Road_ID", "Road_Name", "Road_Type", "Ref", "Length_km", "Flooded_2025", "Source", "geometry"]]
G.to_file("build/vectors/major_roads.geojson", driver="GeoJSON"); print("roads", len(G), "km", round(G.Length_km.sum(), 1), "flooded-flag", int((G.Flooded_2025 == "Yes").sum()))

# ---- hospitals (OSM)
H = json.load(open("build/osm_hosp.json"))["elements"]
rows = []
for e in H:
    c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
    if c["lat"] is None: continue
    t = e.get("tags", {}); rows.append({"Name": t.get("name") or "Unnamed hospital", "Type": t.get("healthcare") or t.get("amenity") or "hospital", "geometry": Point(c["lon"], c["lat"])})
P = gpd.GeoDataFrame(rows, crs=4326).to_crs(CRS)
P = P[P.within(union)].reset_index(drop=True)
P["key"] = P.Name + P.geometry.apply(lambda g: f"{round(g.x / 20)}_{round(g.y / 20)}"); P = P.drop_duplicates("key").drop(columns="key").reset_index(drop=True)
P["Hosp_ID"] = P.index + 1
P = gpd.sjoin(P, W[["Ward_ID", "geometry"]], how="left", predicate="within").drop(columns="index_right")
P["Ward_ID"] = P.Ward_ID.fillna(0).astype(int); P["Source"] = "OpenStreetMap"
P = P[["Hosp_ID", "Name", "Type", "Ward_ID", "Source", "geometry"]]
P.to_file("build/vectors/hospitals.geojson", driver="GeoJSON"); print("hospitals inside study area", len(P))

# ---- flood reports (points digitised from the news report of 26 May 2025; coordinates from OSM place nodes / market ways)
pl = json.load(open("build/osm_places2.json"))["elements"]
def mean_pt(names):
    xs = [(e["lon"], e["lat"]) for e in pl if e["tags"]["name"] in names]; return Point(np.mean([a for a, _ in xs]), np.mean([b for _, b in xs]))
ap = json.load(open("build/osm_apmc.json"))["elements"]
mk = [e["center"] for e in ap if e.get("tags", {}).get("amenity") == "marketplace" and "center" in e]
apmc = Point(np.mean([c["lon"] for c in mk]), np.mean([c["lat"] for c in mk]))
FR = gpd.GeoDataFrame({"Site": ["Nerul", "Belapur", "APMC market, Vashi"],
                       "Report_Type": ["Rainfall record", "Rainfall record", "Waterlogged site"],
                       "Event_Date": ["2025-05-26"] * 3, "Rain_mm": [155.7, 133.9, None],
                       "Note": ["Reported rain 8:30 am to 4:30 pm. Point = centre of the OSM Nerul East/West suburb nodes (approximate, not a gauge location)", "Reported rain 8:30 am to 4:30 pm. Point = centre of the OSM Belapur East/West suburb nodes (approximate, not a gauge location)", "Reported flooding at the market. Point = centre of the four OSM APMC market yards (approximate)"],
                       "Source": ["Free Press Journal, 26 May 2025"] * 3},
                      geometry=gpd.GeoSeries([mean_pt(["Nerul East", "Nerul West"]), mean_pt(["Belapur East", "Belapur West"]), apmc], crs=4326).to_crs(CRS), crs=CRS)
FR["Report_ID"] = [1, 2, 3]; FR = FR[["Report_ID", "Site", "Report_Type", "Event_Date", "Rain_mm", "Note", "Source", "geometry"]]
FR.to_file("build/vectors/flood_reports.geojson", driver="GeoJSON")
print("flood reports inside wards:", [bool(g.within(union)) for g in FR.geometry])

# ---- water bodies and hot zones (renamed from stage 1)
wb = gpd.read_file("build/vectors/water_bodies.geojson"); wb["Source"] = "ESA WorldCover 2021 (10 m), polygons >= 0.5 ha"; wb = wb[["Water_ID", "Water_Type", "Area_ha", "Source", "geometry"]]
wb["Area_ha"] = wb.Area_ha.round(2); wb.to_file("build/vectors/water_bodies2.geojson", driver="GeoJSON")
hz = gpd.read_file("build/vectors/hot_lowgreen_zones.geojson"); hz["Rule"] = "LST >= 45 C and NDVI < 0.2 (30 m), patches >= 2 ha"; hz["Area_ha"] = hz.Area_ha.round(2)
hz = hz[["Zone_ID", "Area_ha", "Mean_LST_C", "Mean_NDVI", "Rule", "geometry"]]; hz.to_file("build/vectors/hot_lowgreen_zones2.geojson", driver="GeoJSON")
print("vectors done")
