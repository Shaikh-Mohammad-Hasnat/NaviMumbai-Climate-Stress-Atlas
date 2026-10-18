# Stage 1 of the CA4 project build: real satellite rasters + ward statistics + raster-derived vectors (EPSG:32643).
import os, sys, json, gzip, math, subprocess, urllib.request
import numpy as np
np.in1d = np.isin
import pandas as pd, geopandas as gpd, rasterio
from rasterio.features import rasterize, shapes
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import from_bounds
from rasterio.merge import merge
from scipy.ndimage import distance_transform_edt, label
from shapely.geometry import shape
from shapely.ops import unary_union

GPKG = "C:/Users/farha/Downloads/hasnat gsi ca/NaviMumbai_Atlas/NaviMumbai_Atlas/NaviMumbai_Atlas.gpkg"
CRS = "EPSG:32643"
for d in ("build/rasters", "build/tables", "build/vectors", "data"): os.makedirs(d, exist_ok=True)
wards = gpd.read_file(GPKG, layer="wards_32643"); wards["ward_no"] = wards["sourcewardcode"].astype(int)
wards = wards.sort_values("ward_no").reset_index(drop=True)
minx, miny, maxx, maxy = wards.total_bounds
m = 300
gx0, gy0 = math.floor((minx - m) / 30) * 30, math.ceil((maxy + m) / 30) * 30
gx1, gy1 = math.ceil((maxx + m) / 30) * 30, math.floor((miny - m) / 30) * 30
def grid(res): return from_origin(gx0, gy0, res, res), (int((gy0 - gy1) / res), int((gx1 - gx0) / res))
T30, S30 = grid(30); T10, S10 = grid(10)
bb4326 = wards.to_crs(4326).total_bounds

def post(url, body):
    r = subprocess.run(["curl", "-s", "-m", "120", "-X", "POST", url, "-H", "Content-Type: application/json", "-d", json.dumps(body)], capture_output=True)
    return json.loads(r.stdout.decode("utf8"))
def read_to_grid(url, transform, shape_, resampling=Resampling.nearest, dtype="float32"):
    out = np.zeros(shape_, dtype=dtype)
    with rasterio.open(url) as ds:
        left, top = transform.c, transform.f; right, bottom = left + shape_[1] * transform.a, top + shape_[0] * transform.e
        bnds = (left, bottom, right, top) if ds.crs.to_string() == CRS else transform_bounds(CRS, ds.crs, left, bottom, right, top)
        win = from_bounds(*bnds, transform=ds.transform).round_offsets().round_lengths().intersection(rasterio.windows.Window(0, 0, ds.width, ds.height))
        arr = ds.read(1, window=win)
        reproject(arr, out, src_transform=ds.window_transform(win), src_crs=ds.crs, dst_transform=transform, dst_crs=CRS, resampling=resampling)
    return out
def index_raster(T, S): return rasterize([(g, i + 1) for i, g in enumerate(wards.geometry)], out_shape=S, transform=T, fill=0, dtype="int32")
I30, I10 = index_raster(T30, S30), index_raster(T10, S10)
def write_tif(name, arr, T, dtype, nodata, mask=None):
    a = arr.astype(dtype).copy()
    if mask is not None: a[~mask] = nodata
    a = np.where(np.isnan(a.astype("float64")) if a.dtype.kind == "f" else False, nodata, a).astype(dtype)
    with rasterio.open(f"build/rasters/{name}.tif", "w", driver="GTiff", height=a.shape[0], width=a.shape[1], count=1, dtype=dtype, crs=CRS, transform=T, nodata=nodata, compress="deflate", tiled=True) as dst:
        dst.write(a, 1)

# ---------------- Landsat LST per scene (Planetary Computer) ----------------
tok = json.loads(subprocess.run(["curl", "-s", "-m", "40", "https://planetarycomputer.microsoft.com/api/sas/v1/token/landsateuwest/landsat-c2"], capture_output=True).stdout.decode())["token"]
ids = ["LC08_L2SP_148047_20260413_02_T1", "LC08_L2SP_147047_20260422_02_T1", "LC09_L2SP_147047_20260430_02_T1"]
d = post("https://planetarycomputer.microsoft.com/api/stac/v1/search", {"collections": ["landsat-c2-l2"], "ids": ids})
scenes = sorted(d["features"], key=lambda f: f["properties"]["datetime"])
lst_list, meta = [], []
for f in scenes:
    st = read_to_grid(f["assets"]["lwir11"]["href"] + "?" + tok, T30, S30); qa = read_to_grid(f["assets"]["qa_pixel"]["href"] + "?" + tok, T30, S30, dtype="uint16")
    bad = ((qa >> 1) & 1) | ((qa >> 2) & 1) | ((qa >> 3) & 1) | ((qa >> 4) & 1)
    cc = st * 0.00341802 + 149.0 - 273.15; cc[(st == 0) | (bad == 1)] = np.nan; cc[(cc < 10) | (cc > 70)] = np.nan
    lst_list.append(cc); meta.append((f["id"], f["properties"]["datetime"][:10], f["properties"]["platform"]))
lst = np.nanmedian(np.stack(lst_list), axis=0)
# per-date ward means
rows = []
for (sid, sdate, plat), arr in zip(meta, lst_list):
    ok = (I30 > 0) & ~np.isnan(arr)
    s_ = np.bincount(I30[ok], weights=arr[ok], minlength=len(wards) + 1); n_ = np.bincount(I30[ok], minlength=len(wards) + 1)
    for i, wn in enumerate(wards.ward_no): rows.append({"Ward_ID": int(wn), "Scene_ID": sid, "Scene_Date": sdate, "Platform": plat.replace("landsat-", "Landsat "), "LST_Mean_C": round(float(s_[i + 1] / max(n_[i + 1], 1)), 2), "Valid_Pixels": int(n_[i + 1])})
pd.DataFrame(rows).to_csv("build/tables/ward_lst_by_date.csv", index=False)

# ---------------- Sentinel-2 NDVI ----------------
d2 = post("https://earth-search.aws.element84.com/v1/search", {"collections": ["sentinel-2-l2a"], "ids": ["S2B_43QBB_20260411_0_L2A", "S2A_43QBB_20260408_1_L2A"]})
nd = []
for f in d2["features"]:
    red = read_to_grid(f["assets"]["red"]["href"], T10, S10); nir = read_to_grid(f["assets"]["nir"]["href"], T10, S10)
    scl = read_to_grid(f["assets"]["scl"]["href"], T10, S10, dtype="uint8") if "scl" in f["assets"] else np.zeros(S10, "uint8")
    r, n = red / 10000.0, nir / 10000.0; v = (n - r) / np.maximum(n + r, 1e-6); v[(red == 0) | np.isin(scl, [3, 8, 9, 10])] = np.nan; nd.append(v)
ndvi = np.nanmedian(np.stack(nd), axis=0)

# ---------------- WorldCover, SRTM, water distance ----------------
lc = read_to_grid("https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N18E072_Map.tif", T10, S10, dtype="uint8")
srcs = []
for la in range(math.floor(bb4326[1]), math.floor(bb4326[3]) + 1):
    for lo in range(math.floor(bb4326[0]), math.floor(bb4326[2]) + 1):
        t = f"N{la:02d}E{lo:03d}"; p = f"data/{t}.hgt"
        if not os.path.exists(p):
            urllib.request.urlretrieve(f"https://s3.amazonaws.com/elevation-tiles-prod/skadi/{t[:3]}/{t}.hgt.gz", p + ".gz")
            with gzip.open(p + ".gz") as g, open(p, "wb") as o: o.write(g.read())
        srcs.append(rasterio.open(p))
marr, mtf = merge(srcs)
elev = np.zeros(S30, "float32"); reproject(marr[0].astype("float32"), elev, src_transform=mtf, src_crs="EPSG:4326", dst_transform=T30, dst_crs=CRS, resampling=Resampling.bilinear)
gy, gx = np.gradient(elev, 30.0, 30.0); slope = np.hypot(gx, gy) * 100.0
dist = distance_transform_edt(~np.isin(lc, [80, 95]), sampling=10.0).astype("float32")

# ---------------- ward statistics (same method as the prototype) ----------------
def zmean(arr, idx, n=len(wards)):
    ok = (idx > 0) & ~np.isnan(arr); s = np.bincount(idx[ok], weights=arr[ok], minlength=n + 1); c = np.bincount(idx[ok], minlength=n + 1); return s[1:] / np.maximum(c[1:], 1), c[1:]
def zshare(mask, idx, n=len(wards)):
    ok = idx > 0; a = np.bincount(idx[ok], weights=mask[ok].astype(float), minlength=n + 1); c = np.bincount(idx[ok], minlength=n + 1); return a[1:] / np.maximum(c[1:], 1) * 100
df = wards[["ward_no"]].copy(); df["area_km2"] = wards.geometry.area / 1e6
df["lst_c"], df["lst_px"] = zmean(lst, I30); df["ndvi"], _ = zmean(ndvi, I10)
df["builtup_pct"] = zshare(lc == 50, I10); df["green_pct"] = zshare(np.isin(lc, [10, 20, 30, 95]), I10); df["water_pct"] = zshare(np.isin(lc, [80, 95, 90]), I10)
df["elev_m"], _ = zmean(elev, I30); df["slope_pct"], _ = zmean(slope, I30); df["dist_water_m"], _ = zmean(dist, I10)
def to15(x, inv=False):
    x = np.asarray(x, float); lo, hi = np.nanmin(x), np.nanmax(x); s = 1 + 4 * (x - lo) / (hi - lo); return 6 - s if inv else s
df["heat"] = to15(df.lst_c); df["green_def"] = to15(df.ndvi, inv=True)
def bins(x, edges, sc): return np.select([x <= e for e in edges], sc[:-1], sc[-1]).astype(float)
f_elev = bins(df.elev_m, [5, 10, 20, 50], [5, 4, 3, 2, 1]); f_slope = bins(df.slope_pct, [2, 5, 10, 20], [5, 4, 3, 2, 1]); f_dist = bins(df.dist_water_m, [250, 500, 1000, 2000], [5, 4, 3, 2, 1])
f_bu = np.select([df.builtup_pct >= 60, df.builtup_pct >= 40, df.builtup_pct >= 20, df.builtup_pct >= 10], [5, 4, 3, 2], 1).astype(float)
A = np.array([[1, 2, 2, 3], [1 / 2, 1, 1 / 2, 1], [1 / 2, 2, 1, 2], [1 / 3, 1, 1 / 2, 1]]); w_, v_ = np.linalg.eig(A); i_ = np.argmax(w_.real); aw = np.abs(v_[:, i_].real); aw /= aw.sum()
df["flood"] = aw[0] * f_elev + aw[1] * f_slope + aw[2] * f_dist + aw[3] * f_bu; df["ucsi"] = (df.heat + df.green_def + df.flood) / 3
df["f_elev"], df["f_slope"], df["f_dist"], df["f_bu"] = f_elev, f_slope, f_dist, f_bu
q = np.quantile(df.ucsi, [.2, .4, .6, .8]); df["ucls"] = np.digitize(df.ucsi, q)
df["rank"] = df.ucsi.rank(ascending=False, method="min").astype(int)
old = pd.read_csv("out/ward_stats.csv")
chk = {c: float(np.abs(old[c].values - df[c].values).max()) for c in ["lst_c", "ndvi", "builtup_pct", "flood", "ucsi"]}
print("max abs difference vs prototype:", chk)
df.to_csv("build/tables/ward_stats_full.csv", index=False)
json.dump({"q_ucsi": q.tolist(), "ahp": aw.tolist(), "lst_lo_hi": [float(df.lst_c.min()), float(df.lst_c.max())], "ndvi_lo_hi": [float(df.ndvi.min()), float(df.ndvi.max())], "scenes": meta}, open("build/tables/params.json", "w"))

# ---------------- rasters to GeoTIFF (clipped to the study area) ----------------
m30, m10 = I30 > 0, I10 > 0
ndvi30 = np.nanmean(ndvi[: S30[0] * 3, : S30[1] * 3].reshape(S30[0], 3, S30[1], 3), axis=(1, 3)) if ndvi.shape[0] >= S30[0] * 3 else None
lo, hi = df.lst_c.min(), df.lst_c.max(); nlo, nhi = df.ndvi.min(), df.ndvi.max()
heat_r = np.clip(1 + 4 * (lst - lo) / (hi - lo), 1, 5); green_r = np.clip(6 - (1 + 4 * (ndvi - nlo) / (nhi - nlo)), 1, 5)
write_tif("LST_Apr2026_C", lst, T30, "float32", -9999, m30); write_tif("NDVI_Apr2026", ndvi, T10, "float32", -9999, m10)
write_tif("LandCover_WorldCover2021", lc, T10, "uint8", 0, m10); write_tif("Elevation_SRTM_m", elev, T30, "float32", -9999, m30)
write_tif("Slope_SRTM_pct", slope, T30, "float32", -9999, m30); write_tif("Distance_to_Water_m", dist, T10, "float32", -9999, m10)
write_tif("HeatScore_1to5", heat_r, T30, "float32", -9999, m30); write_tif("GreenDeficit_1to5", green_r, T10, "float32", -9999, m10)
write_tif("BuiltUp_WorldCover2021", (lc == 50).astype("uint8"), T10, "uint8", 255, m10)

# ---------------- raster-derived vectors ----------------
def polys(mask, T, min_area, simplify=0):
    lab, n = label(mask, structure=np.ones((3, 3)))
    out = []
    for geom, val in shapes(lab.astype("int32"), mask=mask, transform=T, connectivity=8):
        g = shape(geom)
        if g.area >= min_area: out.append((int(val), g.simplify(simplify) if simplify else g))
    return out
water = []
for cls, nm in ((80, "Water"), (95, "Mangrove"), (90, "Wetland")):
    for _, g in polys((lc == cls) & m10, T10, 5000, 4): water.append({"Water_Type": nm, "geometry": g})
wg = gpd.GeoDataFrame(water, crs=CRS); wg["Area_ha"] = wg.geometry.area / 1e4; wg = wg.sort_values("Area_ha", ascending=False).reset_index(drop=True); wg["Water_ID"] = wg.index + 1
wg.to_file("build/vectors/water_bodies.geojson", driver="GeoJSON"); print("water polygons", len(wg), "area km2", round(wg.Area_ha.sum() / 100, 1))
ov = m30 & (lst >= 45) & (ndvi30 < 0.2)
hz = []
lab, n = label(ov, structure=np.ones((3, 3)))
for geom, val in shapes(lab.astype("int32"), mask=ov, transform=T30, connectivity=8):
    g = shape(geom)
    if g.area >= 20000:
        sel = lab == val; hz.append({"Mean_LST_C": round(float(np.nanmean(lst[sel])), 2), "Mean_NDVI": round(float(np.nanmean(ndvi30[sel])), 3), "geometry": g.simplify(10)})
hg = gpd.GeoDataFrame(hz, crs=CRS); hg["Area_ha"] = hg.geometry.area / 1e4; hg = hg.sort_values("Area_ha", ascending=False).reset_index(drop=True); hg["Zone_ID"] = hg.index + 1
hg.to_file("build/vectors/hot_lowgreen_zones.geojson", driver="GeoJSON"); print("hot low-green zones", len(hg), "area km2", round(hg.Area_ha.sum() / 100, 1), "| all-pixel overlay km2", round(ov.sum() * 900 / 1e6, 1))
print("done rasters/tables/vectors")
