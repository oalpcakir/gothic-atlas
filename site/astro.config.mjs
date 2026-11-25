import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

export default defineConfig({
  site: "https://gothic.onuralp.co",
  trailingSlash: "always",
  build: { format: "directory", concurrency: 4 },
  devToolbar: { enabled: false },
  integrations: [sitemap({ filter: (page) => !page.includes("/404") })],
});
