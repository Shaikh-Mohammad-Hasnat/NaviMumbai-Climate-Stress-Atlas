# Build the QGIS project (.qgz), styled layers, saved query results, map layouts and PNG exports. Run with QGIS 4.2 Python (normal Windows Qt platform, not offscreen: offscreen has no fonts).
import sys, os, json, csv
sys.path.append("C:/Program Files/QGIS 4.2.0/apps/qgis/python/plugins")
from qgis.core import *
from qgis.analysis import QgsNativeAlgorithms
from qgis.PyQt.QtCore import Qt, QRectF
from qgis.PyQt.QtGui import QColor, QFont
QgsApplication.setPrefixPath("C:/Program Files/QGIS 4.2.0/apps/qgis", True)
app = QgsApplication([], False); app.initQgis()
import processing
from processing.core.Processing import Processing
Processing.initialize(); QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

SCR = "C:/Users/farha/AppData/Local/Temp/claude/G--5-Claude-Chats-college/081d4375-70ed-43ee-a64d-1d2d6cb50bb2/scratchpad/hasnat/"
PROJ = "G:/1 Programming/College/GIS-CA3-Hasnat/CA4_Project/"
GPKG = PROJ + "data/NaviMumbai_UCSI.gpkg"; QGPKG = PROJ + "data/NaviMumbai_query_results.gpkg"; RAS = PROJ + "data/rasters/"
os.makedirs(PROJ + "maps", exist_ok=True); os.makedirs(PROJ + "queries", exist_ok=True)
U = Qgis.LayoutUnit.Millimeters
proj = QgsProject.instance(); proj.clear()
proj.setCrs(QgsCoordinateReferenceSystem("EPSG:32643")); proj.setTitle("Urban Climate Stress Mapping of Navi Mumbai (UCSI)")
proj.setFilePathStorage(Qgis.FilePathType.Relative)
md = QgsProjectMetadata(); md.setTitle("Urban Climate Stress Mapping of Navi Mumbai"); md.setAuthor("Hasnat Shaikh (Roll 2405003), MGM University")
md.setAbstract("Ward-level Urban Climate Stress Index (UCSI) for 111 Navi Mumbai wards from heat (Landsat 8/9), green-cover deficit (Sentinel-2 NDVI) and flood susceptibility (SRTM, WorldCover, AHP weights). GIS CA4, April 2026 imagery.")
md.setCreationDateTime(__import__("qgis.PyQt.QtCore", fromlist=["QDateTime"]).QDateTime.currentDateTime()); proj.setMetadata(md)
NAVY, HEAT, GREEN, BLUE, GREY = "#0F172A", "#EA580C", "#16A34A", "#2563EB", "#6B7280"

# ------------------------------------------------------------------ helpers
def vl(name, disp, subset=None, path=None):
    l = QgsVectorLayer(f"{path or GPKG}|layername={name}", disp, "ogr"); assert l.isValid(), name
    if subset: l.setSubsetString(subset)
    return l
def rl(fn, disp):
    l = QgsRasterLayer(RAS + fn, disp); assert l.isValid(), fn; return l
def fill(color, outline="#6B7280", w="0.15", alpha=None):
    c = QColor(color)
    if alpha is not None: c.setAlpha(alpha)
    return QgsFillSymbol.createSimple({"color": c.name(QColor.NameFormat.HexArgb), "outline_color": outline, "outline_width": w, "outline_style": "solid" if outline else "no"})
def marker(color, name="circle", size="2.2", outline="#FFFFFF", ow="0.25"):
    return QgsMarkerSymbol.createSimple({"name": name, "color": color, "size": size, "outline_color": outline, "outline_width": ow})
def line(color, w):
    return QgsLineSymbol.createSimple({"color": color, "line_width": str(w), "capstyle": "round", "joinstyle": "round"})
def ramp_items(stops): return [QgsColorRampShader.ColorRampItem(v, QColor(c), lab if lab else str(v)) for v, c, lab in stops]
def pseudo(layer, stops, mn, mx, labs=None):
    sh = QgsColorRampShader(mn, mx); sh.setColorRampType(QgsColorRampShader.Type.Interpolated); sh.setColorRampItemList(ramp_items(stops))
    if labs:
        st = QgsColorRampLegendNodeSettings(); st.setMaximumLabel(labs[0]); st.setMinimumLabel(labs[1]); sh.setLegendSettings(st)
    rs = QgsRasterShader(); rs.setRasterShaderFunction(sh)
    layer.setRenderer(QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, rs)); layer.triggerRepaint()
def paletted(layer, classes):
    cl = [QgsPalettedRasterRenderer.Class(v, QColor(c), lab) for v, c, lab in classes]
    layer.setRenderer(QgsPalettedRasterRenderer(layer.dataProvider(), 1, cl)); layer.triggerRepaint()
def text_fmt(size, color="#111827", bold=False, font="Calibri", buffer=True):
    f = QgsTextFormat(); qf = QFont(font, int(size)); qf.setBold(bold); f.setFont(qf); f.setSize(size); f.setColor(QColor(color))
    if buffer:
        b = QgsTextBufferSettings(); b.setEnabled(True); b.setSize(0.5); b.setColor(QColor("#FFFFFF")); f.setBuffer(b)
    return f
def label_layer(layer, field, size=6.0, expr=False, all_labels=False):
    s = QgsPalLayerSettings(); s.fieldName = field; s.isExpression = expr; s.setFormat(text_fmt(size, bold=True))
    if all_labels:
        try: ps = s.placementSettings(); ps.setOverlapHandling(Qgis.LabelOverlapHandling.AllowOverlapIfRequired); s.setPlacementSettings(ps)
        except Exception as e: print("overlap handling:", e)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(s)); layer.setLabelsEnabled(True)
def jenks_graduated(layer, field, colors):
    cm = QgsClassificationJenks(); cm.setLabelPrecision(2)
    r = QgsGraduatedSymbolRenderer(field); r.setClassificationMethod(cm); r.updateClasses(layer, 5)
    for i in range(len(r.ranges())): r.updateRangeSymbol(i, fill(colors[i]))
    layer.setRenderer(r)

ucsi_colors = ["#FFF6DC", "#FDD49E", "#FC8D59", "#D7301F", "#7F0000"]
green_colors = ["#F6F1E7", "#E5D3B3", "#C9A66B", "#9A6B2F", "#5C3A12"]
flood_colors = ["#EFF6FF", "#BFDBFE", "#60A5FA", "#2563EB", "#1E3A8A"]

# ------------------------------------------------------------------ layers
L = {}
L["boundary"] = vl("study_boundary", "Study boundary"); L["boundary"].setRenderer(QgsSingleSymbolRenderer(fill("#00000000", "#111827", "0.6", 0)))
L["wards"] = vl("wards", "Wards (111) with ward numbers"); L["wards"].setRenderer(QgsSingleSymbolRenderer(fill("#FFFFFF", "#374151", "0.15", 0))); label_layer(L["wards"], "Ward_ID", 6)
L["w_ucsi"] = vl("wards", "UCSI class (final result)")
L["w_ucsi"].setRenderer(QgsCategorizedSymbolRenderer("UCSI_Class", [QgsRendererCategory(v, fill(c, "#6B7280", "0.15"), f"{v}") for v, c in zip(["Highest", "High", "Medium", "Low", "Lowest"], ucsi_colors[::-1])]))
label_layer(L["w_ucsi"], 'CASE WHEN "UCSI_Rank" <= 10 THEN to_string("Ward_ID") END', 7.5, expr=True, all_labels=True)
L["w_flood"] = vl("wards", "Flood susceptibility score (1-5)"); jenks_graduated(L["w_flood"], "Flood_Score", flood_colors)
L["w_green"] = vl("wards", "Green-cover deficit score (1-5)"); jenks_graduated(L["w_green"], "GreenDef_Score", green_colors)
L["w_heat"] = vl("wards", "Heat stress score (1-5)"); jenks_graduated(L["w_heat"], "Heat_Score", ucsi_colors)
L["w_light"] = vl("wards", "Wards (light base)"); L["w_light"].setRenderer(QgsSingleSymbolRenderer(fill("#F1F5F9", "#94A3B8", "0.15")))
L["roads"] = vl("major_roads", "Major roads (OSM)")
root = QgsRuleBasedRenderer.Rule(None); rr = QgsRuleBasedRenderer(root)
for expr, col, w, lab in [('"Flooded_2025" = \'Yes\'', BLUE, 0.7, "Waterlogged 26 May 2025"), ('"Road_Type" IN (\'motorway\',\'trunk\')', "#374151", 0.55, "Motorway / trunk"), ('"Road_Type" = \'primary\'', "#6B7280", 0.4, "Primary"), ('"Road_Type" = \'secondary\'', "#9CA3AF", 0.22, "Secondary")]:
    root.appendChild(QgsRuleBasedRenderer.Rule(line(col, w), 0, 0, expr, lab))
L["roads"].setRenderer(rr)
L["water"] = vl("water_bodies", "Water and mangrove (WorldCover)")
L["water"].setRenderer(QgsCategorizedSymbolRenderer("Water_Type", [QgsRendererCategory("Water", fill("#7FB8DA", "#4B93B8", "0.1"), "Water"), QgsRendererCategory("Mangrove", fill("#4E9F50", "#2F7A3A", "0.1"), "Mangrove"), QgsRendererCategory("Wetland", fill("#A7D3C2", "#6FB3A0", "0.1"), "Wetland")]))
L["hosp"] = vl("hospitals", "Hospitals and clinics (OSM)"); L["hosp"].setRenderer(QgsSingleSymbolRenderer(marker("#111827", "circle", "1.8", "#FFFFFF", "0.25")))
L["flood"] = vl("flood_reports", "Flood reports, 26 May 2025")
L["flood"].setRenderer(QgsCategorizedSymbolRenderer("Report_Type", [QgsRendererCategory("Rainfall record", marker("#FACC15", "circle", "4.2", "#111827", "0.4"), "Rain record"), QgsRendererCategory("Waterlogged site", marker("#F97316", "triangle", "4.8", "#111827", "0.4"), "Waterlogged site")]))
ls = QgsPalLayerSettings(); ls.fieldName = "CASE WHEN \"Rain_mm\" IS NULL THEN \"Site\" ELSE \"Site\" || ': ' || to_string(\"Rain_mm\") || ' mm' END"; ls.isExpression = True; ls.setFormat(text_fmt(8, "#111827", True, buffer=True)); ls.placement = Qgis.LabelPlacement.AroundPoint
L["flood"].setLabeling(QgsVectorLayerSimpleLabeling(ls)); L["flood"].setLabelsEnabled(True)
L["hot"] = vl("hot_lowgreen_zones", "Hot and low-green patches"); L["hot"].setRenderer(QgsSingleSymbolRenderer(fill("#B91C1C", "#7F1D1D", "0.15", 130)))
L["tab"] = vl("ward_lst_by_date", "ward_lst_by_date (table)")
heat_stops = [(32, "#FFF4D6", "32"), (36, "#FDD28A", "36"), (40, "#F59E42", "40"), (44, "#DC5A2B", "44"), (48, "#8E1B1F", "48")]
L["lst"] = rl("LST_Apr2026_C.tif", "Land surface temperature, April 2026 (C)"); pseudo(L["lst"], heat_stops, 32, 48, ("48 °C (hot)", "32 °C or less (cool)"))
L["ndvi"] = rl("NDVI_Apr2026.tif", "NDVI, April 2026"); pseudo(L["ndvi"], [(0, "#D8C9A3", "0.0"), (0.2, "#EAE7B0", "0.2"), (0.35, "#AAD38C", "0.35"), (0.5, "#4E9F50", "0.5"), (0.7, "#1B6B3A", "0.7")], 0, 0.7, ("0.7 or more (dense plants)", "0 or less (bare / built-up)"))
L["lc"] = rl("LandCover_WorldCover2021.tif", "Land cover, ESA WorldCover 2021")
paletted(L["lc"], [(10, "#006400", "Tree cover"), (20, "#FFBB22", "Shrubland"), (30, "#FFFF4C", "Grassland"), (40, "#F096FF", "Cropland"), (50, "#FA0000", "Built-up"), (60, "#B4B4B4", "Bare / sparse"), (80, "#0064C8", "Water"), (90, "#0096A0", "Wetland"), (95, "#00CF75", "Mangrove")])
L["bu"] = rl("BuiltUp_WorldCover2021.tif", "Built-up (WorldCover 2021)"); paletted(L["bu"], [(1, "#B91C1C", "Built-up")])
L["elev"] = rl("Elevation_SRTM_m.tif", "Elevation, SRTM (m)"); pseudo(L["elev"], [(0, "#DDEBD5", "0 m"), (8, "#E9E3B5", "8"), (25, "#E2C58A", "25"), (70, "#CF9A62", "70"), (200, "#A9683A", "200 m")], 0, 200, ("200 m or more", "0 m or less"))
L["slope"] = rl("Slope_SRTM_pct.tif", "Slope (%)"); pseudo(L["slope"], [(0, "#F1F5F9", "0"), (5, "#CBD5E1", "5"), (15, "#94A3B8", "15"), (40, "#475569", "40")], 0, 40, ("40 % or more", "0 % (flat)"))
L["dist"] = rl("Distance_to_Water_m.tif", "Distance to water / mangrove (m)"); pseudo(L["dist"], [(0, "#2563EB", "0 m"), (250, "#93C5FD", "250"), (1000, "#EFF6FF", "1000"), (3000, "#FFFFFF", "3000 m")], 0, 3000, ("3000 m or more", "0 m (at water)"))
L["heatr"] = rl("HeatScore_1to5.tif", "Heat score raster (1-5)"); pseudo(L["heatr"], [(1, "#FFF4D6", "1"), (2, "#FDD28A", "2"), (3, "#F59E42", "3"), (4, "#DC5A2B", "4"), (5, "#8E1B1F", "5")], 1, 5, ("5 (hottest)", "1 (coolest)"))
L["greenr"] = rl("GreenDeficit_1to5.tif", "Green-cover deficit raster (1-5)"); pseudo(L["greenr"], [(1, "#F6F1E7", "1"), (2, "#E5D3B3", "2"), (3, "#C9A66B", "3"), (4, "#9A6B2F", "4"), (5, "#5C3A12", "5")], 1, 5, ("5 (least plants)", "1 (most plants)"))
L["base"] = QgsRasterLayer("type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}&zmax=19&zmin=0&crs=EPSG3857", "BASEMAP_DISPLAY_ONLY (Esri World Imagery, not analysis data)", "wms")
# helper layers used only by the query layouts (kept in the project, not in the layer tree)
H = {}
H["water_big"] = vl("water_bodies", "helper: water >= 1 ha", '"Area_ha" >= 1'); H["water_big"].setRenderer(QgsSingleSymbolRenderer(fill("#3B82F6", "#1D4ED8", "0.1", 200)))
H["roads_major"] = vl("major_roads", "helper: motorway/trunk/primary", '"Road_Type" IN (\'motorway\',\'trunk\',\'primary\')'); H["roads_major"].setRenderer(QgsSingleSymbolRenderer(line("#1D4ED8", 0.45)))
H["hosp_ctx"] = vl("hospitals", "helper: all hospitals"); H["hosp_ctx"].setRenderer(QgsSingleSymbolRenderer(marker("#6B7280", "circle", "1.6", "#FFFFFF", "0.15")))
H["site"] = vl("flood_reports", "helper: waterlogged site", '"Report_Type" = \'Waterlogged site\''); H["site"].setRenderer(QgsSingleSymbolRenderer(marker("#1D4ED8", "triangle", "4.2", "#FFFFFF", "0.3")))

# layer tree
rootg = proj.layerTreeRoot()
groups = [("1  RESULTS (wards)", ["w_ucsi", "w_flood", "w_green", "w_heat"]), ("2  ANALYSIS LAYERS", ["flood", "hosp", "hot", "roads", "water"]),
          ("3  BOUNDARIES", ["wards", "boundary"]), ("4  REMOTE SENSING RASTERS", ["heatr", "greenr", "lst", "ndvi", "lc", "bu", "elev", "slope", "dist"]),
          ("5  TABLES", ["tab"]), ("6  REFERENCE", ["base"])]
for g, keys in groups:
    grp = rootg.addGroup(g)
    for k in keys:
        proj.addMapLayer(L[k], False); node = grp.addLayer(L[k]); node.setItemVisibilityChecked(k in ("w_ucsi", "wards", "boundary"))
for lyr in [L["w_light"]] + list(H.values()): proj.addMapLayer(lyr, False)
for rid, nm, ref, refing in [("rel_ward_lst", "Ward - LST by date", "wards", "tab"), ("rel_ward_hosp", "Ward - hospitals", "wards", "hosp")]:
    rel = QgsRelation(); rel.setId(rid); rel.setName(nm); rel.setReferencedLayer(L[ref].id()); rel.setReferencingLayer(L[refing].id()); rel.addFieldPair("Ward_ID", "Ward_ID"); assert rel.isValid(), rid
    proj.relationManager().addRelation(rel)
bb = L["boundary"].extent(); bm = proj.bookmarkManager()
def addbm(name, x0, y0, x1, y1):
    b = QgsBookmark(); b.setName(name); b.setExtent(QgsReferencedRectangle(QgsRectangle(x0, y0, x1, y1), proj.crs())); bm.addBookmark(b)
ym, yM = bb.yMinimum(), bb.yMaximum(); span = yM - ym
addbm("Whole study area", bb.xMinimum() - 300, ym - 300, bb.xMaximum() + 300, yM + 300)
addbm("North (wards 1 to about 37)", bb.xMinimum() - 300, ym + span * 0.66, bb.xMaximum() + 300, yM + 300)
addbm("Centre", bb.xMinimum() - 300, ym + span * 0.33, bb.xMaximum() + 300, ym + span * 0.67)
addbm("South (wards about 75 to 111)", bb.xMinimum() - 300, ym - 300, bb.xMaximum() + 300, ym + span * 0.34)
proj.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(QgsRectangle(bb.xMinimum() - 500, ym - 500, bb.xMaximum() + 500, yM + 500), proj.crs()))
def theme(name, keys):
    rec = QgsMapThemeCollection.MapThemeRecord(); recs = []
    for k in keys:
        lr = QgsMapThemeCollection.MapThemeLayerRecord(L[k]); lr.usingCurrentStyle = True; lr.currentStyle = L[k].styleManager().currentStyle(); lr.isVisible = True; recs.append(lr)
    rec.setLayerRecords(recs); proj.mapThemeCollection().insert(name, rec)
theme("1 Study area and wards", ["wards", "boundary", "water", "roads"]); theme("2 Land cover", ["boundary", "wards", "lc"]); theme("3 Green cover (NDVI)", ["boundary", "wards", "ndvi"])
theme("4 Heat (LST)", ["boundary", "wards", "lst"]); theme("5 Elevation", ["boundary", "wards", "elev"]); theme("6 Flood susceptibility", ["boundary", "w_flood", "flood"])
theme("7 Heat stress score", ["boundary", "w_heat"]); theme("8 Green-cover deficit", ["boundary", "w_green"]); theme("9 UCSI (final result)", ["boundary", "w_ucsi", "hosp"]); theme("10 Hot and low-green patches", ["boundary", "wards", "hot"])

# ------------------------------------------------------------------ layout helpers
ext0 = L["boundary"].extent()
def frame_extent(w_mm, h_mm, margin=600):
    cx, cy = (ext0.xMinimum() + ext0.xMaximum()) / 2, (ext0.yMinimum() + ext0.yMaximum()) / 2
    h = ext0.height() + 2 * margin; w = h * w_mm / h_mm
    if w < ext0.width() + 2 * margin: w = ext0.width() + 2 * margin; h = w * h_mm / w_mm
    return QgsRectangle(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
def txt_item(layout, text, x, y, w, h, size=10, bold=False, color="#0F172A", font="Calibri", italic=False):
    it = QgsLayoutItemLabel(layout); it.setText(text)
    f = QgsTextFormat(); qf = QFont(font, int(size)); qf.setBold(bold); qf.setItalic(italic); f.setFont(qf); f.setSize(size); f.setColor(QColor(color)); it.setTextFormat(f)
    it.setHAlign(Qt.AlignmentFlag.AlignLeft); it.setVAlign(Qt.AlignmentFlag.AlignTop); it.setBackgroundEnabled(False)
    it.attemptMove(QgsLayoutPoint(x, y, U)); it.attemptResize(QgsLayoutSize(w, h, U)); layout.addLayoutItem(it); return it
def rect_item(layout, x, y, w, h, color, outline=None):
    sh = QgsLayoutItemShape(layout); sh.setShapeType(QgsLayoutItemShape.Shape.Rectangle)
    sh.setSymbol(QgsFillSymbol.createSimple({"color": color, "outline_style": "solid" if outline else "no", "outline_color": outline or "#000000", "outline_width": "0.2"}))
    sh.attemptMove(QgsLayoutPoint(x, y, U)); sh.attemptResize(QgsLayoutSize(w, h, U)); layout.addLayoutItem(sh); return sh
def new_layout(name):
    old = proj.layoutManager().layoutByName(name)
    if old: proj.layoutManager().removeLayout(old)
    lay = QgsPrintLayout(proj); lay.initializeDefaults(); lay.setName(name); lay.pageCollection().page(0).setPageSize("A4", QgsLayoutItemPage.Orientation.Portrait)
    proj.layoutManager().addLayout(lay); return lay
def add_map(lay, layers, x, y, w, h, extent):
    m = QgsLayoutItemMap(lay); m.attemptMove(QgsLayoutPoint(x, y, U)); m.attemptResize(QgsLayoutSize(w, h, U)); m.setCrs(proj.crs()); m.setLayers(layers); m.setKeepLayerSet(True)
    m.setExtent(extent); m.setFrameEnabled(True); m.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, U)); m.setBackgroundColor(QColor("#FFFFFF")); lay.addLayoutItem(m); return m
def add_legend(lay, m, layers, x, y, names=None):
    lg = QgsLayoutItemLegend(lay); lg.setLinkedMap(m); lg.setAutoUpdateModel(False); lg.setTitle("Legend")
    rt = lg.model().rootGroup(); rt.clear()
    for i, l in enumerate(layers):
        n = rt.addLayer(l)
        if names and names[i]: n.setUseLayerName(False); n.setName(names[i])
        if isinstance(l, QgsRasterLayer):
            lg.model().refreshLayerLegend(n); nodes = lg.model().layerLegendNodes(n)
            keep = [k for k, nd in enumerate(nodes) if "Band" not in str(nd.data(Qt.ItemDataRole.DisplayRole))]
            QgsMapLayerLegendUtils.setLegendNodeOrder(n, keep); lg.model().refreshLayerLegend(n)
    try:
        LC = getattr(Qgis, "LegendComponent", None) or QgsLegendStyle.Style
        for comp, sz, b in [("Title", 12, True), ("Subgroup", 9.5, True), ("SymbolLabel", 8.5, False)]:
            lg.rstyle(getattr(LC, comp)).setTextFormat(text_fmt(sz, "#0F172A", b, buffer=False))
    except Exception as e: print("legend fonts:", e)
    lg.setBoxSpace(2); lg.attemptMove(QgsLayoutPoint(x, y, U)); lay.addLayoutItem(lg); return lg
def add_north_scale(lay, m, nx, ny, sx, sy):
    n = QgsLayoutItemPicture(lay); n.setPicturePath(":/images/north_arrows/layout_default_north_arrow.svg"); n.attemptMove(QgsLayoutPoint(nx, ny, U)); n.attemptResize(QgsLayoutSize(14, 14, U)); lay.addLayoutItem(n)
    sb = QgsLayoutItemScaleBar(lay); sb.setStyle("Single Box"); sb.setLinkedMap(m); sb.setUnits(Qgis.DistanceUnit.Kilometers); sb.setNumberOfSegments(2); sb.setNumberOfSegmentsLeft(0); sb.setUnitsPerSegment(2.0); sb.setUnitLabel("km")
    sb.attemptMove(QgsLayoutPoint(sx, sy, U)); lay.addLayoutItem(sb)
def export_png(lay, fn, dpi=170):
    ex = QgsLayoutExporter(lay); st = QgsLayoutExporter.ImageExportSettings(); st.dpi = dpi; st.generateWorldFile = False
    res = ex.exportToImage(PROJ + fn, st); print("export", fn, "OK" if res == QgsLayoutExporter.ExportResult.Success else f"FAIL {res}")

QJ = json.load(open(SCR + "out/queries.json", encoding="utf-8"))
SRC_STD = "Data: Landsat 8/9 Collection 2 Level 2 (USGS/NASA), Sentinel-2 L2A (ESA), ESA WorldCover 2021, SRTM (NASA/USGS), OpenStreetMap contributors. Ward boundaries: OpenCity / BharatLAS (not an official NMMC file). April 2026 imagery."
def map_layout(idx, title, subtitle, layers, legend_layers, key_lines, howto, source, fn, legend_names=None, accent=HEAT, key_y=86):
    lay = new_layout(f"Map {idx} - {title}")
    rect_item(lay, 0, 0, 210, 27, NAVY); rect_item(lay, 0, 27, 210, 1.2, accent)
    txt_item(lay, title, 10, 5, 190, 10, 19, True, "#FFFFFF", "Cambria"); txt_item(lay, subtitle, 10, 16, 190, 9, 10, False, "#CBD5E1")
    m = add_map(lay, layers, 10, 33, 128, 232, frame_extent(128, 232))
    add_legend(lay, m, legend_layers, 143, 33, legend_names)
    rect_item(lay, 143, key_y, 57, 40, "#F1F5F9"); txt_item(lay, "KEY NUMBERS", 146, key_y + 2, 52, 5, 8, True, accent); txt_item(lay, "\n".join("• " + k for k in key_lines), 146, key_y + 8, 52, 32, 8.5)
    rect_item(lay, 143, key_y + 44, 57, 46, "#FFF7ED"); txt_item(lay, "HOW TO READ THIS MAP", 146, key_y + 46, 52, 5, 8, True, accent); txt_item(lay, howto, 146, key_y + 52, 52, 38, 8.5)
    add_north_scale(lay, m, 178, 232, 145, 256)
    txt_item(lay, source, 10, 268, 190, 14, 7.5, False, "#475569", italic=True)
    txt_item(lay, "Prepared by Hasnat Shaikh (Roll 2405003)  |  GIS CA4  |  MGM University  |  CRS: WGS 84 / UTM zone 43N (EPSG:32643)", 10, 285, 190, 6, 7, False, "#64748B")
    export_png(lay, f"maps/{fn}.png"); return lay

# ------------------------------------------------------------------ PHASE 1: run the 10 queries (+1 overlay analysis) as QGIS processing tools
def run(alg, params): return processing.run(alg, params)["OUTPUT"]
def order(layer, expr, asc): return run("native:orderbyexpression", {"INPUT": layer, "EXPRESSION": expr, "ASCENDING": asc, "NULLS_FIRST": False, "OUTPUT": "memory:"})
wsrc = vl("wards", "src_wards")
QR = {}; RES = {}; SPEC = []
def stash(name, layer): layer.setName(name); QR[name] = layer; return layer
def first(layer): return next(layer.getFeatures())
A = [("A1", "Built-up land 80% or more", '"BuiltUp_Pct" >= 80', ["Ward_ID", "BuiltUp_Pct", "LST_C", "UCSI"], '"BuiltUp_Pct"', False, "Built-up %, highest first", "Q_A1_builtup_80plus"),
     ("A2", "Vegetation index (NDVI) below 0.2", '"NDVI" < 0.2', ["Ward_ID", "NDVI", "GreenCover_Pct", "UCSI"], '"NDVI"', True, "NDVI, lowest first", "Q_A2_ndvi_below_0_2"),
     ("A3", "Surface temperature 45 °C or more", '"LST_C" >= 45', ["Ward_ID", "LST_C", "NDVI", "BuiltUp_Pct"], '"LST_C"', False, "LST, hottest first", "Q_A3_lst_45plus"),
     ("A4", "Flood susceptibility score 4.5 or more", '"Flood_Score" >= 4.5', ["Ward_ID", "Flood_Score", "Elev_m", "DistWater_m"], '"Flood_Score"', False, "flood score, highest first", "Q_A4_flood_4_5plus"),
     ("A5", "Built-up 80% or more AND NDVI below 0.2", '"BuiltUp_Pct" >= 80 AND "NDVI" < 0.2', ["Ward_ID", "BuiltUp_Pct", "NDVI", "LST_C", "UCSI", "UCSI_Rank"], '"UCSI_Rank"', True, "UCSI rank (1 = highest stress)", "Q_A5_builtup_and_lowndvi")]
MEAN = {"A1": lambda n, f: f"{n} wards are 80% or more built-up. Ward {f['Ward_ID']} is the most built-up ({f['BuiltUp_Pct']}%).",
        "A2": lambda n, f: f"{n} wards have NDVI below 0.2, which means very few plants. Ward {f['Ward_ID']} has the lowest value ({f['NDVI']}).",
        "A3": lambda n, f: f"{n} wards have an average ground surface temperature of 45 °C or more. Ward {f['Ward_ID']} is the hottest ({f['LST_C']:.1f} °C). This is ground temperature, not air temperature.",
        "A4": lambda n, f: f"{n} wards score 4.5 or more out of 5. Susceptibility means water can collect there more easily. It is not a flood forecast.",
        "A5": lambda n, f: f"{n} wards are both very built-up and very bare of plants. Ward {f['Ward_ID']} ranks highest in this group (UCSI rank {f['UCSI_Rank']} of 111)."}
for qid, title, expr, cols, sortx, asc, sortlab, lname in A:
    res = order(run("native:extractbyexpression", {"INPUT": wsrc, "EXPRESSION": expr, "OUTPUT": "memory:"}), sortx, asc); n = res.featureCount(); f0 = first(res)
    RES[qid] = {"title": title, "expression": expr, "count": n, "wards": sorted(f["Ward_ID"] for f in res.getFeatures()), "first_ward": f0["Ward_ID"]}
    stash(lname, res)
    SPEC.append(dict(id=qid, title=title, tool=f"Select by Expression on layer 'wards':\n{expr}\n\nQGIS tool: Processing > Extract by expression", res=lname, cols=cols, below=[], above=[], summary=f"{n} of 111 wards match", meaning=MEAN[qid](n, f0), sortlab=sortlab, label=True))
# S1 water
water_big = H["water_big"]
res = order(run("native:extractbylocation", {"INPUT": wsrc, "PREDICATE": [0], "INTERSECT": water_big, "OUTPUT": "memory:"}), '"Water_Pct"', False); n = res.featureCount()
RES["S1"] = {"title": "Wards that intersect water or mangrove bodies of 1 ha or more", "count": n, "wards": sorted(f["Ward_ID"] for f in res.getFeatures())}; stash("Q_S1_wards_touching_water", res)
SPEC.append(dict(id="S1", title="Wards intersecting water or mangrove (1 ha or more)", tool="Vector > Research Tools > Select by Location\nInput: wards\nPredicate: intersect\nComparison: water_bodies where Area_ha >= 1", res="Q_S1_wards_touching_water", cols=["Ward_ID", "Water_Pct", "Flood_Score", "UCSI"], below=[], above=["water_big"], summary=f"{n} of 111 wards", meaning=f"{n} wards touch a water or mangrove body of 1 ha or more (blue). Distance to water is one of the four flood factors, so these wards are the first to check.", sortlab="water share, highest first", label=True))
# S2 roads
buf = run("native:buffer", {"INPUT": H["roads_major"], "DISTANCE": 200, "SEGMENTS": 8, "END_CAP_STYLE": 0, "JOIN_STYLE": 0, "MITER_LIMIT": 2, "DISSOLVE": True, "OUTPUT": "memory:"}); stash("Q_S2_road_buffer_200m", buf)
res = order(run("native:extractbylocation", {"INPUT": wsrc, "PREDICATE": [0], "INTERSECT": buf, "OUTPUT": "memory:"}), '"UCSI_Rank"', True); n = res.featureCount()
RES["S2"] = {"title": "Wards within 200 m of a major road", "count": n, "wards": sorted(f["Ward_ID"] for f in res.getFeatures())}; stash("Q_S2_wards_near_major_roads", res)
SPEC.append(dict(id="S2", title="Wards within 200 m of a major road", tool="Vector > Geoprocessing > Buffer\nInput: major_roads (motorway, trunk, primary)\nDistance: 200 m, dissolve\nthen Select by Location:\nwards intersect the buffer", res="Q_S2_wards_near_major_roads", cols=["Ward_ID", "BuiltUp_Pct", "LST_C", "UCSI", "UCSI_Rank"], below=[], above=["Q_S2_road_buffer_200m", "roads_major"], summary=f"{n} of 111 wards", meaning=f"{n} wards have a motorway, trunk or primary road within 200 m (blue buffer). Two of these roads, Thane-Belapur Road and Sion-Panvel Highway, were reported waterlogged on 26 May 2025 (news report).", sortlab="UCSI rank (1 = highest stress)", label=True))
# S3 hospitals inside highest-stress wards
top = stash("Q_S3_highest_ucsi_wards", run("native:extractbyexpression", {"INPUT": wsrc, "EXPRESSION": "\"UCSI_Class\" = 'Highest'", "OUTPUT": "memory:"})); ntop = top.featureCount()
res = order(run("native:extractbylocation", {"INPUT": L["hosp"], "PREDICATE": [6], "INTERSECT": top, "OUTPUT": "memory:"}), '"Ward_ID"', True); n = res.featureCount(); nh = L["hosp"].featureCount()
RES["S3"] = {"title": "Hospitals and clinics inside the highest-UCSI wards", "count": n, "top_wards": ntop, "all_hospitals": nh}; stash("Q_S3_hospitals_in_highest_wards", res)
SPEC.append(dict(id="S3", title="Hospitals inside the highest-stress wards", tool=f"Step 1: Select by expression\n  \"UCSI_Class\" = 'Highest'  ({ntop} wards)\nStep 2: Select by Location\n  Input: hospitals\n  Predicate: are within\n  Comparison: the {ntop} wards", res="Q_S3_hospitals_in_highest_wards", cols=["Hosp_ID", "Name", "Type", "Ward_ID"], below=["Q_S3_highest_ucsi_wards", "hosp_ctx"], above=[], summary=f"{n} of {nh} mapped hospitals", meaning=f"Only {n} of the {nh} mapped hospitals and clinics are inside the {ntop} highest-stress wards (yellow). OpenStreetMap may be missing some facilities, so treat this as a first check.", sortlab="Ward_ID", label=False))
# S4 nearest hospital
cent = run("native:centroids", {"INPUT": top, "ALL_PARTS": False, "OUTPUT": "memory:"})
j = run("native:joinbynearest", {"INPUT": cent, "INPUT_2": H["hosp_ctx"], "FIELDS_TO_COPY": ["Name"], "DISCARD_NONMATCHING": False, "PREFIX": "Hosp_", "NEIGHBORS": 1, "MAX_DISTANCE": None, "OUTPUT": "memory:"})
j = run("native:fieldcalculator", {"INPUT": j, "FIELD_NAME": "Dist_m", "FIELD_TYPE": 1, "FIELD_LENGTH": 10, "FIELD_PRECISION": 0, "FORMULA": 'round("distance")', "OUTPUT": "memory:"})
res = order(j, '"Dist_m"', False); dists = [f["Dist_m"] for f in res.getFeatures()]; f0 = first(res)
RES["S4"] = {"title": "Nearest hospital to each highest-UCSI ward centre", "count": len(dists), "mean_m": round(sum(dists) / len(dists)), "max_m": max(dists), "min_m": min(dists), "farthest_ward": f0["Ward_ID"]}; stash("Q_S4_nearest_hospital_to_ward_centre", res)
SPEC.append(dict(id="S4", title="Nearest hospital to each highest-stress ward", tool="Vector > Geoprocessing > Centroids\n  (the highest-stress wards)\nVector > Data Management >\n  Join attributes by nearest\n  Input: ward centroids\n  Join layer: hospitals, 1 neighbour\nField Dist_m = round(distance), metres", res="Q_S4_nearest_hospital_to_ward_centre", cols=["Ward_ID", "Hosp_Name", "Dist_m", "UCSI"], below=["Q_S3_highest_ucsi_wards", "hosp_ctx"], above=[], summary=f"mean {RES['S4']['mean_m']} m, longest {RES['S4']['max_m']} m", meaning=f"From the centre of each highest-stress ward, the nearest mapped hospital is {RES['S4']['mean_m']} m away on average. The longest distance is {RES['S4']['max_m']} m (ward {f0['Ward_ID']}). Distances are straight lines, not road distance.", sortlab="distance, longest first", label=True))
# S5 waterlogged site
res = run("native:extractbylocation", {"INPUT": wsrc, "PREDICATE": [1], "INTERSECT": H["site"], "OUTPUT": "memory:"}); f0 = first(res)
RES["S5"] = {"title": "Ward that contains the waterlogged APMC market site", "ward": f0["Ward_ID"], "flood_score": f0["Flood_Score"], "ucsi": f0["UCSI"], "ucsi_class": f0["UCSI_Class"], "rank": f0["UCSI_Rank"]}; stash("Q_S5_ward_with_waterlogged_site", res)
SPEC.append(dict(id="S5", title="Ward that contains the waterlogged APMC market", tool="Vector > Research Tools > Select by Location\nInput: wards\nPredicate: contain\nComparison: flood_reports where\n  Report_Type = 'Waterlogged site'", res="Q_S5_ward_with_waterlogged_site", cols=["Ward_ID", "Flood_Score", "UCSI", "UCSI_Class", "UCSI_Rank"], below=[], above=["site"], summary=f"Ward {f0['Ward_ID']}: flood score {f0['Flood_Score']}, UCSI {f0['UCSI']} ({f0['UCSI_Class']})", meaning=f"The APMC market site reported waterlogged on 26 May 2025 lies in ward {f0['Ward_ID']}. The model gives this ward a high flood score ({f0['Flood_Score']}) and UCSI rank {f0['UCSI_Rank']} of 111, so the news report and the model agree here. This is a small consistency check, not proof. The point is approximate (centre of the market yards in OpenStreetMap).", sortlab="Ward_ID", label=True))
# S6 overlay
inter = run("native:intersection", {"INPUT": wsrc, "OVERLAY": L["hot"], "INPUT_FIELDS": ["Ward_ID", "Area_km2"], "OVERLAY_FIELDS": ["Zone_ID"], "OUTPUT": "memory:"})
inter = run("native:fieldcalculator", {"INPUT": inter, "FIELD_NAME": "Hot_ha", "FIELD_TYPE": 0, "FIELD_LENGTH": 12, "FIELD_PRECISION": 2, "FORMULA": "$area / 10000", "OUTPUT": "memory:"}); stash("Q_S6_hot_lowgreen_x_wards", inter)
agg = {}
for f in inter.getFeatures(): agg[f["Ward_ID"]] = agg.get(f["Ward_ID"], 0) + f["Hot_ha"]
wa = {f["Ward_ID"]: f["Area_km2"] * 100 for f in wsrc.getFeatures()}
rows = sorted(agg.items(), key=lambda kv: -kv[1]); tot = sum(agg.values()); best_share = max([r for r in rows if wa[r[0]] >= 50], key=lambda kv: kv[1] / wa[kv[0]])
tb = QgsVectorLayer("None?field=Ward_ID:integer&field=Hot_lowgreen_ha:double&field=Ward_area_ha:double&field=Share_pct:double", "Q_S6_by_ward_table", "memory"); tp = tb.dataProvider(); ft = []
for w, a in rows:
    f = QgsFeature(tb.fields()); f.setAttributes([int(w), round(a, 1), round(wa[w], 1), round(a / wa[w] * 100, 1)]); ft.append(f)
tp.addFeatures(ft); stash("Q_S6_by_ward_table", tb)
RES["S6"] = {"title": "Ward-wise area that is both hot and low-green", "total_ha": round(tot, 1), "wards_touched": len(rows), "top": [(w, round(a, 1), round(a / wa[w] * 100, 1)) for w, a in rows[:10]], "best_share": (best_share[0], round(best_share[1] / wa[best_share[0]] * 100, 1))}
SPEC.append(dict(id="S6", title="Where hot and low-green land overlaps, ward by ward", tool="Raster calculator:\n  LST >= 45 AND NDVI < 0.2\nPolygonise, keep patches >= 2 ha\nVector > Geoprocessing > Intersection:\n  wards with hot patches\nField calculator: $area / 10000 (ha)\nStatistics by category: sum per ward", res="Q_S6_by_ward_table", cols=["Ward_ID", "Hot_lowgreen_ha", "Ward_area_ha", "Share_pct"], below=[], above=[], summary=f"{tot / 100:.1f} km² in 71 patches; {len(rows)} wards touched", meaning=f"Ward {rows[0][0]} has the largest hot and low-green area ({rows[0][1]:.0f} ha). Among wards larger than 50 ha, ward {best_share[0]} has the highest share ({RES['S6']['best_share'][1]}% of the ward). These are the first places to look at for trees or cool roofs.", sortlab="area, largest first", label=False, map_layer="hot"))
SORTF = {"A1": ("BuiltUp_Pct", False), "A2": ("NDVI", True), "A3": ("LST_C", False), "A4": ("Flood_Score", False), "A5": ("UCSI_Rank", True), "S1": ("Water_Pct", False), "S2": ("UCSI_Rank", True), "S3": ("Ward_ID", True), "S4": ("Dist_m", False), "S5": ("Ward_ID", True), "S6": ("Hot_lowgreen_ha", False)}
for sp in SPEC: sp["sortfield"], sp["asc"] = SORTF[sp["id"]]
SPEC[-1]["res_color"] = "#B91C1C"; SPEC[-1]["res_label"] = "Hot and low-green patch (2 ha or more)"
json.dump(RES, open(PROJ + "queries/query_results.json", "w"), indent=1)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("wards", "top")} for k, v in RES.items()}, indent=1)[:2600])

# ------------------------------------------------------------------ PHASE 2: save the results in a second GeoPackage and reload them as project layers
if os.path.exists(QGPKG): os.remove(QGPKG)
processing.run("native:package", {"LAYERS": list(QR.values()), "OUTPUT": QGPKG, "OVERWRITE": True, "SAVE_STYLES": False, "SAVE_METADATA": False, "SELECTED_FEATURES_ONLY": False, "EXPORT_RELATED_LAYERS": False})
P = {}
qgroup = rootg.addGroup("7  QUERY RESULTS (saved in NaviMumbai_query_results.gpkg)")
for name in QR:
    lyr = vl(name, name, path=QGPKG); P[name] = lyr; proj.addMapLayer(lyr, False)
    if lyr.geometryType() == Qgis.GeometryType.Polygon: lyr.setRenderer(QgsSingleSymbolRenderer(fill("#F59E0B", "#B45309", "0.25", 235)))
    elif lyr.geometryType() == Qgis.GeometryType.Point: lyr.setRenderer(QgsSingleSymbolRenderer(marker("#F59E0B", "circle", "3.0", "#7C2D12", "0.3")))
    nd = qgroup.addLayer(lyr); nd.setItemVisibilityChecked(False)
P["Q_S2_road_buffer_200m"].setRenderer(QgsSingleSymbolRenderer(fill("#93C5FD", "#2563EB", "0.1", 90)))
P["Q_S3_highest_ucsi_wards"].setRenderer(QgsSingleSymbolRenderer(fill("#FDE68A", "#7F0000", "0.3", 220)))
P["Q_S6_hot_lowgreen_x_wards"].setRenderer(QgsSingleSymbolRenderer(fill("#B91C1C", "#7F1D1D", "0.15", 150)))
def resolve(k): return P[k] if k in P else (H[k] if k in H else L[k])

# ------------------------------------------------------------------ PHASE 3: layouts
def style_table(tbl):
    tbl.setShowGrid(True); tbl.setGridStrokeWidth(0.15); tbl.setGridColor(QColor("#CBD5E1"))
    tbl.setContentTextFormat(text_fmt(9, "#0F172A", False, buffer=False)); tbl.setHeaderTextFormat(text_fmt(9, "#FFFFFF", True, buffer=False))
    try:
        hs = QgsLayoutTableStyle(); hs.enabled = True; hs.cellBackgroundColor = QColor(NAVY); tbl.setCellStyle(QgsLayoutTable.CellStyleGroup.HeaderRow, hs)
        os_ = QgsLayoutTableStyle(); os_.enabled = True; os_.cellBackgroundColor = QColor("#F8FAFC"); tbl.setCellStyle(QgsLayoutTable.CellStyleGroup.OddRows, os_)
    except Exception as e: print("table style:", e)
def qlayout(sp):
    R = resolve(sp["res"]); qid = sp["id"]
    if sp.get("label") and R.fields().indexOf("Ward_ID") >= 0: label_layer(R, "Ward_ID", 6.5, all_labels=True)
    map_lyr = resolve(sp["map_layer"]) if sp.get("map_layer") else R
    layers = [resolve(k) for k in sp["above"]] + [map_lyr] + [resolve(k) for k in sp["below"]] + [L["boundary"], L["w_light"]]
    lay = new_layout(f"Query {qid}")
    rect_item(lay, 0, 0, 210, 24, NAVY); rect_item(lay, 0, 24, 210, 1.2, "#F59E0B")
    txt_item(lay, f"Query {qid}: {sp['title']}", 10, 4, 190, 10, 15, True, "#FFFFFF", "Cambria"); txt_item(lay, sp["summary"], 10, 15, 190, 7, 9.5, False, "#CBD5E1")
    m = add_map(lay, layers, 10, 30, 96, 172, frame_extent(96, 172, 500))
    rect_item(lay, 112, 30, 88, 44, "#F1F5F9"); txt_item(lay, "HOW IT WAS RUN IN QGIS", 115, 32, 82, 5, 8, True, HEAT); txt_item(lay, sp["tool"], 115, 38, 82, 36, 8, False, "#0F172A", "Consolas")
    rect_item(lay, 112, 78, 88, 20, "#FFF7ED"); txt_item(lay, "RESULT", 115, 80, 82, 5, 8, True, HEAT); txt_item(lay, sp["summary"], 115, 86, 82, 12, 10.5, True)
    rect_item(lay, 112, 102, 88, 42, "#ECFDF5"); txt_item(lay, "WHAT IT MEANS", 115, 104, 82, 5, 8, True, GREEN); txt_item(lay, sp["meaning"], 115, 110, 82, 34, 9)
    rect_item(lay, 112, 150, 5, 4, sp.get("res_color", "#F59E0B"), "#B45309"); txt_item(lay, sp.get("res_label", "Result of the query"), 119, 149.5, 60, 5, 8, False, "#334155"); rect_item(lay, 112, 157, 5, 4, "#F1F5F9", "#94A3B8"); txt_item(lay, "Other wards", 119, 156.5, 40, 5, 8, False, "#334155")
    add_north_scale(lay, m, 185, 172, 114, 190)
    n = R.featureCount(); shown = min(n, 12)
    txt_item(lay, f"Table: {'all ' + str(n) if n <= 12 else 'first 12 of ' + str(n)} rows, sorted by {sp['sortlab']}.", 10, 203, 190, 4, 7.5, False, "#64748B", italic=True)
    tbl = QgsLayoutItemAttributeTable(lay); tbl.setVectorLayer(R); tbl.setMaximumNumberOfFeatures(12); style_table(tbl)
    tbl.setDisplayedFields(sp["cols"])
    sc = QgsLayoutTableColumn(); sc.setAttribute('"' + sp["sortfield"] + '"'); sc.setSortByRank(1); sc.setSortOrder(Qt.SortOrder.AscendingOrder if sp["asc"] else Qt.SortOrder.DescendingOrder)
    tbl.setSortColumns([sc])
    lay.addMultiFrame(tbl); fr = QgsLayoutFrame(lay, tbl); fr.attemptSetSceneRect(QRectF(10, 208, 190, 74)); fr.setFrameEnabled(False); tbl.addFrame(fr)
    txt_item(lay, "Prepared by Hasnat Shaikh (Roll 2405003)  |  GIS CA4  |  Result rendered by QGIS from NaviMumbai_UCSI.gpkg and saved in NaviMumbai_query_results.gpkg", 10, 285, 190, 6, 7, False, "#64748B")
    export_png(lay, f"queries/Query_{qid}.png", 160)
for sp in SPEC: qlayout(sp)

# ---- the 10 thematic maps
WL = [L["boundary"], L["wards"]]
map_layout(1, "Study area and ward boundaries", "Navi Mumbai: 111 wards, major roads, water and mangrove", [L["hosp"], L["roads"], L["water"], L["wards"], L["boundary"]], [L["wards"], L["roads"], L["water"], L["hosp"]],
           ["111 wards, 122.9 km² in total", "Ward numbers run from north (1) to south (111)", "Roads: OpenStreetMap", "Water: WorldCover 2021"], "Each shape is one ward and the number is its Ward_ID. Blue road lines were reported waterlogged on 26 May 2025. Green and blue areas on the west side are mangrove and creek water.",
           SRC_STD, "Map1_Study_area_wards", ["Wards (number = Ward_ID)", "Major roads (OSM)", "Water / mangrove", "Hospitals (OSM)"], accent=BLUE, key_y=128)
map_layout(2, "Land cover and built-up land", "ESA WorldCover 2021 (10 m)", WL + [L["lc"]], [L["lc"]], ["Built-up: 33.1%", "Tree cover: 26.4%", "Mangrove: 13.8%", "Water: 13.3%", "Cropland: 7.0%", "Grass: 5.2%"],
           "Red is built-up land. Green is trees and mangrove. Blue is water. Most built-up land sits in the central strip of the city.", SRC_STD, "Map2_Land_cover", ["Land cover (WorldCover)"], accent=GREY, key_y=114)
map_layout(3, "Vegetation (NDVI)", "Sentinel-2, median of 8 and 11 April 2026", WL + [L["ndvi"]], [L["ndvi"]], ["City mean NDVI: 0.30", "Ward means: 0.12 to 0.49", "40% of the area is below 0.2", "Mangroves stay green in the west"],
           "NDVI measures how green the ground is. Dark green means dense plants. Pale means bare or built-up ground. Low-NDVI wards get a high green-cover deficit score.", SRC_STD, "Map3_NDVI", ["NDVI (greenness)"], accent=GREEN)
map_layout(4, "Land surface temperature (heat)", "Landsat 8/9, median of 13, 22 and 30 April 2026", WL + [L["lst"]], [L["lst"]], [f"City mean: {QJ['city_lst_mean']} °C", "Ward means: 33.7 to 47.6 °C", f"{QJ['pct_area_lst_ge45']}% of the area is 45 °C or hotter", "Hottest ward: ward 70 (47.6 °C)"],
           "Darker means a hotter ground surface. This is the temperature of roofs, roads and soil seen by the satellite. It is higher than the air temperature people feel.", SRC_STD, "Map4_LST", ["Surface temperature"], accent=HEAT)
map_layout(5, "Elevation", "SRTM, 30 m", WL + [L["elev"]], [L["elev"]], ["Low ground along the creek in the west", "Higher ground in the east (Parsik hills)", "Elevation is the top flood factor (43% weight)"],
           "Pale colours are low ground. Brown is higher ground. Low ground collects water more easily. SRTM includes roofs and trees, so it is a surface height.", SRC_STD, "Map5_Elevation", ["Elevation (m)"], accent="#A9683A")
map_layout(6, "Flood susceptibility", "Ward score from elevation, water distance, slope and built-up land (AHP weights 43 / 27 / 16 / 14)", [L["flood"], L["boundary"], L["w_flood"]], [L["w_flood"], L["flood"]],
           ["A susceptibility index, not a forecast", "AHP consistency ratio: 0.017 (below 0.10 is acceptable)", "26 May 2025: Nerul 155.7 mm, Belapur 133.9 mm (news report)"],
           "Darker blue means water can collect more easily. Points show the 26 May 2025 news reports (reported rainfall for Nerul and Belapur, and the waterlogged APMC market). Point positions are approximate.", SRC_STD + " Flood reports: Free Press Journal, 26 May 2025.", "Map6_Flood_susceptibility", ["Flood susceptibility (1-5)", "Flood reports, 26 May 2025"], accent=BLUE, key_y=110)
map_layout(7, "Heat stress score", "Ward temperature stretched to a 1 (coolest) to 5 (hottest) scale", [L["boundary"], L["w_heat"]], [L["w_heat"]], ["Score 5 = hottest ward", "Score 1 = coolest ward", "Median of 3 April 2026 scenes"],
           "Each ward gets one score from its average surface temperature. Dark red wards are the hottest. Classes use Natural Breaks (Jenks).", SRC_STD, "Map7_Heat_stress", ["Heat stress score (1-5)"], accent=HEAT, key_y=88)
map_layout(8, "Green-cover deficit score", "Ward NDVI turned upside down: fewest plants = 5", [L["boundary"], L["w_green"]], [L["w_green"]], ["Score 5 = least vegetation", "Score 1 = most vegetation", "One season only (April 2026)"],
           "Dark brown wards have the fewest plants. NDVI is reversed so that a higher score always means more stress. Classes use Natural Breaks (Jenks).", SRC_STD, "Map8_Green_cover_deficit", ["Green deficit score (1-5)"], accent=GREEN, key_y=88)
map_layout(9, "Urban Climate Stress Index (UCSI)", "UCSI = (Heat + Green-cover deficit + Flood) ÷ 3. Five classes of about 22 wards (quantiles)", [L["hosp"], L["boundary"], L["w_ucsi"]], [L["w_ucsi"], L["hosp"]],
           ["Highest 5 wards: 70, 57, 67, 11, 29", "Highest class has 23 wards (two wards tie)", "Wards 57 and 66 are in the top quarter for all three stresses", "Rankings hold when weights change (rank correlation 0.98 and 0.95)"],
           "Dark red wards have the highest combined stress. Numbers mark the 10 highest-ranked wards. Black dots are hospitals and clinics. UCSI compares wards. It does not predict a future event.", SRC_STD, "Map9_UCSI_final", ["UCSI class", "Hospitals (OSM)"], accent=HEAT, key_y=96)
map_layout(10, "Hot and low-green patches", "Areas at 45 °C or more AND NDVI below 0.2 (spatial overlay)", [L["boundary"], L["hot"], L["wards"]], [L["hot"]], [f"All hot and low-green pixels: {QJ['overlap_area_km2']} km² ({QJ['overlap_pct_city']}% of the area)", f"Patches of 2 ha or more (mapped): 71 patches, {RES['S6']['total_ha'] / 100:.1f} km²"],
           "Each red patch is hot ground with very few plants. These are the first places to check for tree planting or cool roofs.", SRC_STD, "Map10_Hot_low_green_patches", ["Hot + low-green patches"], accent="#B91C1C")

# ------------------------------------------------------------------ save
with open(PROJ + "queries/Query_summary.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["Query", "Type", "Question", "QGIS method", "Result"])
    for sp in SPEC: w.writerow([sp["id"], "Attribute" if sp["id"].startswith("A") else ("Spatial" if sp["id"] != "S6" else "Spatial analysis"), sp["title"], sp["tool"].replace("\n", " | "), sp["summary"]])
ok = proj.write(PROJ + "NaviMumbai_UCSI.qgz"); print("project saved:", ok)
app.exitQgis()
