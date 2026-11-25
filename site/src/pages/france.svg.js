// Shared outline of France, referenced with <use href="/france.svg#fr"> so pages do not each carry it.
import { francePath, MAP_BOX } from "../lib/data.js";

export function GET() {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${MAP_BOX}"><path id="fr" d="${francePath()}"/></svg>`;
  return new Response(svg, { headers: { "Content-Type": "image/svg+xml" } });
}
