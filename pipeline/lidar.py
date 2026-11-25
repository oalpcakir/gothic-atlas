"""Cut each curated cathedral out of the national airborne LiDAR survey (IGN LiDAR HD, Licence Ouverte 2.0).

    python pipeline/lidar.py            # every building that has a file in data/curated/
    python pipeline/lidar.py PA00116046 # one building

For each building: find the 1 km tiles around its Mérimée coordinates, read only the needed part of each
COPC file over HTTP, keep the points classified as building that form one mass with the cathedral,
thin them to a 0.6 m grid and write
    site/public/lidar/<id>.bin   Int16 triples (x east, y north, z up) in decimetres, origin at ground centre
    data/lidar.json              per building: tiles, flight year, point counts, measured heights, side profile
The measured heights are roof and spire tops above local ground. They are not vault heights.
"""
import collections, json, math, sys, time
import numpy as np, laspy, pyproj
from common import OUT, ROOT, http

WFS = ("https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=IGNF_LIDAR-HD_METADONNEE:metadata"
       "&OUTPUTFORMAT=application/json&BBOX={},{},{},{},urn:ogc:def:crs:EPSG::4326")
TO_L93 = pyproj.Transformer.from_crs(4326, 2154, always_xy=True)
TO_WGS = pyproj.Transformer.from_crs(2154, 4326, always_xy=True)
R = 130      # metres around the point that are read
CELL = 2.0   # grid used to find the connected building mass
VOX = 0.6    # thinning grid for the published cloud


def tiles(x, y):
    """Tile records covering the square of side 2R around a Lambert-93 point."""
    lon0, lat0 = TO_WGS.transform(x - R, y - R); lon1, lat1 = TO_WGS.transform(x + R, y + R)
    data = json.loads(http(WFS.format(round(lat0, 6), round(lon0, 6), round(lat1, 6), round(lon1, 6)), tries=3, wait=10))
    return [f["properties"] for f in data["features"]]


def read(url, x, y):
    with laspy.CopcReader.open(url) as rd:
        q = rd.query(laspy.copc.Bounds(mins=np.array([x - R, y - R]), maxs=np.array([x + R, y + R])))
        return np.column_stack([q.x, q.y, q.z]), np.asarray(q.classification)


def building_mass(pts, x, y, ground):
    """Cells of the tall structure nearest the reference point.
    The flood fill only crosses cells whose top is 12 m or more above ground, so cloisters, sacristies and
    neighbouring houses do not pull in the rest of the block; the result is then widened by 4 m to take back
    low chapels and buttress feet."""
    ij = np.floor((pts[:, :2] - [x - R, y - R]) / CELL).astype(int)
    n = int(2 * R / CELL) + 1
    top = np.full((n, n), -1e9)
    np.maximum.at(top, (ij[:, 0], ij[:, 1]), pts[:, 2])
    occ = top > -1e8
    tall = top > ground + 12
    c = n // 2; k = int(40 / CELL)
    win = np.where(tall[c - k:c + k, c - k:c + k], top[c - k:c + k, c - k:c + k], -1e9)
    si, sj = np.unravel_index(np.argmax(win), win.shape); seed = (si + c - k, sj + c - k)
    seen = np.zeros_like(occ); seen[seed] = True; todo = collections.deque([seed])
    while todo:
        i, j = todo.popleft()
        for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if 0 <= a < n and 0 <= b < n and tall[a, b] and not seen[a, b]:
                seen[a, b] = True; todo.append((a, b))
    wide = seen.copy()
    for _ in range(2):
        g = wide.copy()
        g[1:] |= wide[:-1]; g[:-1] |= wide[1:]; g[:, 1:] |= wide[:, :-1]; g[:, :-1] |= wide[:, 1:]
        wide = g
    return wide & occ, ij


def process(b):
    x, y = TO_L93.transform(b["lon"], b["lat"])
    recs = tiles(x, y)
    if not recs:
        return None
    P, C = [], []
    for rec in recs:
        for attempt in range(6):
            try:
                p, c = read(rec["url_npl"], x, y); break
            except Exception as e:  # the download server answers 429 when asked too fast
                if "429" not in repr(e) or attempt == 5:
                    raise
                print("  429, waiting", flush=True); time.sleep(45)
        P.append(p); C.append(c)
    pts, cls = np.vstack(P), np.concatenate(C)
    ground = float(np.median(pts[cls == 2][:, 2])) if (cls == 2).any() else float(np.percentile(pts[:, 2], 2))
    bld = pts[cls == 6]
    seen, ij = building_mass(bld, x, y, ground)
    mass = bld[seen[ij[:, 0], ij[:, 1]]]
    # thin spires are often left unclassified (class 1): keep such points when they stand high above the same footprint
    oth = pts[(cls == 1) & (pts[:, 2] > ground + 20)]
    if len(oth):
        oj = np.floor((oth[:, :2] - [x - R, y - R]) / CELL).astype(int)
        ok = (oj >= 0).all(1) & (oj < seen.shape[0]).all(1)
        oth, oj = oth[ok], oj[ok]
        mass = np.vstack([mass, oth[seen[oj[:, 0], oj[:, 1]]]])
    if len(mass) < 2000:
        return None
    # thin: one point (the highest) per 0.6 m column cell, plus wall points per 0.6 m voxel
    key = np.floor(mass / VOX).astype(np.int64)
    _, idx = np.unique(key, axis=0, return_index=True)
    thin = mass[idx]
    cx, cy = thin[:, 0].mean(), thin[:, 1].mean()
    loc = thin - [cx, cy, ground]
    # main axis by PCA of the footprint, so the long side can be drawn as a profile
    u, s, vt = np.linalg.svd(loc[:, :2] - loc[:, :2].mean(0), full_matrices=False)
    axis = vt[0]; along = loc[:, :2] @ axis
    lo, hi = np.percentile(along, [0.2, 99.8])
    bins = np.clip(((along - lo) / 1.0).astype(int), 0, int(hi - lo))
    prof = np.zeros(int(hi - lo) + 1); np.maximum.at(prof, bins, loc[:, 2])
    across = loc[:, :2] @ np.array([-axis[1], axis[0]])
    out = ROOT / "site" / "public" / "lidar"; out.mkdir(parents=True, exist_ok=True)
    np.round(loc * 10).astype("<i2").tofile(out / f"{b['id']}.bin")
    years = sorted({str(v)[:4] for rec in recs for k, v in rec.items() if "date" in k.lower() and v})
    return {"points": int(len(loc)), "raw_points": int(len(mass)), "tiles": [rec["url_npl"].rsplit("/", 1)[-1] for rec in recs],
            "survey_years": years, "ground_m": round(ground, 1), "top_m": round(float(np.percentile(loc[:, 2], 99.98)), 1),
            "roof_p90_m": round(float(np.percentile(prof[prof > 3], 90)), 1) if (prof > 3).any() else None,
            "length_m": round(float(hi - lo), 1), "width_m": round(float(np.percentile(across, 99.5) - np.percentile(across, 0.5)), 1),
            "axis_deg": round(math.degrees(math.atan2(axis[0], axis[1])) % 180, 1), "profile": [round(float(v), 1) for v in prof]}


def main():
    B = {b["id"]: b for b in json.load(open(OUT / "buildings.json", encoding="utf-8"))["buildings"]}
    ids = sys.argv[1:] or sorted(p.stem for p in (OUT / "curated").glob("PA*.json"))
    path = OUT / "lidar.json"
    res = json.load(open(path, encoding="utf-8")) if path.exists() else {}
    for i in ids:
        if i not in B or B[i]["lat"] is None:
            print(i, "not in atlas"); continue
        try:
            r = process(B[i])
        except Exception as e:  # one bad tile must not stop the run
            print(i, B[i]["commune"], "failed:", repr(e)[:200], flush=True); continue
        if r:
            res[i] = r; print(i, B[i]["commune"], r["points"], "pts, top", r["top_m"], "m, length", r["length_m"], "m", flush=True)
        else:
            res[i] = {"missing": True}; print(i, B[i]["commune"], "no LiDAR tile published or too few points", flush=True)
        json.dump(res, open(path, "w", encoding="utf-8"), separators=(",", ":"))
        time.sleep(40)


if __name__ == "__main__":
    main()
