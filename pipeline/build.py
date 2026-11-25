"""Compile the Gothic Atlas dataset from the raw sources.

    python pipeline/build.py

Reads   raw/merimee.csv, raw/palissy.csv, raw/memoire.csv, raw/wd_*.json, cache/commons.json (optional)
Writes  data/buildings.json            full records, read by the site build
        site/public/data/atlas.json    compact table for the map and the index
        site/public/data/gothic-atlas-buildings.{csv,json}   the public download

Inclusion rule (also printed on the site's About page):
  a religious building protected as a Monument historique is included when
  - "era":       Mérimée dates one of its building campaigns between 1140 and 1600, or
  - "confirmed": Wikidata gives it a Gothic architectural style (P149).
A bare "12e siècle" does not count as Gothic-era: most 12th-century churches are Romanesque.
"""
import collections, csv, json, math, re, unicodedata, urllib.parse
from common import RAW, CACHE, OUT, ROOT, pop_rows, religious_type
from glossary import CRAFT, DENOMINATION, en, owners

ERA_START, ERA_END = 1140, 1600

ORD = {"1er": 1, "1ère": 1, "2e": 2, "3e": 3, "4e": 4}
ORD_EN = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}


def th(n):
    return f"{n}{'th' if 10 < n % 100 < 14 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def parse_campaign(term):
    """'1er quart 13e siècle' -> (1201, 1225, '1st quarter of the 13th century', 'quarter'). None if not a century term."""
    t = term.strip()
    m = re.fullmatch(r"limite (\d+)e siècle (\d+)e siècle", t)
    if m:
        c = int(m[1])
        return (c * 100 - 10, c * 100 + 10, f"turn of the {th(c)} and {th(c + 1)} centuries", "turn")
    m = re.fullmatch(r"(?:(1er|1ère|2e|3e|4e) (quart|moitié) |(milieu|début|fin) )?(\d+)e siècle", t)
    if not m:
        return None
    c = int(m[4]); base = (c - 1) * 100
    if m[2] == "quart":
        q = ORD[m[1]]
        return (base + (q - 1) * 25 + 1, base + q * 25, f"{ORD_EN[q]} quarter of the {th(c)} century", "quarter")
    if m[2] == "moitié":
        h = ORD[m[1]]
        return (base + (h - 1) * 50 + 1, base + h * 50, f"{ORD_EN[h]} half of the {th(c)} century", "half")
    if m[3] == "milieu":
        return (base + 41, base + 60, f"middle of the {th(c)} century", "mid")
    if m[3] == "début":
        return (base + 1, base + 25, f"early {th(c)} century", "quarter")
    if m[3] == "fin":
        return (base + 76, base + 100, f"late {th(c)} century", "quarter")
    return (base + 1, base + 100, f"{th(c)} century", "century")


def split(v):
    return [x.strip() for x in re.split(r"\s*;\s*", v or "") if x.strip()]


def slug_ascii(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def parse_protection(v):
    out = []
    for part in re.split(r"\s*[;.]\s+|;", v.replace("\xa0", " ")):
        m = re.match(r"\s*(\d{4})(?:/(\d{2})/(\d{2}))?\s*:\s*(.+?)\s*$", part)
        if not m:
            continue
        kind = m[4].lower()
        k = "delisted" if "déclass" in kind else "classified" if "class" in kind else "inscribed" if "inscri" in kind else kind
        date = m[1] + (f"-{m[2]}-{m[3]}" if m[2] and m[2] != "00" and m[3] != "00" else "")
        out.append({"date": date, "year": int(m[1]), "kind": k, "partial": "partiel" in kind})
    return sorted(out, key=lambda p: p["date"])


def wd(name):
    p = RAW / f"wd_{name}.json"
    rows = json.load(open(p, encoding="utf-8"))["results"]["bindings"]
    return [{k: v["value"] for k, v in r.items()} for r in rows]


def qid(uri):
    return uri.rsplit("/", 1)[1]


def load_wikidata():
    pa2q = {}
    for r in wd("ids"):
        pa2q.setdefault(r["pa"].strip(), qid(r["item"]))
    gothic = {qid(r["item"]): r["v"] for r in wd("gothic_styles")}
    styles = collections.defaultdict(list)
    for r in wd("style"):
        s = qid(r["v"])
        if s in gothic and gothic[s] not in styles[qid(r["item"])]:
            styles[qid(r["item"])].append(gothic[s])
    def one(name):
        d = {}
        for r in wd(name):
            d.setdefault(qid(r["item"]), r["v"])
        return d
    inc = {}
    for r in wd("inception"):
        m = re.match(r"\+?(\d{4})", r["v"])
        if m and int(r["prec"]) >= 7:
            q = qid(r["item"]); inc[q] = min(inc.get(q, 9999), int(m[1]))
    img = {q: urllib.parse.unquote(v.rsplit("/", 1)[-1]) for q, v in one("image").items()}
    return dict(pa2q=pa2q, styles=styles, label=one("label_en"), commons=one("commons"), image=img,
                enwiki=one("enwiki"), frwiki=one("frwiki"), inception=inc)


def load_merimee(W):
    out = {}
    for r in pop_rows("merimee.csv"):
        typ = religious_type(r)
        if not typ:
            continue
        ref = r["Reference"]
        camps = []
        for field, role in (("Siecle_de_la_campagne_principale_de_construction", "main"), ("Siecle_de_campagne_secondaire_de_construction", "secondary")):
            for term in split(r[field]):
                p = parse_campaign(term)
                if p:
                    camps.append({"from": p[0], "to": p[1], "label": p[2], "precision": p[3], "role": role, "fr": term})
                elif term == "Moyen Age":
                    camps.append({"from": None, "to": None, "label": "Middle Ages (undated)", "precision": "era", "role": role, "fr": term})
        camps.sort(key=lambda c: (c["from"] or 9999, c["to"] or 9999))
        gothic = [c for c in camps if c["from"] and c["from"] >= ERA_START and c["to"] <= ERA_END]
        q = W["pa2q"].get(ref)
        styles = W["styles"].get(q, []) if q else []
        if not gothic and not styles:
            continue
        lat = lon = None
        m = re.match(r"\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", r["coordonnees_au_format_WGS84"])
        if m:
            lat, lon = round(float(m[1]), 5), round(float(m[2]), 5)
        years = [int(y) for y in re.findall(r"\b(1[0-9]{3})\b", r["Datation_de_l_edifice"])]
        b = {
            "id": ref, "name": r["Titre_editorial_de_la_notice"].strip() or r["Denomination_de_l_edifice"],
            "type": typ, "denomination": split(r["Denomination_de_l_edifice"]),
            "denomination_en": [en(DENOMINATION, d) for d in split(r["Denomination_de_l_edifice"])],
            "commune": r["Commune_forme_editoriale"].strip() or r["Commune_forme_index"].strip(),
            "insee": r["COG_Insee_lors_de_la_protection"].strip(), "dept": r["Departement_format_numerique"].strip(),
            "dept_name": r["Departement_en_lettres"].strip(), "region": r["Region"].strip(),
            "address": r["Adresse_forme_editoriale"].strip(), "lat": lat, "lon": lon,
            "level": "confirmed" if styles else "era", "styles": styles,
            "campaigns": camps, "first": min((c["from"] for c in gothic), default=None),
            "first_label": min(gothic, key=lambda c: c["from"])["label"] if gothic else None,
            "dated_years": sorted(set(years)), "historique": r["Historique"].strip(),
            "description": r["Description_de_l_edifice"].strip(),
            "authors": split(r["Auteur_de_l_edifice"]),
            "protection": parse_protection(r["Date_et_typologie_de_la_protection"]),
            "protection_note": r["Precision_de_la_protection"].strip(),
            "world_heritage": "patrimoine mondial" in r["Typologie_de_la_zone_de_protection"],
            "ownership": r["Statut_juridique_de_l_edifice"].strip(),
            "ownership_en": owners(r["Statut_juridique_de_l_edifice"]),
            "decor": split(r["Technique_du_decor_porte_de_l_edifice"]),
            "merimee_updated": r["Date_de_la_derniere_mise_a_jour"],
            "inventaire": [x for x in split(r["Renvoi_vers_une_notice_de_la_base_Merimee_ou_Palissy"]) if x.startswith("IA")],
            "wikidata": q, "objects": None, "photos": None,
        }
        if q:
            b["name_en"], b["commons"], b["image_file"] = W["label"].get(q), W["commons"].get(q), W["image"].get(q)
            b["enwiki"], b["frwiki"], b["wd_inception"] = W["enwiki"].get(q), W["frwiki"].get(q), W["inception"].get(q)
        b["protected_since"] = b["protection"][0]["year"] if b["protection"] else None
        b["name"] = b["name"][:1].upper() + b["name"][1:]
        out[ref] = b
    return out


CENT = re.compile(r"(\d+)e siècle")


def add_palissy(B):
    agg = collections.defaultdict(lambda: {"count": 0, "glass": 0, "cats": collections.Counter(), "cent": collections.Counter(), "items": []})
    for r in pop_rows("palissy.csv"):
        refs = set(re.findall(r"PA\w{8}", r["Reference_a_une_notice_Merimee_MH"]))
        for pa in refs & B.keys():
            a = agg[pa]; a["count"] += 1
            den = r["Denomination"].lower()
            glass = "verrière" in den or "vitrail" in den
            a["glass"] += glass
            for c in split(r["Categorie_technique"])[:1]:
                a["cats"][c] += 1
            m = CENT.search(r["Siecle_de_creation"])
            c = int(m[1]) if m else None
            if c:
                a["cent"][c] += 1
            a["items"].append((c or 99, not glass, r["Reference"], (r["Titre_editorial"] or r["Denomination"]).strip()[:140], r["Format_abrege_du_siecle_de_creation"].strip()))
    for pa, a in agg.items():
        items = sorted(a["items"])[:10]
        cats = collections.Counter()
        for c, n in a["cats"].items():
            cats[en(CRAFT, c)] += n
        B[pa]["objects"] = {"count": a["count"], "stained_glass": a["glass"], "categories": cats.most_common(6),
                            "centuries": sorted(a["cent"].items()),
                            "sample": [{"id": i[2], "title": i[3], "century": i[4]} for i in items]}


def add_memoire(B):
    agg = collections.defaultdict(lambda: {"count": 0, "img": 0, "dec": collections.Counter(), "who": collections.Counter(), "draw": 0, "early": []})
    for r in pop_rows("memoire.csv"):
        refs = set(re.findall(r"PA\w{8}", r["References_Palissy_Merimee_lien_notice_en_cours"])) & B.keys()
        if not refs:
            continue
        m = re.search(r"\b(1[89]\d\d|20[0-2]\d)\b", r["Date_de_la_prise_de_vue"])
        y = int(m[1]) if m else None
        drawing = bool(r["Technique_du_releve"].strip() or r["Echelle_du_graphique"].strip() or r["Date_dessin"].strip())
        who = (r["Auteur_de_la_photographie"] or r["Photographe"]).split(";")[0].strip()
        for pa in refs:
            a = agg[pa]; a["count"] += 1; a["img"] += bool(r["Lien_vers_l_image"])
            a["draw"] += drawing
            if y:
                a["dec"][y // 10 * 10] += 1
                if r["Lien_vers_l_image"]:
                    a["early"].append((y, r["Reference_de_la_notice"], (r["Legende"] or r["Titre_courant"]).strip()[:140], who))
            if who:
                a["who"][who] += 1
    for pa, a in agg.items():
        early = sorted(a["early"])[:6]
        B[pa]["photos"] = {"count": a["count"], "with_image": a["img"], "drawings": a["draw"],
                           "decades": sorted(a["dec"].items()), "earliest": early[0][0] if early else None,
                           "photographers": a["who"].most_common(4),
                           "sample": [{"id": e[1], "year": e[0], "caption": e[2], "by": e[3]} for e in early]}


def add_neighbours(B, k=6):
    pts = [(b["lat"], b["lon"], b["id"]) for b in B.values() if b["lat"] is not None]
    grid = collections.defaultdict(list)
    for p in pts:
        grid[(int(p[0] * 4), int(p[1] * 4))].append(p)
    for lat, lon, i in pts:
        gx, gy = int(lat * 4), int(lon * 4)
        cand = [p for dx in (-1, 0, 1) for dy in (-1, 0, 1) for p in grid[(gx + dx, gy + dy)] if p[2] != i]
        cosl = math.cos(math.radians(lat))
        near = sorted(((math.hypot((p[0] - lat) * 111.2, (p[1] - lon) * 111.2 * cosl), p[2]) for p in cand))[:k]
        B[i]["nearby"] = [{"id": j, "km": round(d, 1)} for d, j in near]
    sd = (48.9354, 2.3599)  # Basilica of Saint-Denis, where the first Gothic choir was built
    for b in B.values():
        if b["lat"] is not None:
            b["km_saint_denis"] = round(math.hypot((b["lat"] - sd[0]) * 111.2, (b["lon"] - sd[1]) * 111.2 * math.cos(math.radians(sd[0]))))


def add_commons(B):
    p = CACHE / "commons.json"
    if not p.exists():
        return 0
    info = json.load(open(p, encoding="utf-8"))
    n = 0
    for b in B.values():
        i = info.get(b.get("image_file") or "")
        if i and i.get("thumb"):
            b["image"] = {**i, "thumb": i["thumb"].split("?")[0]}; n += 1
    return n


def add_curated(B):
    """Hand-compiled dossiers (data/curated/<id>.json) and LiDAR measurements (data/lidar.json)."""
    n = 0
    for f in sorted((OUT / "curated").glob("PA*.json")):
        d = json.load(open(f, encoding="utf-8"))
        b = B.get(f.stem)
        if not b:
            print("curated file without a building:", f.name); continue
        d["name_en"] = re.sub(r"\s*\(.*?\)", "", d.get("name_en") or "").strip() or b.get("name_en")
        d["phases"] = sorted((p for p in d.get("phases", []) if isinstance(p.get("from"), int)), key=lambda p: (p["from"], p.get("to") or p["from"]))
        for p in d["phases"]:
            p["to"] = p["to"] if isinstance(p.get("to"), int) else p["from"]
        d["events"] = sorted((e for e in d.get("events", []) if isinstance(e.get("year"), int)), key=lambda e: e["year"])
        b["dossier"] = d; n += 1
    lp = OUT / "lidar.json"
    if lp.exists():
        pub, held = ROOT / "site" / "public" / "lidar", RAW.parent / "lidar-held"
        for i, r in json.load(open(lp, encoding="utf-8")).items():
            if i in B and r.get("missing"):
                B[i]["lidar_missing"] = True
            if i not in B or r.get("missing"):
                continue
            # The automatic cut cannot always separate a cathedral from buildings that touch it (cloisters,
            # palaces, older churches). A cut is published only when its length is within 0.8-1.2 times the
            # longest published length in the dossier; otherwise it is held back for a manual footprint.
            dims = (B[i].get("dossier") or {}).get("dimensions", {})
            ref = [dims[k]["value"] for k in ("length_exterior_m", "length_interior_m") if isinstance(dims.get(k, {}).get("value"), (int, float))]
            ratio = r["length_m"] / max(ref) if ref else None
            if ratio and 0.8 <= ratio <= 1.2:
                B[i]["lidar"] = r
                if (held / f"{i}.bin").exists() and not (pub / f"{i}.bin").exists():
                    (held / f"{i}.bin").replace(pub / f"{i}.bin")
            else:
                B[i]["lidar_held"] = "no published length to check the cut against" if not ref else f"cut is {ratio:.1f} times the published length"
                if (pub / f"{i}.bin").exists():
                    held.mkdir(parents=True, exist_ok=True); (pub / f"{i}.bin").replace(held / f"{i}.bin")
    return n


def main():
    W = load_wikidata()
    B = load_merimee(W)
    print(f"{len(B)} buildings selected", collections.Counter(b["level"] for b in B.values()))
    add_palissy(B); print("palissy:", sum(1 for b in B.values() if b["objects"]), "buildings with objects")
    add_memoire(B); print("memoire:", sum(1 for b in B.values() if b["photos"]), "buildings with photo records")
    add_neighbours(B)
    print("commons images:", add_commons(B))
    print("curated dossiers:", add_curated(B), "| lidar:", sum(1 for b in B.values() if b.get("lidar")), "shown,", sum(1 for b in B.values() if b.get("lidar_held")), "held")
    rows = sorted(B.values(), key=lambda b: (b["first"] or 9999, b["id"]))
    meta = {"generated": json.load(open(RAW / "fetched.json"))["fetched"], "count": len(rows),
            "rule": {"era_start": ERA_START, "era_end": ERA_END}}
    OUT.mkdir(exist_ok=True)
    json.dump({"meta": meta, "buildings": rows}, open(OUT / "buildings.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    pub = ROOT / "site" / "public" / "data"
    pub.mkdir(parents=True, exist_ok=True)
    types = sorted({b["type"] for b in rows}); regions = sorted({b["region"] for b in rows})
    atlas = {"meta": meta, "types": types, "regions": regions,
             "cols": ["id", "name", "commune", "dept", "region", "type", "level", "first", "lat", "lon", "protected", "photos", "objects", "search"],
             "rows": [[b["id"], b["name"], b["commune"], b["dept"], regions.index(b["region"]), types.index(b["type"]),
                       1 if b["level"] == "confirmed" else 0, b["first"], b["lat"], b["lon"], b["protected_since"],
                       (b["photos"] or {}).get("with_image", 0), (b["objects"] or {}).get("count", 0),
                       slug_ascii(f'{b["name"]} {b["commune"]} {b.get("name_en") or ""}')] for b in rows]}
    json.dump(atlas, open(pub / "atlas.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    cols = ["id", "name", "name_en", "type", "commune", "insee", "dept", "dept_name", "region", "lat", "lon", "level", "styles",
            "first_gothic_campaign_from", "first_gothic_campaign", "campaigns", "protected_since", "protection", "world_heritage",
            "authors", "wikidata", "commons_category", "wikipedia_en", "wikipedia_fr", "photo_records", "earliest_photo", "protected_objects",
            "stained_glass_records", "km_from_saint_denis", "merimee_url"]
    def flat(b):
        return {"id": b["id"], "name": b["name"], "name_en": b.get("name_en"), "type": b["type"], "commune": b["commune"], "insee": b["insee"],
                "dept": b["dept"], "dept_name": b["dept_name"], "region": b["region"], "lat": b["lat"], "lon": b["lon"], "level": b["level"],
                "styles": "; ".join(b["styles"]), "first_gothic_campaign_from": b["first"], "first_gothic_campaign": b["first_label"],
                "campaigns": "; ".join(f'{c["fr"]} ({c["role"]})' for c in b["campaigns"]), "protected_since": b["protected_since"],
                "protection": "; ".join(f'{p["date"]} {p["kind"]}' for p in b["protection"]), "world_heritage": b["world_heritage"],
                "authors": "; ".join(b["authors"]), "wikidata": b["wikidata"], "commons_category": b.get("commons"),
                "wikipedia_en": b.get("enwiki"), "wikipedia_fr": b.get("frwiki"), "photo_records": (b["photos"] or {}).get("count", 0),
                "earliest_photo": (b["photos"] or {}).get("earliest"), "protected_objects": (b["objects"] or {}).get("count", 0),
                "stained_glass_records": (b["objects"] or {}).get("stained_glass", 0), "km_from_saint_denis": b.get("km_saint_denis"),
                "merimee_url": f'https://pop.culture.gouv.fr/notice/merimee/{b["id"]}'}
    with open(pub / "gothic-atlas-buildings.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, cols); w.writeheader(); w.writerows(flat(b) for b in rows)
    # Public JSON: same records without empty fields and without site-only helpers, to keep the file well under 25 MB.
    slim = [{k: v for k, v in b.items() if v not in (None, "", [], False) and k not in ("nearby", "image", "lidar", "lidar_held", "lidar_missing")} for b in rows]
    json.dump({"meta": meta, "licence": "ODbL 1.0", "buildings": slim}, open(pub / "gothic-atlas-buildings.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    for f in (OUT / "buildings.json", pub / "atlas.json", pub / "gothic-atlas-buildings.csv", pub / "gothic-atlas-buildings.json"):
        print(f"{f.relative_to(ROOT)}  {f.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
