// RightHook console on Astro. Server-first per the frontend contract: the page
// is rendered to HTML at build time (Astro's server pass), interactivity lives
// in isolated client islands. True runtime SSR would require a Node adapter —
// a second server process inside the single Cloud Run container, which BUILD.md
// §5 bans ("separate frontend deployment"). Build-time server rendering keeps
// the single-service constraint and ships zero framework JS outside islands.
import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  // Served by the existing FastAPI static mount — no backend changes at all.
  base: "/static/next",
  outDir: "../app/static/next",
  integrations: [react()],
  vite: { plugins: [tailwindcss()] },
});
