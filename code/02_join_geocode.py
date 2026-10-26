"""Step 2: join the Wikipedia master list to Wikidata birthplaces and geocode places of action.

Inputs (read in place):
  work/master.json, work/places.json, work/world.json (steps 0 and 1)
  _data2/wikidata/vc.json            Wikidata (CC0): people awarded the VC, birthplace and its coordinates
  _data2/wikidata/vc_mil.json        Wikidata (CC0): conflicts, branch
  _data2/wikipedia_link_coords.json  coordinates on the Wikipedia articles linked from the lists, and redirects
  _data2/geonames/cities1000.txt     GeoNames places with 1,000 or more people (CC BY 4.0), fallback only
  how-roman-is-your-road/data/counties.geojson  GB ceremonial counties (ONS boundaries, OGL v3)
Outputs:
  data/vc_actions.csv          one row per award (1,357 awards to 1,354 named recipients)
  data/place_geocoding.csv     every place-of-action string from the national lists and how it was located
  work/joined.json             the same as vc_actions.csv, for the next step
Run: python3 02_join_geocode.py
"""
import os, re, json, csv, math, urllib.parse
from collections import Counter, defaultdict
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
D2 = "/home/claude/hist/_data2"
M = json.load(open(os.path.join(ROOT, "work", "master.json")))
P = json.load(open(os.path.join(ROOT, "work", "places.json")))
WD = json.load(open(os.path.join(D2, "wikidata", "vc.json")))
MIL = json.load(open(os.path.join(D2, "wikidata", "vc_mil.json")))
LC = json.load(open(os.path.join(D2, "wikipedia_link_coords.json")))
COORDS, REDIR = LC["coords"], LC["redirects"]
WORLD = json.load(open(os.path.join(ROOT, "work", "world.json")))
CTY = json.load(open("/home/claude/hist/how-roman-is-your-road/data/counties.geojson"))


ALIAS = {"Jack Williams (VC)": "John Henry Williams"}  # the Welsh list's name for the same man


def canon(t):
    if not t: return t
    t = ALIAS.get(t, t)
    t = t.replace("_", " ").strip()
    t = t[0].upper() + t[1:]
    seen = 0
    while t in REDIR and seen < 5: t = REDIR[t]; seen += 1
    return t


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


# ---------- 1. master list: fix one shared link, split the three VC and Bar holders into two awards ----------
for r in M:
    if r["title"] == "John Williams (VC)" and r["campaign"] == "First World War":
        r["title"] = "John Henry Williams"   # the list links both John Williamses to the Rorke's Drift article
BARS = {  # second award: date as given in the list's date column
    "Noel Godfrey Chavasse": ("1917-07-31", "First World War", "31 July 1917 to 2 August 1917"),
    "Arthur Martin-Leake": ("1914-10-29", "First World War", "29 October 1914 to 8 November 1914"),
    "Charles Upham": ("1942-07-14", "Second World War", "14 to 15 July 1942"),
}
A = []
for r in M:
    r = dict(r); r["canon"] = canon(r["title"]); r["award_no"] = 1
    if r["title"] in BARS:
        d2, c2, t2 = BARS[r["title"]]
        first_text = r["date_text"].split(" ")[:3]
        r1 = dict(r); r1["date_text"] = " ".join(first_text) if r["title"] != "Charles Upham" else "22 to 30 May 1941"
        if r["title"] == "Arthur Martin-Leake": r1["campaign"] = "Second Boer War"
        r2 = dict(r); r2.update(date_sort=d2, campaign=c2, campaign_link=c2, date_text=t2, award_no=2)
        A += [r1, r2]
    else:
        A.append(r)
for r in A: r["date_text"] = r["date_text"].replace("–", " to ").replace("&ndash;", " to ")
print("named recipients", len(M), "awards", len(A))

# ---------- 2. Wikidata ----------
wd_by_title = defaultdict(list)
for x in WD:
    t = urllib.parse.unquote(x["enwiki"].split("/wiki/", 1)[1])
    wd_by_title[canon(t)].append(x)
conf_by_p = defaultdict(set)
for x in MIL:
    if x.get("confLabel"): conf_by_p[x["p"]].add(x["confLabel"])
COUNTRY_ISO = {}
cgeoms = [(c["name"], c["iso"], shape(c["geom"])) for c in WORLD["countries"]]
ctree = STRtree([g for _, _, g in cgeoms])
cnty = [(f["properties"]["county"], f["properties"]["nation"], shape(f["geometry"])) for f in CTY["features"]]
ktree = STRtree([g for _, _, g in cnty])


def country_of(lat, lon):
    pt = Point(lon, lat)
    for i in ctree.query(pt):
        if cgeoms[i][2].contains(pt): return cgeoms[i][0], cgeoms[i][1]
    i = ctree.nearest(pt)
    if cgeoms[i][2].distance(pt) < 0.1: return cgeoms[i][0], cgeoms[i][1]
    return None, None


def county_of(lat, lon):
    pt = Point(lon, lat)
    for i in ktree.query(pt):
        if cnty[i][2].contains(pt): return cnty[i][0], cnty[i][1]
    i = ktree.nearest(pt)
    if cnty[i][2].distance(pt) < 0.03: return cnty[i][0], cnty[i][1]
    return None, None


nomatch, multi_bp = [], 0
for r in A:
    rows = wd_by_title.get(r["canon"], [])
    r["wikidata"] = rows[0]["p"] if rows else None
    bps = {}
    for x in rows:
        if x.get("bpc"): bps.setdefault(x["bp"], x)
    if len(bps) > 1 and r["award_no"] == 1: multi_bp += 1
    # several birthplaces on one person: keep the most specific (not a country label), else the first
    pick = None
    for x in bps.values():
        if x.get("bpLabel") != x.get("bpcountryLabel"): pick = x; break
    if pick is None and bps: pick = list(bps.values())[0]
    if not rows and r["award_no"] == 1: nomatch.append(r["title"])
    r["birthplace"] = pick["bpLabel"] if pick else (rows[0].get("bpLabel") if rows else None)
    r["birthplace_qid"] = pick["bp"] if pick else None
    r["dob"] = rows[0].get("dob", "")[:10] if rows else None
    if pick:
        lon, lat = map(float, re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", pick["bpc"]).groups())
        r["birth_lat"], r["birth_lon"] = round(lat, 5), round(lon, 5)
        r["birth_country"], r["birth_iso"] = country_of(lat, lon)
        r["birth_county"], r["birth_nation"] = county_of(lat, lon) if r["birth_iso"] == "GB" else (None, None)
    else:
        r["birth_lat"] = r["birth_lon"] = r["birth_country"] = r["birth_iso"] = r["birth_county"] = r["birth_nation"] = None
    r["wd_conflicts"] = sorted(conf_by_p.get(r["wikidata"], []))
print("no Wikidata match:", len(nomatch), nomatch[:20])
print("people with more than one birthplace on Wikidata:", multi_bp)

# ---------- 3. places of action from the national lists ----------
ISO = {"France": ["FR"], "India": ["IN", "PK", "BD"], "Belgium": ["BE"], "South Africa": ["ZA"], "Burma": ["MM", "IN"],
       "Crimea": ["UA", "RU"], "Afghanistan": ["AF"], "Italy": ["IT"], "Turkey": ["TR"], "Mesopotamia": ["IQ"],
       "New Zealand": ["NZ"], "Germany": ["DE"], "Egypt": ["EG"], "Tunisia": ["TN"], "New Guinea": ["PG", "ID"],
       "Somaliland": ["SO"], "Palestine": ["IL", "PS"], "Abyssinia": ["ET"], "China": ["CN"], "Greece": ["GR"],
       "Russia": ["RU"], "Netherlands": ["NL"], "Persia": ["IR"], "Vietnam": ["VN"], "South Vietnam": ["VN"], "Malaya": ["MY"],
       "Ashanti": ["GH"], "Rhodesia": ["ZW", "ZM"], "Sudan": ["SD"], "Libya": ["LY"], "Finland": ["FI", "AX"], "Bengal": ["IN", "BD"],
       "Eritrea": ["ER"], "Papua": ["PG"], "Borneo": ["MY", "ID", "BN"], "Japan": ["JP"], "Gambia": ["GM"], "Denmark": ["DK", "SEA"],
       "Singapore": ["SG"], "Canada": ["CA"], "Tibet": ["CN"], "Lebanon": ["LB"], "Kenya": ["KE"], "Syria": ["SY"],
       "East Timor": ["TL"], "Hong Kong": ["HK"], "Algeria": ["DZ"], "Iraq": ["IQ"], "German East Africa": ["TZ"],
       "Norway": ["NO"], "Burma (now Myanmar)": ["MM", "IN"], "British North Borneo": ["MY"], "Pakistan": ["PK"], "Malaysia": ["MY"],
       "Korea": ["KR", "KP"], "Ethiopia": ["ET"], "Nigeria": ["NG"], "Ghana": ["GH"], "Uganda": ["UG"], "Tanzania": ["TZ"]}
# coordinates on an article for a whole country or large region are too coarse to stand for a place of action
COARSE = set(ISO) | {"India", "British India", "France", "Belgium", "Burma", "Afghanistan", "Egypt", "South Africa", "Turkey", "Italy",
                     "Germany", "Japan", "Atlantic Ocean", "Pacific Ocean", "Mesopotamia", "Western Front (World War I)",
                     "British Malaya", "Malaya", "Bengal", "Persia", "Iran", "Iraq", "Ottoman Empire", "Russia", "China",
                     "Qing dynasty", "Ethiopia", "Ethiopian Empire", "New Guinea", "Papua New Guinea", "Somaliland", "British Somaliland",
                     "Sudan", "Libya", "Tunisia", "Greece", "Netherlands", "Finland", "Vietnam", "South Vietnam", "Malaysia",
                     "Borneo", "Korea", "Gambia", "The Gambia", "Ashanti Empire", "Rhodesia", "Crimea", "Myanmar", "Pakistan",
                     "Bangladesh", "Punjab", "Oudh State", "Awadh", "Kingdom of Afghanistan", "Emirate of Afghanistan", "Tibet",
                     "Syria", "Lebanon", "Palestine", "Kenya", "Algeria", "Eritrea", "Norway", "Denmark", "New Zealand", "Canada",
                     "Sri Lanka", "Hong Kong", "Singapore", "Mandatory Palestine", "Ottoman Syria", "Zululand", "Transvaal",
                     "South African Republic", "Orange Free State", "Natal", "Colony of Natal", "Cape Colony", "Waziristan",
                     "North-West Frontier Province", "Swat (Pakistan)", "Gallipoli", "Andaman Islands", "Bhutan", "Sikkim", "Manipur",
                     "Bechuanaland", "Matabeleland", "Mashonaland", "Basutoland", "Abyssinia", "Kingdom of Ashanti"}
GN = defaultdict(list)
with open(os.path.join(D2, "geonames", "cities1000.txt"), encoding="utf-8") as fh:
    for ln in fh:
        f = ln.rstrip("\n").split("\t")
        rec = (f[8], float(f[4]), float(f[5]), int(f[14] or 0), f[0], f[1])
        for n in {f[1], f[2], *[a for a in f[3].split(",") if a]}:
            if len(n) > 2: GN[n.lower()].append(rec)

STRIP = re.compile(r"\b(near|nr\.?|sector|wood|ridge|river|bay|hill|heights|road|bridge|support line|canal|area|front|in|the)\b", re.I)


def geonames(name, countries):
    tried = []
    for cand in [name, STRIP.sub(" ", name)]:
        cand = re.sub(r"\s+", " ", cand).strip(" ,.-")
        if not cand or cand.lower() in tried: continue
        tried.append(cand.lower())
        hits = [h for h in GN.get(cand.lower(), []) if h[0] in countries]
        uniq = {h[4]: h for h in hits}.values()
        uniq = sorted(uniq, key=lambda h: -h[3])
        if not uniq: continue
        far = [h for h in uniq if hav((h[1], h[2]), (uniq[0][1], uniq[0][2])) > 50]
        if far: return None, f"ambiguous: {len(uniq)} GeoNames places called {cand}"
        return uniq[0], cand
    return None, "no GeoNames match"


def in_country(lat, lon, countries, tol_km=60):
    """True if the point lies in (or within tol_km of) one of the ISO countries."""
    if not countries: return True
    pt = Point(lon, lat)
    if "SEA" in countries and country_of(lat, lon)[0] is None: return True  # a naval action off that coast
    for name, iso, g in cgeoms:
        if iso in countries or (iso == "GB-NIR" and "GB" in countries):
            if g.contains(pt) or g.distance(pt) * 111 < tol_km: return True
    return False


BATTLES = {}
for x in json.load(open(os.path.join(D2, "wikidata", "battles_world.json"))):
    mm = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", x.get("c") or "")
    if mm:
        lo, la = map(float, mm.groups())
        BATTLES[x["b"]] = (x["bLabel"], la, lo, x.get("enwiki", ""))
WD_BATTLE_DATES = defaultdict(list)
for x in json.load(open(os.path.join(D2, "wikidata", "battles_world.json"))):
    WD_BATTLE_DATES[x["b"]] += [x.get("d", ""), x.get("d2", "")]
BATTLE_BY_LABEL = defaultdict(list)
for q, (lab, la, lo, en) in BATTLES.items(): BATTLE_BY_LABEL[lab.lower()].append((q, lab, la, lo, en))


def locate(row):
    pt = row["place_text"]
    parts = [s.strip() for s in re.split(r",", pt) if s.strip()]
    cty = parts[-1] if len(parts) > 1 else None
    cty = re.sub(r"\s*\(.*\)$", "", cty).strip() if cty else None
    if cty and cty.lower().startswith("near "): cty = cty[5:]
    countries = ISO.get(cty or "", [])
    # (a) a wikilink in the place cell that leads to an article with coordinates
    for ln in row["place_links"]:
        t = canon(ln)
        if t in COORDS and t not in COARSE and ln not in COARSE:
            la, lo = COORDS[t]
            if not in_country(la, lo, countries):
                continue
            return dict(lat=la, lon=lo, method="wikipedia_link", matched=t, precision="place",
                        source=f"https://en.wikipedia.org/wiki/{urllib.parse.quote(t.replace(' ', '_'))}")
    first = re.sub(r"\(.*?\)", "", parts[0]).strip() if parts else ""
    # (b) unlinked text that is exactly the title of a linked Wikipedia article with coordinates, inside the stated country
    if countries and first:
        for cand in [first, first.replace("St. ", "Saint-").replace("St ", "Saint-")]:
            t = canon(cand)
            if t in COORDS and t not in COARSE:
                la, lo = COORDS[t]
                if in_country(la, lo, countries, 30):
                    return dict(lat=la, lon=lo, method="wikipedia_title", matched=t, precision="place",
                                source=f"https://en.wikipedia.org/wiki/{urllib.parse.quote(t.replace(' ', '_'))}")
    # (c) GeoNames cities1000, same name inside the stated country, unambiguous within 50 km
    reason = "country not recognised for GeoNames fallback" if cty else "no country given"
    if countries and first:
        h, how = geonames(first, countries)
        if h:
            return dict(lat=h[1], lon=h[2], method="geonames", matched=f"{h[5]} ({h[0]}, GeoNames {h[4]})", precision="place",
                        source=f"https://www.geonames.org/{h[4]}")
        reason = how
        # (d) a Wikidata battle named after the place ("Battle of X"), inside the stated country
        for lab in [f"battle of {first.lower()}", f"siege of {first.lower()}", f"battle of the {first.lower()}"]:
            hits = [b for b in BATTLE_BY_LABEL.get(lab, []) if in_country(b[2], b[3], countries, 30)]
            if len(hits) == 1:
                q, lab_, la, lo, en = hits[0]
                return dict(lat=la, lon=lo, method="wikidata_battle", matched=f"{lab_} ({q})", precision="place",
                            source=f"https://www.wikidata.org/wiki/{q}")
    # (e) a linked region or country: keep but mark as coarse (not used for distances or the hot-spot map)
    for ln in row["place_links"]:
        t = canon(ln)
        if t in COORDS and in_country(COORDS[t][0], COORDS[t][1], countries, 300):
            la, lo = COORDS[t]
            return dict(lat=la, lon=lo, method="wikipedia_link_coarse", matched=t, precision="region",
                        source=f"https://en.wikipedia.org/wiki/{urllib.parse.quote(t.replace(' ', '_'))}", note=reason)
    return dict(lat=None, lon=None, method="unmatched", matched="", precision="", source="", note=reason)


geo_rows = []
by_title = defaultdict(list)
for row in P:
    g = locate(row); row.update(g)
    by_title[canon(row["title"])].append(row)
    geo_rows.append(row)

# join to awards: same article; for the three double awards, match on year
PRI = ["Irish", "Indian Army", "Australian", "Canadian", "New Zealand", "By nationality"]
for r in A:
    cands = by_title.get(r["canon"], [])
    yr = (r["date_sort"] or "")[:4]
    if r["title"] in BARS:
        cands = [c for c in cands if c["year"][:4] == yr] or []
    cands = sorted(cands, key=lambda c: (c["lat"] is None, c["precision"] != "place", PRI.index(c["list"])))
    r["in_lists"] = sorted({c["list"] for c in by_title.get(r["canon"], [])}, key=PRI.index)
    if cands:
        c = cands[0]
        r.update(place_text=c["place_text"], place_list=c["list"], place_lat=c["lat"], place_lon=c["lon"], place_method=c["method"],
                 place_matched=c["matched"], place_precision=c["precision"], place_source=c["source"], province=c.get("province"))
        alt = [x for x in cands[1:] if x["lat"] is not None and c["lat"] is not None and hav((x["lat"], x["lon"]), (c["lat"], c["lon"])) > 100]
        r["place_conflict_km"] = round(max(hav((x["lat"], x["lon"]), (c["lat"], c["lon"])) for x in alt)) if alt else None
    else:
        r.update(place_text=None, place_list=None, place_lat=None, place_lon=None, place_method=None, place_matched=None,
                 place_precision=None, place_source=None, province=None, place_conflict_km=None)
    ok = r["birth_lat"] is not None and r["place_lat"] is not None and r["place_precision"] == "place"
    r["distance_km"] = round(hav((r["birth_lat"], r["birth_lon"]), (r["place_lat"], r["place_lon"]))) if ok else None

# second source: a single specific battle on the person's Wikidata "conflict" (P607) statements, with coordinates
conf_q_by_p = defaultdict(set)
for x in MIL:
    if x.get("conf"): conf_q_by_p[x["p"]].add(x["conf"])
BROAD = re.compile(r"war|campaign|front|theat|emergency|rebellion|mutiny|expedition|intervention|confrontation|bombing|operation|conflict|crisis|uprising|insurgency|revolt|occupation|invasion|offensive|raid on|hundred days|western desert", re.I)
for r in A:
    if r["place_precision"] == "place" or not r["wikidata"]: continue
    yr = int((r["date_sort"] or "0")[:4])
    bs = []
    for q in conf_q_by_p.get(r["wikidata"], []):
        if q in BATTLES and not BROAD.search(BATTLES[q][0]):
            bs.append((q,) + BATTLES[q])
    if len(bs) != 1: continue
    q, lab, la, lo, en = bs[0]
    bdates = [x for x in WD_BATTLE_DATES.get(q, []) if x]
    if bdates and not any(abs(int(d[:4]) - yr) <= 1 for d in bdates): continue
    r.update(place_text=lab, place_list="Wikidata conflict (P607)", place_lat=la, place_lon=lo, place_method="wikidata_p607_battle",
             place_matched=f"{lab} ({q})", place_precision="place", place_source=f"https://www.wikidata.org/wiki/{q}")
for r in A:
    ok = r["birth_lat"] is not None and r["place_lat"] is not None and r["place_precision"] == "place"
    r["distance_km"] = round(hav((r["birth_lat"], r["birth_lon"]), (r["place_lat"], r["place_lon"]))) if ok else None
print("awards placed from Wikidata battles:", sum(r["place_method"] == "wikidata_p607_battle" for r in A))

# national-list rows that found no award in the master list
unj = [row for row in P if not any(canon(row["title"]) == r["canon"] for r in A)]
print("national-list rows not joined to master:", len(unj), [u["title"] for u in unj][:30])
print("place methods (rows):", Counter(g["method"] for g in geo_rows))
print("awards with a place:", sum(r["place_text"] is not None for r in A), "with precise coords:",
      sum(r["place_precision"] == "place" for r in A), "with distance:", sum(r["distance_km"] is not None for r in A))
print("conflicting places across lists (>100 km):", [(r["title"], r["place_conflict_km"]) for r in A if r["place_conflict_km"]])

FIELDS = ["title", "name", "award_no", "rank", "unit", "campaign", "date_sort", "date_text", "posthumous", "wikidata", "dob",
          "birthplace", "birthplace_qid", "birth_lat", "birth_lon", "birth_country", "birth_iso", "birth_county", "birth_nation",
          "in_lists", "place_text", "place_list", "place_lat", "place_lon", "place_method", "place_matched", "place_precision",
          "place_source", "distance_km", "province", "wd_conflicts"]
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
with open(os.path.join(ROOT, "data", "vc_actions.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["wikipedia_article"] + FIELDS[1:])
    for r in sorted(A, key=lambda r: (r["date_sort"] or "9999", r["name"])):
        w.writerow([";".join(v) if isinstance(v, list) else ("" if v is None else v) for v in [r[k] for k in FIELDS]])
with open(os.path.join(ROOT, "data", "place_geocoding.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["list", "wikipedia_article", "year", "conflict", "place_text", "place_links", "method", "matched", "precision", "lat", "lon", "source", "note"])
    for g in geo_rows:
        w.writerow([g["list"], g["title"], g["year"], g["conflict"], g["place_text"], ";".join(g["place_links"]), g["method"], g["matched"],
                    g["precision"], g["lat"] if g["lat"] is not None else "", g["lon"] if g["lon"] is not None else "", g["source"], g.get("note", "")])
json.dump({"awards": A, "geo_rows": geo_rows, "nomatch_wd": nomatch, "multi_bp": multi_bp, "unjoined": [u["title"] for u in unj]},
          open(os.path.join(ROOT, "work", "joined.json"), "w"), ensure_ascii=False)
