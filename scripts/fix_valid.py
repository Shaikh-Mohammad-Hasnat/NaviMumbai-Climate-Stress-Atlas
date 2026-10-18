# Check geometry validity in every spatial layer of the GeoPackage and repair with MakeValid (in place).
from osgeo import ogr
ogr.UseExceptions()
ds = ogr.Open("G:/1 Programming/College/GIS-CA3-Hasnat/CA4_Project/data/NaviMumbai_UCSI.gpkg", 1)
for i in range(ds.GetLayerCount()):
    lyr = ds.GetLayer(i)
    if lyr.GetGeomType() == ogr.wkbNone: continue
    bad = 0; fixed = 0
    lyr.ResetReading()
    feats = [f for f in lyr]
    for f in feats:
        g = f.GetGeometryRef()
        if g is not None and not g.IsValid():
            bad += 1
            ng = g.MakeValid()
            # keep the original geometry type (MakeValid can return a collection)
            if ng is not None and ng.GetGeometryType() in (ogr.wkbGeometryCollection,):
                keep = ogr.Geometry(lyr.GetGeomType())
                for k in range(ng.GetGeometryCount()):
                    p = ng.GetGeometryRef(k)
                    if ogr.GT_Flatten(p.GetGeometryType()) in (ogr.wkbPolygon, ogr.wkbMultiPolygon):
                        keep.AddGeometry(p.Clone()) if ogr.GT_Flatten(p.GetGeometryType()) == ogr.wkbPolygon else [keep.AddGeometry(p.GetGeometryRef(j).Clone()) for j in range(p.GetGeometryCount())]
                ng = keep
            ng = ogr.ForceTo(ng, lyr.GetGeomType())
            f.SetGeometry(ng); lyr.SetFeature(f); fixed += 1
    print(lyr.GetName(), "features", len(feats), "invalid", bad, "repaired", fixed)
ds = None
