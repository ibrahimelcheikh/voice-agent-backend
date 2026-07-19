# AtlasPrimeX — Marketing Website

Static marketing site (Phase 1). Plain HTML/CSS/JS — no build step, no framework.
It is completely independent of the voice-agent backend and deploys as its own
Railway service.

## Files

| File | Purpose |
|---|---|
| `index.html` | The page markup (extracted from the design file, unchanged visually) |
| `styles.css` | All styles (extracted from the design's inline `<style>`) |
| `main.js` | All behavior — 3D phone tilt, conversation loop, counters, FAQ accordion, marquee (extracted from the design's inline `<script>`) |
| `assets/logo-mark.png` | Real AtlasPrimeX logo mark — used in the nav & footer where the design had the placeholder "A" |
| `assets/logo.png` | Full AtlasPrimeX horizontal lockup (kept for future use) |
| `assets/favicon-*.png`, `favicon.ico`, `favicon.png` | Favicons generated from the logo |
| `Caddyfile` | Static server config (gzip, cache headers, security headers) |
| `Dockerfile` | Builds a tiny Caddy image that serves this folder |
| `railway.json` | Tells Railway to build with the Dockerfile |

The only changes from the original design file are structural, not visual:
inline CSS/JS were moved into `styles.css` / `main.js`, the placeholder text
"A" logo mark was replaced with the real logo image (same 34×34 footprint), and
favicon + meta-description tags were added. Nothing else was touched.

## Run locally

Any static server works — no dependencies:

```bash
cd website
python3 -m http.server 8080
# open http://localhost:8080
```

Or exactly as Railway will run it (requires Docker):

```bash
cd website
docker build -t atlasprimex-web .
docker run --rm -e PORT=8080 -p 8080:8080 atlasprimex-web
# open http://localhost:8080
```

## Deploy on Railway

This is a **new, separate service** — it does not touch the existing
voice-agent backend service.

### Option A — Railway dashboard (recommended)

1. Open your project on [railway.app](https://railway.app) → **New** → **GitHub Repo**
   → pick this repo (`ibrahimelcheikh/voice-agent-backend`).
2. In the new service: **Settings → Source → Root Directory** = `website`.
   (This is what makes Railway build *this* folder and ignore the backend.)
3. Railway auto-detects `railway.json` → builds the `Dockerfile` (Caddy). No env
   vars are required; Railway provides `$PORT` automatically.
4. **Settings → Networking → Generate Domain** to get a public URL
   (e.g. `atlasprimex-web.up.railway.app`). Add your custom domain
   (`atlasprimex.ai`) here later.
5. Deploy. Every push to the branch redeploys automatically.

### Option B — Railway CLI

```bash
npm i -g @railway/railway   # if not installed
railway login
railway link                # select your existing project
# create a service whose root is the website/ folder:
cd website
railway up                  # builds the Dockerfile in this folder
railway domain              # generate a public URL
```

> If `railway up` picks up the repo root instead of `website/`, set the
> service's **Root Directory** to `website` in the dashboard (Option A, step 2),
> then redeploy.

### Notes

- **Fonts:** Sora / Inter / Noto Sans Arabic load from Google Fonts (same as the
  design). No self-hosting needed; the page degrades gracefully to system fonts.
- **"Book a demo" links** currently point to `mailto:hello@atlasprimex.ai`. In
  **Phase 4** these will be wired to a `POST /api/v1/leads` endpoint on the
  backend.
- The backend service is unaffected — this folder ships on its own.
