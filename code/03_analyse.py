"""Step 3: analysis. Writes data/results.json (every number used anywhere) and the reusable data files.

Input: work/joined.json (step 2)
Outputs:
  data/results.json
  data/vc_awards.csv            one row per award, cleaned, with conflict group, region of action and distance
  data/birth_places.csv         birthplaces with counts
  data/birth_counties_gb.csv    births by GB ceremonial county (modern boundaries)
  data/hotspots.csv             places of action grouped within 15 km
  data/flows.geojson            a line from birthplace to place of action for every award where both are known
  work/site.json                compact data for the page
Run: python3 03_analyse.py
"""
import os, re, json, csv, math, statistics as st
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
J = json.load(open(os.path.join(ROOT, "work", "joined.json")))
A = J["awards"]


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


# ---------- cleaning ----------
FIX = []
for a in A:
    if a["title"] == "William Knox Leet" and a["campaign"] == "Indian Mutiny":
        a["campaign"] = "Anglo-Zulu War"
        FIX.append("William Knox Leet: the list's campaign column says Indian Mutiny, but his date of action (28 March 1879), the Irish list's place (Inhlobana) and Wikidata all point to the Anglo-Zulu War; I use Anglo-Zulu War.")
    if a["campaign"] == "Zulu War": a["campaign"] = "Anglo-Zulu War"
    if a["campaign"] == "—": a["campaign"] = "Not at war (Canada, 1866)"
    years = re.findall(r"(1[89]\d\d|20\d\d)", a["date_text"] or "")
    a["year"] = int(years[0]) if years else int(a["date_sort"][:4]) if a["date_sort"] else None
    if a["date_sort"] and a["year"] and int(a["date_sort"][:4]) != a["year"]:
        FIX.append(f"{a['name']}: hidden sort date {a['date_sort']} but the visible date reads '{a['date_text']}'; I use the visible year {a['year']}.")
    # birthplace precision: a country or the bare "Nepal" etc. is too coarse for distance
    bp = a["birthplace"] or ""
    a["birth_precision"] = None if a["birth_lat"] is None else ("country" if bp in ("Nepal", "India", "Ireland", "Scotland", "England", "Wales", "Canada", "Australia", "Kingdom of England", "British Empire", "British India", "Pakistan", "United Kingdom", "New Zealand", "South Africa") or re.match(r"^Q\d+$", bp) else "place")
print("\n".join(FIX))

GROUPS = [("crimea", "Crimean War", 1854, 1856), ("mutiny", "Indian Mutiny", 1857, 1859), ("victorian", "Other campaigns, 1856 to 1913", 0, 0),
          ("ww1", "First World War", 1914, 1918), ("interwar", "Between the wars", 1919, 1938), ("ww2", "Second World War", 1939, 1945), ("post", "Since 1945", 1946, 2100)]
SAF = {"Second Boer War", "First Boer War", "Anglo-Zulu War", "Basuto War", "9th Cape Frontier War", "Matabeleland Rebellion", "Mashona Rebellion"}


def group(a):
    c = a["campaign"]
    if c == "Crimean War": return "crimea"
    if c == "Indian Mutiny": return "mutiny"
    if c == "First World War": return "ww1"
    if c == "Second World War": return "ww2"
    if a["year"] >= 1946: return "post"
    if a["year"] >= 1919: return "interwar"
    return "victorian"


for a in A:
    a["group"] = group(a)
    a["southern_africa_war"] = a["campaign"] in SAF

# ---------- regions ----------
REG_ISO = {
    "Western Front and north-west Europe": "FR BE NL DE LU DK NO".split(),
    "Italy and the Mediterranean": "IT GR MT ES CY SM AL".split(),
    "Russia, the Baltic and the Black Sea": "UA RU FI AX EE LV".split(),
    "Gallipoli and the Middle East": "TR IQ IR SY LB IL PS JO SA".split(),
    "North and East Africa": "EG LY TN DZ SD ER ET SO -99 KE TZ UG".split(),
    "Southern Africa": "ZA ZW ZM BW LS NA MZ".split(),
    "West Africa": "GH GM NG SL".split(),
    "South Asia and Afghanistan": "IN PK BD NP BT AF LK".split(),
    "Burma and South-East Asia": "MM MY SG TH VN ID TL BN".split(),
    "China, Japan and Korea": "CN HK JP KR KP".split(),
    "New Zealand and the Pacific": "NZ PG SB AU".split(),
    "The Americas and South Atlantic": "CA FK US".split(),
}
ISO2REG = {i: r for r, l in REG_ISO.items() for i in l}
CAMP_REG = {"Crimean War": "Russia, the Baltic and the Black Sea", "Indian Mutiny": "South Asia and Afghanistan",
            "Second Afghan War": "South Asia and Afghanistan", "Tirah Campaign": "South Asia and Afghanistan", "Waziristan Campaign": "South Asia and Afghanistan",
            "Mohmand Campaign": "South Asia and Afghanistan", "Second Mohmand Campaign": "South Asia and Afghanistan", "Hunza-Naga Campaign": "South Asia and Afghanistan",
            "Chitral Expedition": "South Asia and Afghanistan", "Siege of Malakand": "South Asia and Afghanistan", "Umbeyla Campaign": "South Asia and Afghanistan",
            "Bhutan War": "South Asia and Afghanistan", "Lushai Expedition": "South Asia and Afghanistan", "Second Naga Hills Expedition": "South Asia and Afghanistan",
            "Anglo-Manipur War": "South Asia and Afghanistan", "Baluchistan": "South Asia and Afghanistan", "Andaman Islands Expedition": "South Asia and Afghanistan",
            "War in Afghanistan": "South Asia and Afghanistan", "Helmand": "South Asia and Afghanistan", "Operation Herrick": "South Asia and Afghanistan",
            "Armed Mission to Tibet": "China, Japan and Korea", "Third China War": "China, Japan and Korea", "Taiping Rebellion": "China, Japan and Korea",
            "Boxer Rising": "China, Japan and Korea", "Bombardment of Shimonoseki": "China, Japan and Korea", "Korean War": "China, Japan and Korea",
            "Kachin Hills Expedition": "Burma and South-East Asia", "British rule in Burma": "Burma and South-East Asia", "Perak War": "Burma and South-East Asia",
            "Vietnam War": "Burma and South-East Asia", "Malaysia-Indonesia Confrontation": "Burma and South-East Asia",
            "New Zealand Wars": "New Zealand and the Pacific", "Anglo-Persian War": "Gallipoli and the Middle East", "Arab Revolt": "Gallipoli and the Middle East",
            "Operation Telic": "Gallipoli and the Middle East", "Occupation of Crete": "Italy and the Mediterranean",
            "Sudan Campaign": "North and East Africa", "Occupation of Egypt": "North and East Africa", "Abyssinian War": "North and East Africa",
            "Second Somaliland Expedition": "North and East Africa", "Third Somaliland Expedition": "North and East Africa", "Fourth Somaliland Expedition": "North and East Africa",
            "First Ashanti Expedition": "West Africa", "Third Ashanti Expedition": "West Africa", "The Gambia": "West Africa", "Kano-Sokoto Expedition": "West Africa",
            "North Russia Relief Force": "Russia, the Baltic and the Black Sea", "Falklands War": "The Americas and South Atlantic",
            "Not at war (Canada, 1866)": "The Americas and South Atlantic"}
for c in SAF: CAMP_REG[c] = "Southern Africa"

WORLD = json.load(open(os.path.join(ROOT, "work", "world.json")))
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
cg = [(c["iso"], shape(c["geom"])) for c in WORLD["countries"]]
ct = STRtree([g for _, g in cg])


def iso_at(lat, lon):
    pt = Point(lon, lat)
    for i in ct.query(pt):
        if cg[i][1].contains(pt): return cg[i][0]
    i = ct.nearest(pt)
    return cg[i][0] if cg[i][1].distance(pt) < 0.5 else None


for a in A:
    a["place_iso"] = iso_at(a["place_lat"], a["place_lon"]) if a["place_lat"] is not None else None
    if a["place_lat"] is not None:
        a["region"] = ISO2REG.get(a["place_iso"]) or (CAMP_REG.get(a["campaign"], "At sea") if a["place_iso"] is None else "Other")
        a["region_from"] = "place of action"
    elif a["campaign"] in CAMP_REG:
        a["region"] = CAMP_REG[a["campaign"]]; a["region_from"] = "campaign"
    else:
        a["region"] = None; a["region_from"] = None
    if a["birth_lat"] is not None:
        iso = a["birth_iso"]
        if iso == "GB": b = a["birth_nation"] or "Great Britain, county not found"
        elif iso in ("IE", "GB-NIR"): b = "Ireland"
        elif iso in ("IN", "PK", "BD", "NP", "LK", "MM", "BT"): b = "South Asia"
        elif iso == "AU": b = "Australia"
        elif iso == "CA": b = "Canada"
        elif iso == "NZ": b = "New Zealand"
        elif iso in ("ZA", "ZW", "ZM", "BW", "LS", "NA"): b = "Southern Africa"
        else: b = "Elsewhere"
    else:
        b = "Not known"
    a["birth_group"] = b
    a["dist_ok"] = a["distance_km"] is not None and a["birth_precision"] == "place"

people = [a for a in A if a["award_no"] == 1]
R = {}
R["counts"] = dict(recipients=len(people), awards=len(A), bars=sum(a["award_no"] == 2 for a in A),
                   posthumous=sum(a["posthumous"] for a in people), wikidata_matched=sum(a["wikidata"] is not None for a in people),
                   birth_coords=sum(a["birth_lat"] is not None for a in people), birth_precise=sum(a["birth_precision"] == "place" for a in people),
                   birth_country_only=sum(a["birth_precision"] == "country" for a in people),
                   wikidata_rows=None, multi_birthplace=J["multi_bp"],
                   place_any=sum(a["place_text"] is not None for a in A), place_precise=sum(a["place_precision"] == "place" for a in A),
                   place_region_only=sum(a["place_precision"] == "region" for a in A),
                   place_from_lists=sum(a["place_precision"] == "place" and a["place_method"] != "wikidata_p607_battle" for a in A),
                   place_from_wikidata=sum(a["place_method"] == "wikidata_p607_battle" for a in A),
                   distance_n=sum(a["dist_ok"] for a in A), region_known=sum(a["region"] is not None for a in A),
                   first_year=min(a["year"] for a in A), last_year=max(a["year"] for a in A))
R["counts"]["share_place_precise"] = R["counts"]["place_precise"] / len(A)
R["counts"]["share_distance"] = R["counts"]["distance_n"] / len(A)
R["counts"]["share_birth"] = R["counts"]["birth_coords"] / len(people)
R["counts"]["share_region"] = R["counts"]["region_known"] / len(A)
R["fixes"] = FIX
R["unjoined_national_rows"] = J["unjoined"]

# geocoding audit
G = J["geo_rows"]
R["geocoding"] = dict(rows=len(G), by_method=dict(Counter(g["method"] for g in G)),
                      precise=sum(g["precision"] == "place" for g in G), region=sum(g["precision"] == "region" for g in G),
                      unmatched=sum(g["method"] == "unmatched" for g in G),
                      by_list={l: dict(rows=sum(g["list"] == l for g in G), precise=sum(g["list"] == l and g["precision"] == "place" for g in G)) for l in sorted({g["list"] for g in G})})
R["geocoding"]["share_unmatched"] = R["geocoding"]["unmatched"] / len(G)
R["geocoding"]["share_precise"] = R["geocoding"]["precise"] / len(G)

# conflicts
gl = {k: n for k, n, *_ in GROUPS}
R["groups"] = [dict(key=k, label=n, awards=sum(a["group"] == k for a in A),
                    place_precise=sum(a["group"] == k and a["place_precision"] == "place" for a in A),
                    distance_n=sum(a["group"] == k and a["dist_ok"] for a in A),
                    posthumous=sum(a["group"] == k and a["posthumous"] for a in A)) for k, n, *_ in GROUPS]
for g in R["groups"]:
    g["share_place"] = g["place_precise"] / g["awards"]
    d = [a["distance_km"] for a in A if a["group"] == g["key"] and a["dist_ok"]]
    g["median_km"] = st.median(d) if d else None
camp = Counter(a["campaign"] for a in A)
R["campaigns"] = [dict(campaign=c, awards=n) for c, n in camp.most_common()]
R["southern_africa"] = dict(awards=sum(a["southern_africa_war"] for a in A), boer2=camp["Second Boer War"], zulu=camp["Anglo-Zulu War"], boer1=camp["First Boer War"])
R["years"] = {str(y): n for y, n in sorted(Counter(a["year"] for a in A).items())}
peak = max(R["years"].items(), key=lambda kv: kv[1])
R["peak_year"] = dict(year=int(peak[0]), awards=peak[1])
R["ww1_share"] = camp["First World War"] / len(A)
R["pre1914"] = sum(a["year"] < 1914 for a in A)
R["since1946"] = sum(a["year"] >= 1946 for a in A)
first = min(A, key=lambda a: a["date_sort"] or "9999")
R["first_action"] = dict(name=first["name"], date=first["date_text"], place=first["place_text"], birthplace=first["birthplace"])
last = max(A, key=lambda a: a["date_sort"] or "0")
R["last_action"] = dict(name=last["name"], date=last["date_text"], year=last["year"], campaign=last["campaign"])

# births
R["birth_groups"] = dict(Counter(a["birth_group"] for a in people))
R["birth_countries"] = [dict(country=c, n=n) for c, n in Counter(a["birth_country"] for a in people if a["birth_country"]).most_common(25)]
ire = [a for a in people if a["birth_group"] == "Ireland"]
R["ireland"] = dict(n=len(ire), share=len(ire) / len(people), republic=sum(a["birth_iso"] == "IE" for a in ire), north=sum(a["birth_iso"] == "GB-NIR" for a in ire))
BG_ORDER = ["England", "Scotland", "Wales", "Ireland", "South Asia", "Australia", "Canada", "New Zealand", "Southern Africa", "Elsewhere", "Not known"]
R["birth_group_order"] = BG_ORDER
R["birth_by_group"] = {}
for k, n, *_ in GROUPS:
    sub = [a for a in A if a["group"] == k]
    c = Counter(a["birth_group"] for a in sub)
    R["birth_by_group"][k] = {b: c.get(b, 0) for b in BG_ORDER}
    R["birth_by_group"][k]["total"] = len(sub)
for b in BG_ORDER:
    R.setdefault("birth_totals", {})[b] = sum(a["birth_group"] == b for a in people)
R["birth_totals"]["Great Britain, county not found"] = sum(a["birth_group"] == "Great Britain, county not found" for a in people)
# Irish share by era
R["irish_share_by_group"] = {k: R["birth_by_group"][k]["Ireland"] / R["birth_by_group"][k]["total"] for k, *_ in GROUPS}
R["dominion_share_by_group"] = {k: sum(R["birth_by_group"][k][b] for b in ("Australia", "Canada", "New Zealand", "Southern Africa")) / R["birth_by_group"][k]["total"] for k, *_ in GROUPS}
R["southasia_share_by_group"] = {k: R["birth_by_group"][k]["South Asia"] / R["birth_by_group"][k]["total"] for k, *_ in GROUPS}
# born in India to British families vs Indian Army: just counts by birth group; nothing more is claimed
towns = Counter(a["birthplace"] for a in people if a["birthplace"] and a["birth_precision"] == "place")
R["top_towns"] = [dict(town=t, n=n, country=next(a["birth_country"] for a in people if a["birthplace"] == t)) for t, n in towns.most_common(25)]
cnt = Counter(a["birth_county"] for a in people if a["birth_county"])
R["top_counties"] = [dict(county=c, n=n) for c, n in cnt.most_common(20)]
R["birth_share"] = {b: R["birth_totals"][b] / len(people) for b in BG_ORDER}
R["gb_births"] = sum(a["birth_iso"] == "GB" for a in people)
R["nations"] = dict(Counter(a["birth_nation"] for a in people if a["birth_nation"]))
london = [a for a in people if a["birth_county"] == "Greater London"]
R["london"] = dict(n=len(london), share=len(london) / len(people))

# Lancashire: today's Lancashire, Greater Manchester and Merseyside
LANC = ("Lancashire", "Greater Manchester", "Merseyside")
lanc = sorted([a for a in people if a["birth_county"] in LANC], key=lambda a: a["year"])
R["lancashire"] = dict(n=len(lanc), by_county={c: sum(a["birth_county"] == c for a in lanc) for c in LANC},
                       by_group=dict(Counter(gl[a["group"]] for a in lanc)),
                       towns=[dict(town=t, n=n) for t, n in Counter(a["birthplace"] for a in lanc).most_common(12)],
                       posthumous=sum(a["posthumous"] for a in lanc),
                       people=[dict(name=a["name"], born=a["birthplace"], county=a["birth_county"], year=a["year"], campaign=a["campaign"],
                                    unit=a["unit"], place=a["place_text"] if a["place_precision"] in ("place", "region") else None,
                                    posthumous=a["posthumous"], article=a["title"]) for a in lanc])
R["lancashire"]["rank_combined"] = None
# rank of the combined area against single counties
cnt2 = Counter(cnt); comb = sum(cnt[c] for c in LANC)
R["lancashire"]["combined_vs"] = [dict(county=c, n=n) for c, n in cnt.most_common(3)]
R["lancashire"]["combined_rank"] = 1 + sum(1 for c, n in cnt.items() if c not in LANC and n > len(lanc))
R["lancashire"]["share"] = len(lanc) / len(people)
R["lancashire"]["share_of_england"] = len(lanc) / R["birth_totals"]["England"]
R["lancashire"]["ww1"] = sum(a["group"] == "ww1" for a in lanc)
R["lancashire"]["with_place"] = sum(a["place_precision"] == "place" for a in lanc)

# places of action: hot spots (greedy clusters of precise places within RAD km of the densest point)
RAD = 15
pts = [a for a in A if a["place_precision"] == "place"]
pts.sort(key=lambda a: a["place_text"])
clusters = []
for a in sorted(pts, key=lambda a: -sum(1 for b in pts if hav((a["place_lat"], a["place_lon"]), (b["place_lat"], b["place_lon"])) <= RAD)):
    if a.get("_c") is not None: continue
    mem = [b for b in pts if b.get("_c") is None and hav((a["place_lat"], a["place_lon"]), (b["place_lat"], b["place_lon"])) <= RAD]
    cid = len(clusters)
    for b in mem: b["_c"] = cid
    names = Counter(re.sub(r"^(Siege|Battle|Relief) of (the )?", "", re.split(r",", b["place_text"])[0].strip()) for b in mem)
    clusters.append(dict(id=cid, lat=a["place_lat"], lon=a["place_lon"], n=len(mem), names=[n for n, _ in names.most_common(4)],
                         groups=dict(Counter(gl[b["group"]] for b in mem)),
                         years=[min(b["year"] for b in mem), max(b["year"] for b in mem)]))
clusters.sort(key=lambda c: -c["n"])
R["hotspots"] = [dict(rank=i + 1, **{k: v for k, v in c.items() if k != "id"}) for i, c in enumerate(clusters[:15])]
R["hotspot_clusters"] = len(clusters)
R["hotspot_radius"] = RAD
R["doi"] = "10.5281/zenodo.23677831"
def _hot(word):
    for c in clusters:
        if any(word.lower() in n.lower() for n in c["names"]): return dict(n=c["n"], names=c["names"], rank=clusters.index(c) + 1)
R["hot"] = {k: _hot(w) for k, w in [("ypres", "Ypres"), ("somme", "Somme"), ("lucknow", "Lucknow"), ("sevastopol", "Sevastopol"), ("delhi", "Delhi"),
                                    ("rorke", "Rorke"), ("gallipoli", "Gallipoli"), ("cambrai", "Cambrai"), ("lens", "Lens")]}
R["regions"] = [dict(region=r, awards=n, from_place=sum(a["region"] == r and a["region_from"] == "place of action" for a in A)) for r, n in Counter(a["region"] for a in A if a["region"]).most_common()]
R["regions_ww_unknown"] = sum(a["region"] is None for a in A)

# distances
dd = [a for a in A if a["dist_ok"]]
D = sorted(a["distance_km"] for a in dd)
q = lambda p: D[min(len(D) - 1, int(round(p * (len(D) - 1))))]
R["distance"] = dict(n=len(D), median=st.median(D), mean=st.mean(D), q25=q(.25), q75=q(.75), max=D[-1], min=D[0],
                     over_5000=sum(d > 5000 for d in D), over_10000=sum(d > 10000 for d in D), under_1000=sum(d < 1000 for d in D),
                     under_500=sum(d < 500 for d in D))
R["distance"]["share_over_5000"] = R["distance"]["over_5000"] / len(D)
R["distance"]["share_under_1000"] = R["distance"]["under_1000"] / len(D)
R["distance_by_birth"] = []
for b in BG_ORDER:
    d = [a["distance_km"] for a in dd if a["birth_group"] == b]
    if len(d) >= 5: R["distance_by_birth"].append(dict(group=b, n=len(d), median=st.median(d), q25=sorted(d)[len(d) // 4], q75=sorted(d)[(3 * len(d)) // 4]))
R["distance_by_conflict"] = []
for k, n, *_ in GROUPS:
    d = [a["distance_km"] for a in dd if a["group"] == k]
    if d: R["distance_by_conflict"].append(dict(key=k, label=n, n=len(d), median=st.median(d)))
# adjusted median: weight each award in the subset so that birth group x conflict group cells match the full list
cellA = Counter((a["birth_group"], a["group"]) for a in A); cellD = Counter((a["birth_group"], a["group"]) for a in dd)
wts = [(a["distance_km"], cellA[(a["birth_group"], a["group"])] / cellD[(a["birth_group"], a["group"])]) for a in dd]
wts.sort(); tot = sum(w for _, w in wts); acc = 0; wmed = None
for d, w in wts:
    acc += w
    if acc >= tot / 2: wmed = d; break
covered = sum(cellA[c] for c in cellD)
R["distance"]["adjusted_median"] = wmed
R["distance"]["adjusted_cover"] = covered / len(A)
R["distance"]["adjusted_share_over_5000"] = sum(w for d, w in wts if d > 5000) / tot
R["distance"]["adjusted_share_under_1000"] = sum(w for d, w in wts if d < 1000) / tot
far = sorted(dd, key=lambda a: -a["distance_km"])[:5]; near = sorted(dd, key=lambda a: a["distance_km"])[:5]
f = lambda a: dict(name=a["name"], born=a["birthplace"], place=a["place_text"], year=a["year"], km=a["distance_km"], campaign=a["campaign"])
R["farthest"] = [f(a) for a in far]; R["nearest"] = [f(a) for a in near]
# coverage bias of the distance subset
R["distance_subset_birth"] = {b: sum(a["birth_group"] == b for a in dd) for b in BG_ORDER}
R["distance_subset_share"] = {b: (sum(a["birth_group"] == b for a in dd) / len(dd)) for b in BG_ORDER}
R["all_share"] = {b: (sum(a["birth_group"] == b for a in A) / len(A)) for b in BG_ORDER}
# England-born subset sensitivity: medians for England-born in WW1 only
for b in ("England", "Scotland", "Ireland", "Australia", "Canada", "New Zealand", "South Asia"):
    d = [a["distance_km"] for a in dd if a["birth_group"] == b and a["group"] == "ww1"]
    R.setdefault("ww1_distance_by_birth", {})[b] = dict(n=len(d), median=st.median(d) if d else None)
R["posthumous_share"] = R["counts"]["posthumous"] / len(people)
R["posthumous_ww1"] = sum(a["posthumous"] for a in A if a["group"] == "ww1")
R["posthumous_ww2"] = sum(a["posthumous"] for a in A if a["group"] == "ww2")

# ---------- outputs ----------
json.dump(R, open(os.path.join(ROOT, "data", "results.json"), "w"), indent=1, ensure_ascii=False)
OUT = ["title", "name", "award_no", "rank", "unit", "campaign", "group", "year", "date_text", "posthumous", "wikidata", "dob",
       "birthplace", "birthplace_qid", "birth_lat", "birth_lon", "birth_precision", "birth_country", "birth_county", "birth_group",
       "place_text", "place_list", "place_lat", "place_lon", "place_precision", "place_method", "place_matched", "place_source",
       "region", "region_from", "distance_km"]
with open(os.path.join(ROOT, "data", "vc_awards.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["wikipedia_article"] + OUT[1:] + ["conflict_group"])
    for a in sorted(A, key=lambda a: (a["date_sort"] or "9999", a["name"])):
        w.writerow(["" if a[k] is None else a[k] for k in OUT] + [gl[a["group"]]])
with open(os.path.join(ROOT, "data", "birth_places.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["birthplace", "wikidata", "lat", "lon", "country", "gb_county", "recipients"])
    bp = defaultdict(list)
    for a in people:
        if a["birth_lat"] is not None: bp[(a["birthplace"], a["birthplace_qid"])].append(a)
    for (n, qid), l in sorted(bp.items(), key=lambda kv: -len(kv[1])):
        w.writerow([n, qid, l[0]["birth_lat"], l[0]["birth_lon"], l[0]["birth_country"], l[0]["birth_county"] or "", len(l)])
with open(os.path.join(ROOT, "data", "birth_counties_gb.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["county", "nation", "recipients_born"])
    for c, n in cnt.most_common():
        w.writerow([c, next(a["birth_nation"] for a in people if a["birth_county"] == c), n])
with open(os.path.join(ROOT, "data", "hotspots.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["rank", "lat", "lon", "awards", "place_names", "conflicts", "first_year", "last_year"])
    for i, c in enumerate(clusters):
        w.writerow([i + 1, c["lat"], c["lon"], c["n"], "; ".join(c["names"]), "; ".join(f"{k} {v}" for k, v in c["groups"].items()), *c["years"]])
feats = [dict(type="Feature", geometry=dict(type="LineString", coordinates=[[a["birth_lon"], a["birth_lat"]], [a["place_lon"], a["place_lat"]]]),
              properties=dict(name=a["name"], article=a["title"], year=a["year"], campaign=a["campaign"], group=gl[a["group"]],
                              born=a["birthplace"], place=a["place_text"], distance_km=a["distance_km"])) for a in dd]
json.dump(dict(type="FeatureCollection", features=feats), open(os.path.join(ROOT, "data", "flows.geojson"), "w"), ensure_ascii=False)

# compact page data: one array per award
GK = [k for k, *_ in GROUPS]
BGI = {b: i for i, b in enumerate(BG_ORDER + ["Great Britain, county not found"])}
rows = []
for a in sorted(A, key=lambda a: (a["date_sort"] or "9999")):
    rd = lambda v: None if v is None else round(v, 3)
    rows.append([a["name"], a["title"], a["rank"], a["unit"], a["campaign"], GK.index(a["group"]), a["year"], a["date_text"], int(a["posthumous"]),
                 a["birthplace"], rd(a["birth_lat"]), rd(a["birth_lon"]), BGI[a["birth_group"]], a["birth_county"],
                 a["place_text"], rd(a["place_lat"]) if a["place_precision"] == "place" else None, rd(a["place_lon"]) if a["place_precision"] == "place" else None,
                 a["distance_km"] if a["dist_ok"] else None, a["wikidata"]])
site = dict(rows=rows, groups=[[k, n] for k, n, *_ in GROUPS], bg=BG_ORDER + ["Great Britain, county not found"], R=R)
json.dump(site, open(os.path.join(ROOT, "work", "site.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print(json.dumps({k: R[k] for k in ("counts", "groups", "distance", "birth_totals", "ireland", "lancashire")}, indent=0, ensure_ascii=False)[:6000])
print("hotspots", [(h["names"][:2], h["n"]) for h in R["hotspots"]])
print("towns", [(t["town"], t["n"]) for t in R["top_towns"][:15]])
print("regions", R["regions"], R["regions_ww_unknown"])
print("dist by birth", R["distance_by_birth"])
print("far", R["farthest"][:3], "near", R["nearest"][:3])
print("site kB", os.path.getsize(os.path.join(ROOT, "work", "site.json")) // 1024)
