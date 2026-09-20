# Arvelos — Personalized Astrology & Numerology Report Engine

A one-time-payment web app: the visitor enters their birth details, pays once,
and receives an individually-calculated astrology + numerology PDF by download
and email. No subscription.

> **Stack note (important):** "astro" here means *astrology*, not the Astro.js
> framework. This is a **Python (FastAPI) backend + a static HTML/CSS/JS
> frontend** — there is **no Node build**, so there is intentionally **no
> `package.json`, `astro.config.mjs`, `src/`, or `dist/`.** The frontend is
> plain, pre-built HTML served directly (no compile step). The whole website
> runs from a **single container**.

## What "web" and "mobile" mean here
The frontend (`frontend/index.html`) is a **responsive website** — it already
works in mobile browsers (phones/tablets) and desktop. There is no separate
native iOS/Android app; "mobile" = the same site on a phone. If you ever want a
true native app, that would wrap this same API and is a separate project.

## Project layout
```
Dockerfile          ← root-context build, used by render.yaml / railway.json only
render.yaml         ← one-click deploy on Render.com
railway.json        ← one-click deploy on Railway
Procfile            ← generic PaaS start command
requirements.txt    ← Python deps (root copy for host auto-detection)
runtime.txt         ← pins Python 3.12
app.json            ← Heroku deploy-button manifest
Aptfile             ← system libs (for non-Docker buildpack hosts)
.dockerignore       ← keeps the root-context build fast (see astro-engine/.dockerignore too)

backend/            FastAPI app + engine
  app.py            API + serves the static frontend when ARVELOS_FRONTEND set
  chart_engine.py   Swiss Ephemeris: Western + Vedic charts, dashas, transits
  numerology.py     Chaldean numerology, Lo Shu, Kua, personal months
  report_generator.py  assembles the PDF (WeasyPrint)
  content_*.py      the interpretive writing
  chart_graphics.py chart wheels + Lo Shu SVGs
  orders.py         order lifecycle + the `customers` table
  delivery.py       email delivery (Resend HTTP API, legacy SMTP fallback, outbox in dev)
  geo.py            offline IP -> country lookup, for the phone country-code default only
  gdpr_tools.py      export/delete/optout CLI — request+approve, never automatic (see below)
  payment/          Stripe adapter (USD only) + mock fallback
  requirements.txt
frontend/           landing, quiz, checkout, delivery, terms, privacy, cities.json
pdf_templates/      report.html + cover_emblem.png
assets/             cover artwork source
deploy/             the ACTUAL production path — Dokploy + Traefik + Docker
                    Compose on the Hostinger VPS. deploy/Dockerfile (not the
                    root one), docker-compose.yml + .override.yml (Traefik
                    router labels), .env.example (real secrets go in a
                    gitignored deploy/.env, never committed)
samples/            example generated PDFs (Western / Vedic / Mixed)
```

## Run locally
```bash
cd backend
pip install -r requirements.txt
ARVELOS_FRONTEND=$(pwd)/../frontend uvicorn app:app --reload --port 8000
# open http://localhost:8000
```

## Deploy — pick one

**A. Your VPS via Dokploy + Docker Compose (what's actually running in
production today, on Hostinger)**
```bash
ssh <vps> && cd /path/to/repo
git pull
cd astro-engine/deploy
docker compose up -d --build      # rebuild + recreate whenever backend/frontend code changed
                                   # (env-only changes, e.g. a new API key in .env, just need `up -d`)
```
Real secrets (Stripe/Resend keys) go in `deploy/.env` — copy
`deploy/.env.example`, fill it in on the server, never commit it.
`docker-compose.override.yml` carries the Traefik router labels (TLS via
Let's Encrypt, canonical-domain redirect); Traefik itself runs as its own
Dokploy-managed container, not something this repo starts.

**B. Render.com (one-click, untested against the current codebase for a while)**
Push this repo to GitHub → Render → New + → **Blueprint** → select the repo →
Apply. `render.yaml` provisions the web service + a 1 GB disk for the database.
Then point your domain at the Render URL (CNAME) in your DNS.

**C. Railway / Fly.io (same caveat as B)**
Connect the repo; both auto-detect the root `Dockerfile` (`railway.json` sets
the start command). Add a persistent volume mounted at `/data`.

## Environment variables
| Var | Default | Purpose |
|-----|---------|---------|
| `PAYMENT_PROVIDER` | – | set to `mock` to force dummy payments regardless of the keys below (e.g. staging) |
| `STRIPE_API_KEY` / `STRIPE_WEBHOOK_SECRET` | – | live gateway (USD only — see below); unset = mock |
| `BASE_URL` | `https://astro.arvelos.cloud` | used in emails, gateway redirects, CORS |
| `ARVELOS_ALLOWED_ORIGINS` | – | comma-separated CORS origins; falls back to `BASE_URL` |
| `ARVELOS_FRONTEND` | – | path to `frontend/`; set to serve the site from the app |
| `ARVELOS_DB` | `../data/arvelos.db` | SQLite path (use `/data/...` on hosts) |
| `ARVELOS_DATA_DIR` | `../data` | base dir for the DB, generated reports, and the dev-mode email outbox — set to a persistent volume on hosts |
| `RESEND_API_KEY` / `RESEND_FROM` | – | email delivery (report link, and later opt-in emails) via Resend's HTTP API — the chosen provider. Needs the `RESEND_FROM` domain verified in the Resend dashboard first, or sending to real customers fails. Unset = write to outbox |
| `SMTP_HOST/PORT/USER/PASS/FROM` | – | legacy plain-SMTP path, only used if `RESEND_API_KEY` is unset |

The site sells in USD only, via Stripe — there is no currency selection,
client-side or server-side (see `backend/payment/GATEWAYS.md` for why:
a prior INR/Razorpay path with regional pricing let anyone check out at
the discounted price regardless of location, so it was removed rather
than hidden). Falls back to the built-in mock adapter (dummy payment,
real report) when `STRIPE_API_KEY` is absent — so the site works
end-to-end with zero payment config, and Stripe activates the moment
the key is added.

Go-live checklist and the marketing/ads plan are in `DEPLOY_STEPS.md`,
`ARVELOS_HANDOFF.md`, and `marketing/CAMPAIGN.md`.

## Customer records & GDPR

Every order upserts a row in `customers` (deduped by lowercased email —
name, phone, order count, and the two separate opt-in flags/timestamps
for general updates and monthly Rashi/zodiac insights). It deliberately
excludes birth details, which stay in `orders` only. This is the table
to read from for anything community/outreach-related — never `orders`.

There's no admin UI or API for this yet — everything runs on the server
(same env as the container). `export` is read-only and immediate.
`delete`/`optout` are deliberately two-step: **nothing destructive ever
happens automatically** — logging a request never touches data, only an
explicit `approve` does, and every request plus its outcome stays in
`gdpr_requests` forever as the audit trail, independent of whether the
underlying customer/order data still exists.

```bash
python -m gdpr_tools export person@example.com        # full JSON of everything tied to that email

python -m gdpr_tools request delete person@example.com [note...]
python -m gdpr_tools request optout person@example.com marketing|zodiac|all [note...]
python -m gdpr_tools list [pending|approved|rejected|all]   # default: pending
python -m gdpr_tools approve <request_id> [approved_by]     # only this executes anything
python -m gdpr_tools reject <request_id> [reason...]
```

See the docstring in `backend/gdpr_tools.py` for exactly what each does.
