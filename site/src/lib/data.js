// Loads the compiled dataset once per build and exposes helpers shared by all pages.
import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd(); // the site/ folder
let cache;
export function load() {
  if (!cache) {
    const raw = JSON.parse(fs.readFileSync(path.join(ROOT, "..", "data", "buildings.json"), "utf8"));
    cache = { meta: raw.meta, buildings: raw.buildings, byId: new Map(raw.buildings.map((b) => [b.id, b])) };
  }
  return cache;
}

export const href = (b) => `/buildings/${(b.id ?? b).toLowerCase()}/`;
export const fmt = (n) => (n ?? 0).toLocaleString("en-GB");
export const place = (b) => `${b.commune}, ${b.dept_name}`;

// One hue per century of the first Gothic-era campaign, taken from stained glass: cobalt, violet, ruby, amber, green.
export const CENTURIES = [
  { c: 12, label: "12th c.", color: "var(--c12)" },
  { c: 13, label: "13th c.", color: "var(--c13)" },
  { c: 14, label: "14th c.", color: "var(--c14)" },
  { c: 15, label: "15th c.", color: "var(--c15)" },
  { c: 16, label: "16th c.", color: "var(--c16)" },
];
export const centuryOf = (year) => (year == null ? null : Math.min(16, Math.max(12, Math.floor((year - 1) / 100) + 1)));

// Plain equirectangular projection scaled at 46.5 N; mainland France and Corsica fit a 420 x 400 box.
const K = 600 / 15.6;
const COS = Math.cos((46.5 * Math.PI) / 180);
export const project = (lon, lat) => [+((lon + 5.4) * COS * K + 8).toFixed(1), +((51.3 - lat) * K + 8).toFixed(1)];
export const MAP_BOX = "0 0 420 400";
export const inFrance = (b) => b.lat != null && b.lat > 41 && b.lat < 51.5 && b.lon > -5.5 && b.lon < 10;

let outline;
export function francePath() {
  if (!outline) {
    const g = JSON.parse(fs.readFileSync(path.join(ROOT, "src", "data", "france-outline.json"), "utf8")).geometry;
    outline = g.coordinates
      .filter((poly) => poly[0].length >= 12)
      .map((poly) => {
        let last = null;
        const pts = [];
        for (const [lon, lat] of poly[0]) {
          const p = project(lon, lat);
          if (last && Math.abs(p[0] - last[0]) + Math.abs(p[1] - last[1]) < 1.2) continue;
          pts.push(p.join(","));
          last = p;
        }
        return "M" + pts.join("L") + "Z";
      })
      .join("");
  }
  return outline;
}

export const SOURCES = {
  M: { name: "Mérimée", long: "Base Mérimée, Ministère de la Culture (Licence Ouverte 2.0)" },
  W: { name: "Wikidata", long: "Wikidata (CC0)" },
  P: { name: "Palissy", long: "Base Palissy, Ministère de la Culture (Licence Ouverte 2.0)" },
  Ph: { name: "Mémoire", long: "Base Mémoire, Médiathèque du patrimoine et de la photographie (metadata under ODbL)" },
  A: { name: "Atlas", long: "Computed by Gothic Atlas from the sources above" },
};

export const TYPE_PLURAL = {
  cathedral: "cathedrals", church: "churches", chapel: "chapels", abbey: "abbeys", "abbey church": "abbey churches",
  priory: "priories", convent: "convents", "collegiate church": "collegiate churches", basilica: "basilicas",
  commandery: "commanderies", charterhouse: "charterhouses", monastery: "monasteries", cloister: "cloisters", oratory: "oratories",
};
