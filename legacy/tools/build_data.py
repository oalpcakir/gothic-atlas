"""Build site/index.html from site/src.html + data/wd.json + data/metropole.geojson.

Wikidata gives the list (name, city, coordinates, Mérimée id, style, dates, heights).
Its dates and heights are noisy (Romanesque predecessors, spires vs vaults, cm vs m),
so CURATED below overrides the start of Gothic works and gives nave vault heights
for the well-documented cathedrals. Values are approximate, as commonly cited.
"""
import json, math, sys, pathlib, re

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent

# qid: (gothic_start, vault_m, note)  -- None keeps Wikidata / leaves empty
CURATED = {
    "Q184407": (1140, 29, "Abbot Suger's choir (1140-44): the first Gothic choir."),
    "Q489014": (1140, 24.4, "Often called the first Gothic cathedral."),
    "Q932828": (1150, 22.7, None),
    "Q1736217": (1153, None, None),
    "Q585947": (1160, 24, "Famous for the stone oxen on its towers."),
    "Q2981": (1163, 33, "Flying buttresses added around 1180, among the first anywhere."),
    "Q1736223": (1177, 30, None),
    "Q476516": (1185, 28, "Tallest building in the world 1876-1880 (cast-iron spire)."),
    "Q180274": (1194, 36.5, "Rebuilt after the 1194 fire; most of its 12th/13th-c. glass survives."),
    "Q207985": (1195, 37.5, "No transept: five aisles in one huge stepped section."),
    "Q2443243": (1208, 28.5, None),
    "Q206823": (1211, 38, "Coronation church of the French kings."),
    "Q1518999": (1215, 30, None),
    "Q1351690": (1221, 30, None),
    "Q106934": (1220, 42.3, "Largest cathedral in France by volume."),
    "Q513300": (1225, 48.5, "Highest Gothic vault ever built; the choir vault fell in 1284."),
    "Q745460": (1225, 32, "Its 142 m spire made it the world's tallest building 1647-1874."),
    "Q671066": (1220, 41.4, "Called 'God's lantern' for its huge glass area."),
    "Q1636244": (1230, None, None),
    "Q2419151": (1239, None, None),
    "Q547013": (1170, 29, None),
    "Q2189282": (1273, None, None),
    "Q473121": (1272, 41, "Only the choir was finished; the nave was never built."),
    "Q94744": (1282, 30, "Brick fortress-cathedral of the south."),
    "Q1788518": (1454, None, "Gothic choir added to a Romanesque church."),
    "Q1135277": (None, None, None),
    "Q2310816": (None, None, None),
    "Q656738": (None, None, None),
    "Q1736197": (1364, None, None),
    "Q1366553": (1601, None, "Rebuilt in Gothic style 1601-1829 after the Wars of Religion."),
}
DROP_HEIGHT = {"Q1736197"}  # 2850 is cm or junk


def period(styles, start):
    s = " ".join(styles).lower()
    if "brick" in s or "meridional" in s:
        return "south"
    if "flamboyant" in s:
        return "flamboyant"
    if "rayonnant" in s and "classic" not in s:
        return "rayonnant"
    if start is None:
        return "gothic"
    if start < 1190:
        return "early"
    if start < 1240:
        return "high"
    if start < 1350:
        return "rayonnant"
    return "flamboyant"


def cathedrals():
    rows = json.load(open(ROOT / "data/wd.json", encoding="utf-8"))["results"]["bindings"]
    by = {}
    for b in rows:
        q = b["c"]["value"].rsplit("/", 1)[1]
        lon, lat = map(float, re.findall(r"-?[\d.]+", b["coord"]["value"]))
        r = by.setdefault(q, dict(id=q, name=b["cLabel"]["value"], city=b.get("cityLabel", {}).get("value"),
                                  lat=lat, lon=lon, years=set(), heights=set(), styles=set(),
                                  merimee=b.get("merimee", {}).get("value"), wiki=b.get("article", {}).get("value")))
        if "inception" in b:
            r["years"].add(int(b["inception"]["value"][:5].strip("-+") or 0))
        if "height" in b:
            r["heights"].add(float(b["height"]["value"]))
        r["styles"].add(b["styleLabel"]["value"])
    out = []
    for q, r in by.items():
        start = min(r["years"]) if r["years"] else None
        if start is not None and start < 1130:
            start = None  # Romanesque or earlier predecessor, not the Gothic works
        vault, note, src = None, None, "wikidata"
        if q in CURATED:
            cs, cv, note = CURATED[q]
            start, vault, src = cs, cv, "curated"
        heights = sorted(h for h in r["heights"] if h < 200 and q not in DROP_HEIGHT)
        if r["city"] and r["city"].startswith(("Quartier", "Roman Catholic", "5th arr")):
            r["city"] = {"Q2981": "Paris", "Q1521": "Lyon"}.get(q, r["city"].split(" of ")[-1])
        out.append(dict(id=q, name=r["name"], city=r["city"], lat=round(r["lat"], 4), lon=round(r["lon"], 4),
                        start=start, vault=vault, tallest=heights[-1] if heights else None,
                        period=period(r["styles"], start), styles=sorted(r["styles"]),
                        merimee=r["merimee"], wiki=r["wiki"], note=note, src=src))
    out.sort(key=lambda c: (c["start"] is None, c["start"] or 0, c["name"]))
    return out


# Equirectangular, scaled by cos(46.5) so France keeps its shape. viewBox 0 0 600 600.
LON0, LAT1, K = -5.4, 51.3, 600 / 15.6
COS = math.cos(math.radians(46.5))


def proj(lon, lat):
    return round((lon - LON0) * COS * K + 8, 1), round((LAT1 - lat) * K + 8, 1)


def france_path():
    g = json.load(open(ROOT / "data/metropole.geojson", encoding="utf-8"))["geometry"]
    parts = []
    for poly in g["coordinates"]:
        ring = poly[0]
        if len(ring) < 12:
            continue  # small islands
        pts, last = [], None
        for lon, lat in ring:
            p = proj(lon, lat)
            if last and abs(p[0] - last[0]) + abs(p[1] - last[1]) < 1.2:
                continue
            pts.append(p)
            last = p
        parts.append("M" + "L".join(f"{x},{y}" for x, y in pts) + "Z")
    return "".join(parts)


def main():
    cats = cathedrals()
    for c in cats:
        c["x"], c["y"] = proj(c["lon"], c["lat"])
    data = dict(cathedrals=cats, france=france_path())
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    src = (ROOT / "site/src.html").read_text(encoding="utf-8")
    html = src.replace("/*@DATA@*/null", blob)
    (ROOT / "site/index.html").write_text(html, encoding="utf-8")
    dated = sum(c["start"] is not None for c in cats)
    print(f"{len(cats)} cathedrals, {dated} dated, {sum(c['vault'] is not None for c in cats)} with vault height;"
          f" data {len(blob)//1024} KB -> site/index.html")


if __name__ == "__main__":
    main()
