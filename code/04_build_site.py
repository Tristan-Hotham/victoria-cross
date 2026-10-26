"""Step 4: build ../index.html from page_template.html and ../README.md from README_template.md.

Every number in the text is a placeholder like {{counts.awards|int}} filled from
../data/results.json, and the compact page data (../work/site.json) is embedded as `const D = ...`.
Formats: int (thousands commas), pct0, pct1, f1, raw.
Run: python3 04_build_site.py
"""
import os, re, json

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
site = open(os.path.join(ROOT, "work", "site.json")).read()
# some Wikipedia unit and place names carry en dashes; show them as plain hyphens on the page
site = site.replace("–", "-").replace("—", "-")


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{int(round(v)):,}"
    if f == "pct0": return f"{v * 100:.0f}%"
    if f == "pct1": return f"{v * 100:.1f}%"
    if f == "f1": return f"{v:.1f}"
    return str(v)


def sub(m):
    path, _, f = m.group(1).partition("|")
    return fmt(get(path.strip()), f.strip() or "raw")


t = open(os.path.join(HERE, "page_template.html")).read()
t = re.sub(r"\{\{(.+?)\}\}", sub, t)
t = t.replace("/*DATA*/", "const D = " + site + ";")
open(os.path.join(ROOT, "index.html"), "w").write(t)
print("index.html", len(t.encode()) // 1024, "KB")
md = re.sub(r"\{\{(.+?)\}\}", sub, open(os.path.join(HERE, "README_template.md")).read())
open(os.path.join(ROOT, "README.md"), "w").write(md)
print("README.md written")
