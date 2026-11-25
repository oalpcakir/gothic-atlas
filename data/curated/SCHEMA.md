# Curated cathedral dossier: one JSON file per building, named `<Mérimée id>.json`

Every figure carries its own source. Facts only: never copy sentences from a source; write summaries in your own words.

```json
{
  "id": "PA00116046",
  "name_en": "Amiens Cathedral",
  "summary": "Two or three plain sentences in English on what makes the building matter. Own words.",
  "dimensions": {
    "vault_height_m":   {"value": 42.3, "source": "https://…", "note": "nave vault, interior", "alt": [{"value": 43, "source": "https://…"}]},
    "length_interior_m": {"value": 133.5, "source": "https://…"},
    "length_exterior_m": {"value": 145, "source": "https://…"},
    "nave_width_m":      {"value": 14.6, "source": "https://…", "note": "central vessel, between pier axes"},
    "tallest_point_m":   {"value": 112.7, "source": "https://…", "note": "flèche"},
    "towers_m":          {"value": 68.2, "source": "https://…", "note": "north tower"},
    "area_m2":           {"value": 7700, "source": "https://…", "note": "interior floor area"}
  },
  "phases": [
    {"from": 1220, "to": 1236, "part": "nave", "what": "Nave and west front built first, under Robert de Luzarches", "source": "https://…", "certainty": "documented|approximate|debated"}
  ],
  "events": [
    {"year": 1258, "type": "fire|collapse|war|revolution|restoration|lightning|other", "what": "One sentence.", "source": "https://…"}
  ],
  "masters": [{"name": "Robert de Luzarches", "active": "1220–c.1228", "source": "https://…"}],
  "sources": [{"title": "Title of page or book", "url": "https://…"}]
}
```

Rules
- Leave a field out when no source gives it. Do not estimate.
- When two sources disagree, keep the better-supported value in `value` and list the other under `alt`.
- `part` is one of: crypt, choir, ambulatory, transept, nave, west front, towers, spire, chapels, cloister, whole.
- Phases cover the medieval works from the start of the Gothic building to its completion or abandonment (include later completions such as 19th-century spires as phases too).
- Events cover damage and repair from the Middle Ages to today.
