# AtlasPrimeX — Product Demo Video

`AtlasPrimeX-Demo.mp4` — 1920×1080, 30 fps, h264/yuv420p, **~115.6 s, ~11 MB**.
Fully scripted with Playwright (Chromium `recordVideo`) + ffmpeg — no manual screen capture.

## Scenes (each recorded as its own clip, then crossfaded)

1. **Intro** (`scenes/intro.html`) — logo + tagline + animated orbs (6 s)
2. **Website tour** — serves `../website/` and smooth-scrolls every section (36 s)
3. **Merchant dashboard** — mounts `02-merchant-dashboard.jsx` in `dash-shell/` (Vite+React) and walks Overview → Conversations → Services detail → Reports chart → Settings/Holidays → Arabic RTL, with a visible cursor (35 s)
4. **Live call** (`scenes/call.html`) — animated bilingual call story: dial → IVR → booking → reschedule → urgent escalation + auto-created ticket → end card (34.6 s)
5. **Outro** (`scenes/outro.html`) — logo + CTA + URLs (6 s)

## Rebuild

```bash
cd video
npm install                        # playwright-core
python3 -m http.server 8200 &       # serves video/ (scenes + assets)
(cd ../website && python3 -m http.server 8201 &)
(cd dash-shell && npm install && npm run build && cd dist && python3 -m http.server 8202 &)

node run-intro.js && node run-website.js && node run-dashboard.js && node run-call.js && node run-outro.js
# convert each clips-raw/*.webm -> clips/*.mp4, then xfade-concat into AtlasPrimeX-Demo.mp4
# (ffmpeg commands are in the build history / this repo's session)
```

- Fonts (Poppins, Noto Sans Arabic) are self-hosted in `assets/fonts/` so scenes render offline.
- ffmpeg used: static 7.0.2 (via `pip install imageio-ffmpeg`).
- `node_modules/`, `dist/`, `clips/`, `clips-raw/`, `*.webm` are gitignored.

## Optional narration
An Azure TTS English voiceover can be muxed under the video on request (one line per scene).
