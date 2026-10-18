# Check that the Field Calculator formulas written in the report reproduce the stored ward values (run with QGIS Python).
import sys
sys.path.append("C:/Program Files/QGIS 4.2.0/apps/qgis/python/plugins")
from qgis.core import *
QgsApplication.setPrefixPath("C:/Program Files/QGIS 4.2.0/apps/qgis", True)
app = QgsApplication([], False); app.initQgis()
G = "G:/1 Programming/College/GIS-CA3-Hasnat/CA4_Project/data/NaviMumbai_UCSI.gpkg"
w = QgsVectorLayer(G + "|layername=wards", "wards", "ogr"); assert w.isValid()
TESTS = {
 "Heat_Score": ('1 + 4 * ("LST_C" - minimum("LST_C")) / (maximum("LST_C") - minimum("LST_C"))', 0.011),
 "GreenDef_Score": ('5 - 4 * ("NDVI" - minimum("NDVI")) / (maximum("NDVI") - minimum("NDVI"))', 0.011),
 "Flood_Score": ('0.42486 * "F_Elev" + 0.16129 * "F_Slope" + 0.27007 * "F_Water" + 0.14378 * "F_BuiltUp"', 0.011),
 "UCSI": ('("Heat_Score" + "GreenDef_Score" + "Flood_Score") / 3', 0.011),
 "F_Elev": ('CASE WHEN "Elev_m" <= 5 THEN 5 WHEN "Elev_m" <= 10 THEN 4 WHEN "Elev_m" <= 20 THEN 3 WHEN "Elev_m" <= 50 THEN 2 ELSE 1 END', None),
 "F_Slope": ('CASE WHEN "Slope_Pct" <= 2 THEN 5 WHEN "Slope_Pct" <= 5 THEN 4 WHEN "Slope_Pct" <= 10 THEN 3 WHEN "Slope_Pct" <= 20 THEN 2 ELSE 1 END', None),
 "F_Water": ('CASE WHEN "DistWater_m" <= 250 THEN 5 WHEN "DistWater_m" <= 500 THEN 4 WHEN "DistWater_m" <= 1000 THEN 3 WHEN "DistWater_m" <= 2000 THEN 2 ELSE 1 END', None),
 "F_BuiltUp": ('CASE WHEN "BuiltUp_Pct" >= 60 THEN 5 WHEN "BuiltUp_Pct" >= 40 THEN 4 WHEN "BuiltUp_Pct" >= 20 THEN 3 WHEN "BuiltUp_Pct" >= 10 THEN 2 ELSE 1 END', None),
 "UCSI_Class": ("CASE WHEN \"UCSI_Rank\" <= 23 THEN 'Highest' WHEN \"UCSI_Rank\" <= 45 THEN 'High' WHEN \"UCSI_Rank\" <= 67 THEN 'Medium' WHEN \"UCSI_Rank\" <= 89 THEN 'Low' ELSE 'Lowest' END", None),
}
ctx = QgsExpressionContext(); ctx.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(w))
for fld, (expr, tol) in TESTS.items():
    e = QgsExpression(expr); e.prepare(ctx); worst = 0; bad = 0
    for f in w.getFeatures():
        ctx.setFeature(f); v = e.evaluate(ctx)
        if e.hasEvalError(): print(fld, "EVAL ERROR:", e.evalErrorString()); break
        if tol is None: bad += (v != f[fld])
        else:
            d = abs(float(v) - float(f[fld])); worst = max(worst, d); bad += (d > tol)
    print(f"{fld:15s} mismatches: {bad:3d}   worst abs diff: {worst:.4f}")
app.exitQgis()
