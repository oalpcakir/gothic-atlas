# Gothic Atlas

An open, non-commercial atlas of Gothic architecture, starting with France. It compiles public heritage
registers into one linked dataset and publishes it as a static site at `gothic.onuralp.co`.

## Layout

| Path | What it is |
|---|---|
| `pipeline/` | Python scripts (standard library only) that fetch and compile the data |
| `data/buildings.json` | The compiled dataset, read by the site build |
| `site/` | Astro static site: atlas map, one page per building, data download |
| `legacy/` | The first prototype (single page with a building game), kept for the game's return |

## Rebuild the data

Raw files are about 1.8 GB and live outside the repo, in `%LOCALAPPDATA%/gothic-atlas/raw`
(override with the `GOTHIC_RAW` environment variable).

```
python pipeline/fetch.py        # POP exports + Wikidata (one query a minute)
python pipeline/build.py        # select, parse, link -> data/ and site/public/data/
python pipeline/commons.py      # lead-image credits from Wikimedia Commons (cached)
python pipeline/build.py        # again, to merge the image credits
```

Use `python pipeline/fetch.py --refresh` to re-download everything. Refreshes are run by hand.

## Build the site

```
cd site
npm install
npm run build      # writes site/dist
npm run dev        # local preview
```

## Sources and licences

- Mérimée and Palissy, Ministère de la Culture: Licence Ouverte 2.0
- Mémoire (metadata only), Médiathèque du patrimoine et de la photographie: ODbL
- Wikidata: CC0. Wikimedia Commons images: licence shown beside each image
- Boundaries: IGN ADMIN EXPRESS COG CARTO PE (Licence Ouverte 2.0), via `pipeline/boundaries.py`

The code is released under the MIT licence (see `LICENSE`). The compiled dataset (`data/`, `site/public/data/`) is released under the [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/), and the text written for the site under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
