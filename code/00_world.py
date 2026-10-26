"""Step 0: a small world outline for the static maps and for classifying birthplaces by country.

Source: Natural Earth 1:50m Admin 0 countries (public domain), from the
natural-earth-vector repository on GitHub (github.com/nvkelso/natural-earth-vector,
geojson/ne_50m_admin_0_countries.geojson). Pass its path as NE50 or leave the default.
Output: work/world.json  {"countries": [{"name", "iso", "geom"}], "land": geom}
  with geometries simplified to 0.05 degrees for drawing.
Also splits the island of Ireland (Republic of Ireland plus Northern Ireland) out of the
United Kingdom polygon, so births can be put in "Ireland (island)" or "Great Britain".
Run: python3 00_world.py
"""
import os, json
from shapely.geometry import shape, mapping, MultiPolygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
NE50 = os.environ.get("NE50", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/sw/ne/geojson/ne_50m_admin_0_countries.geojson")
g = json.load(open(NE50))
out = []
full = []
for f in g["features"]:
    p = f["properties"]; geom = shape(f["geometry"])
    name = p.get("NAME_EN") or p.get("NAME"); iso = p.get("ISO_A2_EH") or p.get("ISO_A2")
    full.append((name, iso, geom))
uk = next(x for x in full if x[1] == "GB"); ie = next(x for x in full if x[1] == "IE")
parts = list(uk[2].geoms) if isinstance(uk[2], MultiPolygon) else [uk[2]]
ni = [q for q in parts if q.buffer(0.05).intersects(ie[2])]
rest = [q for q in parts if q not in ni]
for name, iso, geom in full:
    if iso == "GB":
        out.append({"name": "Northern Ireland", "iso": "GB-NIR", "geom": mapping(unary_union(ni).simplify(0.01))})
        out.append({"name": "Great Britain", "iso": "GB", "geom": mapping(unary_union(rest).simplify(0.01))})
        continue
    out.append({"name": name, "iso": iso, "geom": mapping(geom.simplify(0.02 if iso in ("IE",) else 0.05, preserve_topology=True))})
land = unary_union([shape(c["geom"]) for c in out]).simplify(0.05)
os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
json.dump({"countries": out, "land": mapping(land), "source": "Natural Earth 1:50m Admin 0 countries, public domain, via github.com/nvkelso/natural-earth-vector"},
          open(os.path.join(ROOT, "work", "world.json"), "w"))
print("countries", len(out), "kB", os.path.getsize(os.path.join(ROOT, "work", "world.json")) // 1024)
