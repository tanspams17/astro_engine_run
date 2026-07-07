# Arvelos — Project Handoff (paste this into a new chat to continue)

**Product:** Arvelos — one-time-payment personalized astrology + numerology PDF
report engine. No subscription. Domain: **arvelos.cloud** (registered on
Hostinger, DNS not yet pointed). Owner: Raj.

**How to resume:** Start a new chat, attach this file, and say *"Continue the
Arvelos build from this handoff — finish the VPS test deploy."* All source
lives in the outputs folder under `astro-engine/` (see file map below).

---

## 1. Current status — where we are RIGHT NOW

The whole product is BUILT and tested locally. We are mid-way through a
**live test deployment** to Raj's VPS (native Python, no Docker, on port
8801, mock-payment mode) so Raj can proofread the funnel + a real PDF.

**Deployment progress:** transferring the app tarball to the VPS in 4
base64 chunks via the Deploy API. **Chunk 1 of 4 sent** (`/home/deploy/app.b64`
had 30001 bytes). Chunks 2–4 (`/tmp/L_ab`, `L_ac`, `L_ad` in the sandbox —
these are gone on resume, so REBUILD the bundle fresh, see §5). After all
chunks: `base64 -d app.b64 > app.tgz`, verify sha256
`8e1fde0b29fa8119654989ae8d4d84465ab6fb4f267ec4b3e71102e6a030508b`, extract,
build venv, generate emblem + cities.json on the box, launch uvicorn.

> Simpler on resume: don't chunk. Rebuild the lean bundle and transfer it
> in fewer, cleaner steps, OR (better) have the VPS `git`/`curl` it if we
> put it somewhere reachable. The chunk method works but is token-heavy.

---

## 2. VPS ACCESS — the key unlock (via vps-deploy skill + Claude-in-Chrome)

Raj's VPS runs a persistent **Deploy API**. Claude reaches it from any chat
using the Claude-in-Chrome MCP (the sandbox itself has NO network).

| Field | Value |
|---|---|
| VPS IP | 187.124.117.22 |
| Ping | http://187.124.117.22:7071/ping → `{"ok":true}` |
| Run endpoint | http://187.124.117.22:7071/run (POST JSON) |
| Deploy token | `4c1898867fe907ecd387d6b89724bd0997f04089d7757f6806c595b8ec8f0613` |
| Runs as | user `deploy` (uid 1001), cwd /home/deploy |
| Timeout | 120 s per command |

**How to call it:** load Chrome tools, navigate a tab to
`http://187.124.117.22:7071/ping` (HTTP base avoids mixed-content block),
then `javascript_tool`:
```js
(async () => {
  const res = await fetch('http://187.124.117.22:7071/run', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ token:'4c18...0613', cmd:'<shell>', cwd:'/home/deploy' })
  });
  return await res.json();   // {stdout, stderr, error, exitCode}
})();
```

**VPS environment (probed):** Ubuntu 24.04 · Docker 29.5 + Compose v5 (but
docker needs sudo) · Nginx 1.24 running on :80 (job-applications app) ·
Python 3.12 + venv · **WeasyPrint system libs present** (pango/cairo/gdk) ·
certbot NOT installed · **sudo requires a password (deploy user cannot sudo)**.

**Consequences:** For the test, run natively as `deploy` on a spare port
(8801). Full Docker+Nginx+TLS on the root domain later needs a
password-capable step from Raj (or root Deploy API access).

---

## 3. What's BUILT (all tested locally, green)

- **Chart engine** (`backend/chart_engine.py`) — Swiss Ephemeris: Western
  tropical/Placidus + Vedic sidereal/Lahiri, nakshatra, Vimshottari dasha,
  12-month Jupiter/Saturn transits + Sade Sati. Validated vs reference values.
- **Numerology** (`backend/numerology.py`) — Chaldean: Mulank, Bhagyank,
  name/soul/personality numbers, Kua, Lo Shu grid, personal months.
  Reproduces the reference "Pamit Raj Fortune Report" exactly (Mulank 7,
  Bhagyank 2, name 4, Kua 8, karmic 16).
- **Report generator + content** (`report_generator.py`, `content_library.py`,
  `content_vedic.py`, `content_numerology.py`) — warm/grounded tone, no
  health claims, no gemstone upsell. Mixed report ~30 pages.
- **Chart graphics** (`chart_graphics.py`) — Western wheel, North-Indian
  diamond kundali, Lo Shu grid, cover zodiac ring + emblem, all SVG/PIL.
- **Cover** — ornate purple/gold, zodiac ring, tagline "॥ Your Sky · Your
  Numbers · Your Year Ahead ॥", name plaque, TOC/index page. Current emblem =
  gold Sudarshan-chakra × solar-diadem (dense 16-spoke solid-fill), rendered
  to `pdf_templates/cover_emblem.png`. **PENDING:** Raj's own zodiac-wheel PNG
  to swap in — see §6.
- **Backend API** (`app.py`) — quiz w/ UTM capture, order lifecycle
  (pending→paid→delivered/failed/refunded), mock + Mollie adapters switched
  by `PAYMENT_PROVIDER` env, background PDF fulfilment, download links,
  optional static frontend serving via `ARVELOS_FRONTEND` env. Birth time
  OPTIONAL end-to-end (falls back to Moon-based kundali).
- **Payments** (`backend/payment/`) — `interface.py`, `mock_adapter.py`,
  `mollie_adapter.py` (hosted checkout + webhook, tested with faked API).
  Flip live with `PAYMENT_PROVIDER=mollie` + `MOLLIE_API_KEY`.
- **Frontend** (`frontend/`) — landing, multi-step quiz (7192-city
  autocomplete, live pricing, GDPR unticked opt-in, no-birth-time checkbox,
  gender for Kua), checkout (card fields for mock / redirect for Mollie),
  delivery page. `terms.html`, `privacy.html`.
- **Deploy scaffolding** (`deploy/`) — Dockerfile, docker-compose.yml,
  nginx.conf.template, one-command `deploy.sh`. Plus `arvelos_deploy.zip` +
  `DEPLOY_STEPS.md` in outputs root.
- **Marketing** (`marketing/`) — 3 finished 9:16 launch videos (ElevenLabs
  VO + rendered visuals), CAMPAIGN.md with UTM links, workflow_diagram.png.

## Pricing decided
Western $19 / Vedic $19 / Mixed $29 (₹999/₹999/₹1,499). Launch low, raise
after reviews. Target: diaspora women 25–40 (US/UK/CA), then US/UK wellness,
then India domestic. Lead with Mixed at $29.

---

## 4. File map (under outputs/astro-engine/)
```
backend/  chart_engine.py numerology.py report_generator.py
          content_library.py content_vedic.py content_numerology.py
          chart_graphics.py app.py orders.py delivery.py
          gen_emblems_v2.py gen_chakra_v2.py   (emblem generators)
          payment/ interface.py mock_adapter.py mollie_adapter.py
          requirements.txt
pdf_templates/  report.html  cover_emblem.png
frontend/  index.html terms.html privacy.html cities.json
deploy/  Dockerfile docker-compose.yml nginx.conf.template deploy.sh
marketing/  videos/*.mp4 CAMPAIGN.md workflow_diagram.png design_philosophy.md
```

---

## 5. NEXT ACTIONS (in order)

1. **Finish the test deploy** (native, port 8801). Rebuild lean bundle:
   ```bash
   cd outputs/astro-engine
   rsync -a --exclude __pycache__ --exclude data --exclude 'backend/gen_cover_options.py' \
     --exclude 'backend/gen_emblem_options.py' --exclude 'backend/gen_emblem_chakra.py' \
     backend pdf_templates frontend /tmp/ship2/
   rm -f /tmp/ship2/pdf_templates/cover_emblem.png /tmp/ship2/frontend/cities.json
   tar czf app.tgz -C /tmp/ship2 .        # ~68 KB; keep gen_emblems_v2.py + gen_chakra_v2.py
   ```
   Transfer to VPS (chunk base64 through Deploy API, ≤30 KB/chunk), then on VPS:
   ```bash
   cd /home/deploy && base64 -d app.b64 > app.tgz && mkdir -p arvelos && tar xzf app.tgz -C arvelos
   cd arvelos/backend && python3 -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt geonamescache numpy pillow
   # regenerate cover emblem + cities.json ON the box:
   python3 -c "from gen_chakra_v2 import chakra_solid; from gen_emblems_v2 import S; from PIL import Image; chakra_solid().resize((S,S),Image.LANCZOS).save('../pdf_templates/cover_emblem.png')"
   python3 - <<'PY'  # cities.json via geonamescache (script in original session, pop>=80k)
   PY
   ARVELOS_DB=/home/deploy/arvelos/data/arvelos.db \
   ARVELOS_FRONTEND=/home/deploy/arvelos/frontend \
   nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 8801 >/home/deploy/arvelos.log 2>&1 &
   ```
   Smoke test: `curl -s http://127.0.0.1:8801/api/health`. Give Raj the link
   **http://187.124.117.22:8801/** to proofread (mock pay: any card works,
   card ending in 0 = simulated decline).
2. **Raj proofreads** the funnel + a generated PDF on that link.
3. **Swap Raj's cover PNG** once it lands as a real file attachment (§6).
4. **DNS**: point arvelos.cloud A-record → 187.124.117.22 in Hostinger hPanel.
5. **Production**: Docker+Nginx+TLS on root domain (needs sudo-capable step).
6. **Mollie**: Raj signs up + KYB (get astrology approved in writing), then
   flip `PAYMENT_PROVIDER=mollie` + key (1-line).
7. **SMTP**: pick Postmark/Brevo, set SMTP_* env. Until then download links work.
8. **Instagram**: create account, post the 3 Reels (steps in CAMPAIGN.md).

---

## 6. Cover emblem — FINALIZED ✓
Raj's uploaded artwork (`Cover_sudarshan.png` — gold zodiac wheel + moon +
sun on a navy starfield) is now the official cover. Source kept at
`astro-engine/assets/cover_artwork_source.png`; the feathered version used by
the template is `astro-engine/pdf_templates/cover_emblem.png` (edges vignetted
so the rectangle melts in). The cover background gradient was recolored to
navy (#241a5e→#1a1150→#130a40) to match the artwork = one seamless field.
The deploy zip now bundles the real emblem (~5 MB), so NO need to regenerate
it on the VPS. The old chakra generators (gen_emblems_v2.py, gen_chakra_v2.py)
remain in the repo but are unused. **Engine is final as of this version.**

---

## 7. Guardrails to remember
- Never enter payment credentials / API keys into forms on Raj's behalf.
- Confirm before any irreversible/side-effectful action.
- Deploy API commands are fine (Raj's own infra), but treat destructive ones
  (rm -rf outside /home/deploy/arvelos, touching the job-applications app on
  :80, docker on shared host) with care — port 80 is the OTHER project.
