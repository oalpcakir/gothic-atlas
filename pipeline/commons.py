"""Fetch author, licence and thumbnail for each building's lead image on Wikimedia Commons.

    python pipeline/commons.py

Reads data/buildings.json (run build.py first), writes cache/commons.json, then re-run build.py.
Polite by design: 50 titles per request, one request every 3 s, a minute's pause when Commons says 429, results cached between runs.
"""
import html, json, re, time, urllib.parse
from common import CACHE, OUT, http

API = "https://commons.wikimedia.org/w/api.php"
WIDTH = 960  # one of the standard thumbnail widths Commons accepts


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()[:120]


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "commons.json"
    cache = json.load(open(path, encoding="utf-8")) if path.exists() else {}
    files = sorted({urllib.parse.unquote(b["image_file"]) for b in json.load(open(OUT / "buildings.json", encoding="utf-8"))["buildings"] if b.get("image_file")})
    raw = {urllib.parse.unquote(k): k for k in {b["image_file"] for b in json.load(open(OUT / "buildings.json", encoding="utf-8"))["buildings"] if b.get("image_file")}}
    todo = [f for f in files if raw[f] not in cache]
    print(len(files), "images,", len(todo), "to fetch", flush=True)
    for i in range(0, len(todo), 50):
        batch = todo[i:i + 50]
        q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|size|extmetadata",
                                    "iiurlwidth": WIDTH, "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl", "titles": "|".join("File:" + f for f in batch)})
        data = json.loads(http(API + "?" + q, tries=30, wait=60))
        norm = {n["to"]: n["from"] for n in data["query"].get("normalized", [])}
        for p in data["query"]["pages"].values():
            title = norm.get(p["title"], p["title"])[5:]
            key = raw.get(title) or raw.get(title.replace("_", " "))
            if not key:
                continue
            ii = (p.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata", {})
            cache[key] = {"thumb": ii.get("thumburl"), "w": ii.get("thumbwidth"), "h": ii.get("thumbheight"), "page": ii.get("descriptionurl"),
                          "artist": clean(meta.get("Artist", {}).get("value")), "licence": clean(meta.get("LicenseShortName", {}).get("value")),
                          "licence_url": meta.get("LicenseUrl", {}).get("value")} if ii.get("thumburl") else {}
        for f in batch:
            cache.setdefault(raw[f], {})
        json.dump(cache, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  {min(i + 50, len(todo))}/{len(todo)}", flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main()
