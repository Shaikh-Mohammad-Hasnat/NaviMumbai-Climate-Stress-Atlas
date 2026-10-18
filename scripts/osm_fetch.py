import json, subprocess, time, geopandas as gpd, sys
w=gpd.read_file("C:/Users/farha/Downloads/hasnat gsi ca/NaviMumbai_Atlas/NaviMumbai_Atlas/NaviMumbai_Atlas.gpkg",layer="wards_32643").to_crs(4326); bb=w.total_bounds
b=f"({bb[1]-0.004},{bb[0]-0.004},{bb[3]+0.004},{bb[2]+0.004})"
Q={'roads':f'[out:json][timeout:100];way["highway"~"^(motorway|trunk|primary|secondary)$"]{b};out geom tags;',
   'hosp':f'[out:json][timeout:100];(node["amenity"="hospital"]{b};way["amenity"="hospital"]{b};);out center tags;',
   'apmc':f'[out:json][timeout:100];(node["name"~"APMC"]{b};way["name"~"APMC"]{b};);out center tags;',
   'places':f'[out:json][timeout:100];node["place"~"suburb|neighbourhood|town"]["name"~"Nerul|Belapur|Vashi|Turbhe|Airoli|Ghansoli|Kopar|Digha|Sanpada"]{b};out tags;'}
for k,q in Q.items():
    ok=False
    for attempt in range(3):
        for ep in ["https://overpass.kumi.systems/api/interpreter","https://overpass-api.de/api/interpreter"]:
            r=subprocess.run(["curl","-s","-m","120","-A","GIS-CA4-student-project","--data-urlencode","data="+q,ep],capture_output=True)
            try:
                j=json.loads(r.stdout.decode('utf8')); json.dump(j,open(f'build/osm_{k}.json','w')); print(k,len(j['elements']),'elements',flush=True); ok=True; break
            except Exception: time.sleep(3)
        if ok: break
    if not ok: print(k,'FAILED',flush=True)
