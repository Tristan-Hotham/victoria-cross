"""Step 1: parse the Wikipedia Victoria Cross lists into tables.

Inputs (read in place, not copied):
  _data2/wikipedia_vc_wikitext.json   wikitext of the Wikipedia lists (CC BY-SA 4.0)
Outputs:
  work/master.json     one row per entry in "List of Victoria Cross recipients (A-F)", "(G-M)", "(N-Z)"
  work/places.json     one row per entry in the national lists that give a "Place of action" column
Run: python3 01_parse_lists.py
"""
import os, re, json, html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA2 = "/home/claude/hist/_data2"
W = json.load(open(os.path.join(DATA2, "wikipedia_vc_wikitext.json")))
os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)


def strip_refs(s):
    s = re.sub(r"<ref[^>/]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"\{\{(?:efn|ref label|Ref label|refn|#tag:ref)[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*\}\}", "", s, flags=re.S)
    return s


def split_cells(row):
    """Split a wikitable row into cells, respecting [[...]] and {{...}}."""
    lines = row.strip("\n").split("\n")
    out = []
    for ln in lines:
        if not ln or ln[0] not in "|!":
            if out: out[-1] += " " + ln
            continue
        body = ln[1:]
        # split on || or !! outside brackets
        parts, depth, cur, i = [], 0, "", 0
        while i < len(body):
            two = body[i:i + 2]
            if two in ("[[", "{{"): depth += 1; cur += two; i += 2; continue
            if two in ("]]", "}}"): depth -= 1; cur += two; i += 2; continue
            if depth == 0 and two in ("||", "!!"): parts.append(cur); cur = ""; i += 2; continue
            cur += body[i]; i += 1
        parts.append(cur)
        out.extend(parts)
    # drop cell attributes like style="..."| (a single | outside brackets before content)
    clean = []
    for c in out:
        depth, cut = 0, None
        for i in range(len(c)):
            two = c[i:i + 2]
            if two in ("[[", "{{"): depth += 1
            elif two in ("]]", "}}"): depth -= 1
            elif c[i] == "|" and depth == 0 and (i == 0 or c[i - 1] != "|"):
                pre = c[:i]
                if re.search(r"(style|align|scope|class|rowspan|colspan|data-sort-value)\s*=", pre): cut = i
                break
        clean.append(c[cut + 1:] if cut is not None else c)
    return clean


def links(s):
    """Return list of (target, display) for wikilinks in s."""
    return [(m.group(1).strip(), (m.group(2) or m.group(1)).strip()) for m in re.finditer(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]", s)]


def plain(s):
    s = strip_refs(s)
    s = re.sub(r'<span style="display:none">.*?</span>', "", s)
    s = re.sub(r"\{\{sort\|[^|]*\|(.*?)\}\}", r"\1", s)
    s = re.sub(r"\{\{(?:HMS|HMAS|HMNZS|SS|HMCS)\|([^|}]*)(?:\|[^}]*)?\}\}", r"HMS \1", s)
    s = re.sub(r"\{\{sortname\|([^|}]*)\|([^|}]*)(?:\|[^}]*)?\}\}", r"\1 \2", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", s).strip()


def name_cell(c):
    """Return (article title, display name)."""
    c = strip_refs(c)
    m = re.search(r"\{\{sortname\|([^}]*)\}\}", c)
    if m:
        parts = m.group(1).split("|")
        pos = [p for p in parts if "=" not in p]
        kw = dict(p.split("=", 1) for p in parts if "=" in p)
        first, last = pos[0].strip(), pos[1].strip()
        disp = f"{first} {last}".strip()
        if len(pos) >= 3 and pos[2].strip():
            title = pos[2].strip()
        else:
            title = disp + (f" ({kw['dab'].strip()})" if kw.get("dab") else "")
        return title, disp
    L = links(c)
    if L: return L[0][0], plain(c)
    return None, plain(c)


def rows_of(text):
    out = []
    for tb in re.finditer(r"\{\|.*?\n\|\}", text, flags=re.S):
        t = tb.group(0)
        for r in re.split(r"\n\|-[^\n]*", t)[1:]:
            if r.strip().startswith("!") and "scope=\"row\"" not in r and "sortname" not in r and "[[" not in r.split("\n")[0][:5]:
                continue
            out.append(r)
    return out


# ---------- master A to Z list ----------
master = []
for page in ["List of Victoria Cross recipients (A–F)", "List of Victoria Cross recipients (G–M)", "List of Victoria Cross recipients (N–Z)"]:
    for r in rows_of(W[page]["wt"]):
        c = split_cells(r)
        if len(c) < 5: continue
        title, disp = name_cell(c[0])
        if not disp: continue
        camp_links = links(strip_refs(c[3]))
        dm = re.search(r'<span style="display:none">(\d{4})-(\d{2})-(\d{2})</span>', c[4])
        unit_links = links(strip_refs(c[2]))
        master.append({
            "title": title, "name": disp, "rank": plain(c[1]), "unit": plain(c[2]),
            "unit_link": unit_links[0][0] if unit_links else None,
            "campaign": plain(c[3]), "campaign_link": camp_links[0][0] if camp_links else None,
            "date_sort": f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else None,
            "date_text": plain(c[4]).replace("*", "").strip(),
            "posthumous": "*" in plain(c[4]) or "e3d9ff" in c[4],
            "page": page.replace("–", " to "),
        })
print("master rows", len(master))

# ---------- national lists with a Place of action column ----------
NAT = {
    "List of Irish Victoria Cross recipients": "Irish",
    "List of Victoria Cross recipients of the Indian Army": "Indian Army",
    "List of Australian Victoria Cross recipients": "Australian",
    "List of Canadian Victoria Cross recipients": "Canadian",
    "List of New Zealand Victoria Cross recipients": "New Zealand",
    "List of Victoria Cross recipients by nationality": "By nationality",
}
places = []
for page, tag in NAT.items():
    t = W[page]["wt"]
    for tb in re.finditer(r"\{\|.*?\n\|\}", t, flags=re.S):
        tbt = tb.group(0)
        hdr = re.search(r"\n!(.*?)\n\|-", tbt, flags=re.S)
        if not hdr: continue
        heads = [plain(h) for h in split_cells("!" + hdr.group(1).replace("\n!", "!!"))]
        heads = [re.sub(r"\s+", " ", h).strip() for h in heads]
        if "Place of action" not in heads: continue
        ip = heads.index("Place of action"); idate = heads.index("Date of action"); icf = heads.index("Conflict")
        inat = heads.index("Nationality") if "Nationality" in heads else None
        iprov = next((i for i, h in enumerate(heads) if h.startswith("Province")), None)
        for r in re.split(r"\n\|-[^\n]*", tbt)[1:]:
            c = split_cells(r)
            if len(c) <= ip: continue
            title, disp = name_cell(c[0])
            if not title or "List of" in (title or ""): continue
            pc = strip_refs(c[ip])
            places.append({
                "list": tag, "title": title, "name": disp,
                "year": plain(c[idate]).replace("*", "").strip(),
                "conflict": plain(c[icf]),
                "place_text": plain(pc), "place_links": [l[0] for l in links(pc)],
                "nationality": plain(c[inat]) if inat is not None else None,
                "province": plain(c[iprov]) if iprov is not None else None,
            })
print("national-list rows", len(places))
from collections import Counter
print(Counter(p["list"] for p in places))
json.dump(master, open(os.path.join(ROOT, "work", "master.json"), "w"), ensure_ascii=False, indent=0)
json.dump(places, open(os.path.join(ROOT, "work", "places.json"), "w"), ensure_ascii=False, indent=0)
