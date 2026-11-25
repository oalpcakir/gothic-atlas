"""Department boundaries and the outline of France from IGN ADMIN EXPRESS (Licence Ouverte 2.0).

    python pipeline/boundaries.py

Uses the small-scale ("PE") cartographic edition, simplifies it for the web and writes
    site/public/data/france-departements.geojson   departments, for the Atlas map
    site/src/data/france-outline.json               outline of mainland France and Corsica, for small maps
"""
import json
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from common import ROOT, http

LAYER = "ADMINEXPRESS-COG-CARTO-PE.2026:departement"
WFS = ("https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES={}"
       "&OUTPUTFORMAT=application/json&SRSNAME=EPSG:4326&COUNT=200")
SOURCE = "IGN, ADMIN EXPRESS COG CARTO PE 2026 (Licence Ouverte 2.0)"


def rounded(geom, nd=4):
    g = mapping(geom)
    r = lambda c: [round(c[0], nd), round(c[1], nd)]
    if g["type"] == "Polygon":
        g["coordinates"] = [[r(c) for c in ring] for ring in g["coordinates"]]
    else:
        g["coordinates"] = [[[r(c) for c in ring] for ring in poly] for poly in g["coordinates"]]
    return g


def main():
    data = json.loads(http(WFS.format(LAYER), tries=3, wait=20))
    feats = []
    for f in data["features"]:
        p = f["properties"]
        code = p.get("code_insee") or p.get("insee_dep") or ""
        if len(code) > 2 and not code.startswith("2"):
            continue  # overseas departments (971...) are not drawn
        g = shape(f["geometry"])
        if g.bounds[0] < -6 or g.bounds[2] > 10:
            continue
        feats.append((code, p.get("nom_officiel") or "", g))
    print(len(feats), "mainland departments")
    out = {"type": "FeatureCollection", "source": SOURCE, "features": [
        {"type": "Feature", "properties": {"code": c, "name": n}, "geometry": rounded(g.simplify(0.004, preserve_topology=True))}
        for c, n, g in feats]}
    p = ROOT / "site" / "public" / "data" / "france-departements.geojson"
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    outline = unary_union([g.buffer(0.0005) for _, _, g in feats]).simplify(0.01, preserve_topology=True)
    q = ROOT / "site" / "src" / "data" / "france-outline.json"
    json.dump({"type": "Feature", "properties": {"source": SOURCE}, "geometry": rounded(outline, 3)}, open(q, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"{p.name} {p.stat().st_size / 1e3:.0f} KB, {q.name} {q.stat().st_size / 1e3:.0f} KB, outline is {outline.geom_type}")


if __name__ == "__main__":
    main()
