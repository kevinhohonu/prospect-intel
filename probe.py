# TEMPORARY probe, reverted after one run: how does SAM.gov `title` match?
import os, requests
from datetime import date, timedelta
key = os.environ["SAM_API_KEY"]
t = date.today(); f = (t - timedelta(days=90)).strftime("%m/%d/%Y"); to = t.strftime("%m/%d/%Y")
for term in ["gauge", "gage", "flood", "tidal", "tide gauge", "water level", "liquid level", "level sensor", "hydrolog", "hydrograph", "stream", "river", "coastal", "shoreline", "resilien", "surge", "early warning", "warning system", "monitoring", "telemetry", "sensor", "inundation", "stormwater", "levee", "floodwall", "NOAA", "USGS"]:
    for ptype in ["o,k,p"]:
        p = {"api_key": key, "title": term, "postedFrom": f, "postedTo": to, "limit": 3}
        if ptype: p["ptype"] = ptype
        r = requests.get("https://api.sam.gov/opportunities/v2/search", params=p, timeout=60)
        d = r.json() if r.ok else {}
        print(f"PROBE title={term!r} ptype={ptype} status={r.status_code} total={d.get('totalRecords')} sample={[o.get('title','')[:50] for o in d.get('opportunitiesData') or []]}", flush=True)
