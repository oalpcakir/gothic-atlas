// Helpers for the hand-compiled cathedral dossiers and the charts drawn from them.
import { load } from "./data.js";

export const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
export const curated = () => load().buildings.filter((b) => b.dossier);
export const shortName = (b) => (b.dossier.name_en || b.name).replace(/ Cathedral$/, "").replace(/^Basilica of /, "").replace(/^Notre-Dame de /, "");
export const host = (url) => { try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return "source"; } };
export const dim = (b, k) => b.dossier.dimensions?.[k]?.value ?? null;
// Start of the Gothic works: the first phase from 1130 on (earlier phases are Romanesque predecessors).
export const firstYear = (b) => (b.dossier.phases.find((p) => p.from >= 1130) ?? b.dossier.phases[0])?.from ?? null;
// Start of the main vessel: the first such phase on the choir, nave or whole building.
export const bodyYear = (b) => (b.dossier.phases.find((p) => p.from >= 1130 && ["choir", "nave", "whole", "ambulatory"].includes(p.part)) ?? {}).from ?? firstYear(b);

export const PARTS = {
  crypt: ["Crypt", "var(--ink-2)"], choir: ["Choir", "var(--c12)"], ambulatory: ["Ambulatory", "var(--c12)"],
  transept: ["Transept", "var(--c13)"], nave: ["Nave", "var(--c14)"], "west front": ["West front", "var(--c15)"],
  towers: ["Towers", "var(--c16)"], spire: ["Spire", "var(--c16)"], chapels: ["Chapels", "var(--undated)"],
  cloister: ["Cloister", "var(--undated)"], whole: ["Whole building", "var(--ink)"],
};
export const partColor = (p) => (PARTS[p] || PARTS.whole)[1];
export const LEGEND_PARTS = ["choir", "transept", "nave", "west front", "towers", "chapels", "whole"];

export const DIM_LABELS = [
  ["vault_height_m", "Vault height", "m"], ["length_interior_m", "Length, interior", "m"], ["length_exterior_m", "Length, exterior", "m"],
  ["nave_width_m", "Width of central vessel", "m"], ["tallest_point_m", "Tallest point", "m"], ["towers_m", "Towers", "m"], ["area_m2", "Floor area", "m²"],
];
export const num = (v) => (typeof v === "number" ? v.toLocaleString("en-GB", { maximumFractionDigits: 2 }) : String(v));

// Gantt of building phases for one or many buildings. rows: [{label, href, phases, events}]
export function gantt(rows, { x0 = 1130, x1 = 1560, width = 900, labelW = 150, rowH = 20 } = {}) {
  const W = width, R = 70, T = 22;
  const H = T + rows.length * rowH + 8;
  const X = (y) => labelW + ((Math.min(Math.max(y, x0), x1) - x0) / (x1 - x0)) * (W - labelW - R);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" style="min-width:${Math.min(W, 640)}px" role="img" aria-label="Building phases by year">`;
  for (let y = Math.ceil(x0 / 50) * 50; y <= x1; y += 50) {
    s += `<line x1="${X(y)}" x2="${X(y)}" y1="${T - 4}" y2="${H - 6}" stroke="var(--rule)" stroke-width="${y % 100 ? 0.5 : 1}"/>`;
    if (y % 100 === 0) s += `<text x="${X(y)}" y="12" text-anchor="middle">${y}</text>`;
  }
  rows.forEach((r, i) => {
    const y = T + i * rowH;
    if (r.label) s += r.href ? `<a href="${r.href}"><text x="${labelW - 8}" y="${y + 12}" text-anchor="end" style="fill:var(--accent);font-size:11px">${esc(r.label)}</text></a>`
      : `<text x="${labelW - 8}" y="${y + 12}" text-anchor="end" style="font-size:11px">${esc(r.label)}</text>`;
    const late = [];
    for (const p of r.phases) {
      if (p.from > x1) { late.push(p); continue; }
      const a = X(p.from), b = X(Math.max(p.to, p.from + 2));
      s += `<rect x="${a}" y="${y + 3}" width="${Math.max(2.5, b - a)}" height="${rowH - 8}" fill="${partColor(p.part)}" fill-opacity="${p.certainty === "documented" ? 0.95 : 0.6}"><title>${esc(`${p.from}–${p.to} ${p.part}: ${p.what}`)}</title></rect>`;
      if (p.to > x1) late.push(p);
    }
    if (late.length) s += `<text x="${W - R + 6}" y="${y + 12}">→ ${Math.max(...late.map((p) => p.to))}</text>`;
    for (const e of r.events || []) {
      if (e.year < x0 || e.year > x1 || !["fire", "collapse", "lightning", "war"].includes(e.type)) continue;
      const x = X(e.year);
      s += `<path d="M${x - 3.5},${y + 1}h7l-3.5,6z" fill="var(--ink)"><title>${esc(`${e.year} ${e.type}: ${e.what}`)}</title></path>`;
    }
  });
  return s + "</svg>";
}
