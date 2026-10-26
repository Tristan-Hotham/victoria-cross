"""Step 5: render ../header.png (1200x630 social card) with Playwright Chromium.

Draws the world outline (Natural Earth, work/world.json) and every located birthplace-to-deed line.
Fonts: pass a folder of TTFs as FONT_DIR (FrauncesVar.ttf, SourceSerif4-Regular.ttf, IBMPlexMono-Regular.ttf,
IBMPlexMono-Medium.ttf); otherwise system fonts are used.
Run: python3 05_header.py
"""
import os, json, math
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
S = json.load(open(os.path.join(ROOT, "work", "site.json"))); R = S["R"]
W0 = json.load(open(os.path.join(ROOT, "work", "world.json")))
FD = os.environ.get("FONT_DIR", "")
COL = ["#7FA8DA", "#D9A441", "#93B85B", "#E0566A", "#B497D9", "#4FBDBD", "#EE8E4C"]
# equirectangular crop: lon -20..180, lat -50..65 into a 640x420 box
LON0, LON1, LAT0, LAT1, BW = -25, 180, -50, 66, 590
BH = BW * (LAT1 - LAT0) / (LON1 - LON0) * 1.15
P = lambda lat, lon: ((lon - LON0) / (LON1 - LON0) * BW, (LAT1 - lat) / (LAT1 - LAT0) * BH)


def rings(g):
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    out = []
    for poly in polys:
        for ring in poly[:1]:
            if all(x < LON0 - 5 or x > LON1 + 5 for x, _ in ring): continue
            out.append("M" + "L".join(f"{P(y, x)[0]:.1f} {P(y, x)[1]:.1f}" for x, y in ring) + "Z")
    return "".join(out)


land = "".join(rings(c["geom"]) for c in W0["countries"])
paths = []
for r in S["rows"]:
    if r[17] is None: continue
    a, b = P(r[10], r[11]), P(r[15], r[16])
    dx, dy = b[0] - a[0], b[1] - a[1]
    c = ((a[0] + b[0]) / 2 + dy * .18, (a[1] + b[1]) / 2 - dx * .18)
    paths.append(f'<path d="M{a[0]:.1f} {a[1]:.1f}Q{c[0]:.1f} {c[1]:.1f} {b[0]:.1f} {b[1]:.1f}" stroke="{COL[r[5]]}"/>')
dots = "".join(f'<circle cx="{P(r[15], r[16])[0]:.1f}" cy="{P(r[15], r[16])[1]:.1f}" r="1.9" fill="{COL[r[5]]}"/>' for r in S["rows"] if r[15] is not None)
ff = ""
if FD:
    ff = "".join(f"@font-face{{font-family:'{n}';src:url('file://{FD}/{f}');font-weight:{w};}}" for n, f, w in [
        ("Fraunces", "FrauncesVar.ttf", "100 900"), ("Source Serif 4", "SourceSerif4-Regular.ttf", "400"),
        ("IBM Plex Mono", "IBMPlexMono-Regular.ttf", "400"), ("IBM Plex Mono", "IBMPlexMono-Medium.ttf", "500")])
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{ff}
body{{margin:0;width:1200px;height:630px;background:#12161F;color:#ECE6DA;overflow:hidden;position:relative;font-family:'Source Serif 4',Georgia,serif}}
.k{{position:absolute;left:70px;top:90px;font:500 15px/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#A39C8E;display:flex;gap:12px;align-items:center}}
.k b{{background:#E0566A;color:#12161F;padding:7px 9px;font-weight:500}}
h1{{position:absolute;left:66px;top:134px;margin:0;font:900 112px/.88 Fraunces,Georgia,serif;letter-spacing:-.02em;font-variation-settings:"SOFT" 50}}
h1 em{{font-style:normal;color:#E0566A;display:block}}
p{{position:absolute;left:70px;top:390px;width:470px;margin:0;font-size:26px;line-height:1.36;color:#DCD5C8}}
.f{{position:absolute;left:70px;bottom:44px;font:400 14px/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#7E7868}}
svg{{position:absolute;right:18px;top:{(630 - BH) / 2:.0f}px}}
</style></head><body>
<div class="k"><b>Data study</b><span>The Victoria Cross</span></div>
<h1>Far from<em>home</em></h1>
<p>{R['counts']['awards']:,} Victoria Crosses: where the recipients were born, and where they won them.</p>
<div class="f">Dr Tristan Hotham · Independent researcher</div>
<svg width="{BW}" height="{BH:.0f}" viewBox="0 0 {BW} {BH:.0f}"><path d="{land}" fill="#1E2535" stroke="#2C3448" stroke-width=".6"/>
<g fill="none" stroke-width=".9" stroke-opacity=".55">{''.join(paths)}</g><g fill-opacity=".95">{dots}</g></svg>
</body></html>"""
tmp = os.path.join(ROOT, "work", "header.html"); open(tmp, "w").write(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 630})
    pg.goto("file://" + os.path.abspath(tmp)); pg.wait_for_timeout(500)
    pg.screenshot(path=os.path.join(ROOT, "header.png")); b.close()
print("header.png written")
