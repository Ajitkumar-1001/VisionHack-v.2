# Build-only image. There is no frontend RUNTIME container by design.
#
# PRD §19 mandates a single Cloud Run service and §30 explicitly bans a
# separate frontend deployment, so this stage compiles the Astro console and
# hands the static output to the FastAPI container, which serves it. A second
# long-running web server would be a second thing to deploy, a second origin to
# CORS, and a divergence between what runs locally and what runs in production.
#
# astro.config.mjs sets outDir "../app/static/next", i.e. OUTSIDE this build
# context. The compose service therefore bind-mounts the repo and writes the
# result back to the host, where the app Dockerfile's `COPY app/` picks it up.
FROM node:22-alpine

WORKDIR /build

# Lockfile first so a source edit doesn't reinstall the dependency tree.
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY . .

# Writes to /repo/app/static/next via the bind mount declared in compose.
CMD ["npm", "run", "build"]
