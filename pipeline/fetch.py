"""Download raw sources into the raw folder.

    python pipeline/fetch.py            # fetch whatever is missing
    python pipeline/fetch.py --refresh  # re-download everything

POP exports (Mérimée, Palissy, Mémoire) come from the Ministry of Culture's public bucket.
Wikidata: one SPARQL query per property, about one a minute (the endpoint's limit).
"""
import json, sys, time, urllib.parse
from common import RAW, POP_BUCKET, POP_FILES, http

SPARQL = "https://query.wikidata.org/sparql"
Q = {  # one simple query per property, over every item that carries a Mérimée id (P380)
    "ids": "SELECT ?item ?pa WHERE { ?item wdt:P380 ?pa }",
    "style": "SELECT ?item ?v WHERE { ?item wdt:P380 [] ; wdt:P149 ?v }",
    "gothic_styles": 'SELECT ?item ?v WHERE { ?item wdt:P279* wd:Q176483 ; rdfs:label ?v FILTER(LANG(?v)="en") }',
    "label_en": 'SELECT ?item ?v WHERE { ?item wdt:P380 [] ; rdfs:label ?v FILTER(LANG(?v)="en") }',
    "commons": "SELECT ?item ?v WHERE { ?item wdt:P380 [] ; wdt:P373 ?v }",
    "image": "SELECT ?item ?v WHERE { ?item wdt:P380 [] ; wdt:P18 ?v }",
    "enwiki": "SELECT ?item ?v WHERE { ?item wdt:P380 [] . ?v schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> }",
    "frwiki": "SELECT ?item ?v WHERE { ?item wdt:P380 [] . ?v schema:about ?item ; schema:isPartOf <https://fr.wikipedia.org/> }",
    "inception": "SELECT ?item ?v ?prec WHERE { ?item wdt:P380 [] ; p:P571/psv:P571 [ wikibase:timeValue ?v ; wikibase:timePrecision ?prec ] }",
}


def main():
    refresh = "--refresh" in sys.argv
    RAW.mkdir(parents=True, exist_ok=True)
    for local, remote in POP_FILES.items():
        if refresh or not (RAW / local).exists():
            print("POP", remote); http(POP_BUCKET + remote, RAW / local)
    for name, q in Q.items():
        dest = RAW / f"wd_{name}.json"
        if refresh or not dest.exists():
            print("Wikidata", name, flush=True)
            http(SPARQL + "?" + urllib.parse.urlencode({"query": q}), dest, accept="application/sparql-results+json")
            n = len(json.load(open(dest, encoding="utf-8"))["results"]["bindings"])
            print(f"  {n} rows", flush=True); time.sleep(65)  # WDQS allows about one query a minute
    json.dump({"fetched": time.strftime("%Y-%m-%d")}, open(RAW / "fetched.json", "w"))


if __name__ == "__main__":
    main()
