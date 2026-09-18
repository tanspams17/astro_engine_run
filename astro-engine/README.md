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
Dockerfile          ← builds the whole app into one container (root level)
render.yaml         ← one-click deploy on Render.com
railway.json        ← one-click deploy on Railway
Procfile            ← generic PaaS start command
requirements.txt    ← Python deps (root copy for host auto-detection)
runtime.txt         ← pins Python 3.12
app.json            ← Heroku deploy-button manifest
Aptfile             ← system libs (for non-Docker buildpack hosts)

backend/            FastAPI app + engine
  app.py            API + serves the static frontend when ARVELOS_FRONTEND set
  chart_engine.py   Swiss Ephemeris: Western + Vedic charts, dashas, transits
  numerology.py     Chaldean numerology, Lo Shu, Kua, personal months
  report_generator.py  assembles the PDF (WeasyPrint)
  content_*.py      the interpretive writing
  chart_graphics.py chart wheels + Lo Shu SVGs
  orders.py delivery.py  order lifecycle + email
  payment/          gateway-agnostic adapter (mock + Mollie)
  requirements.txt
frontend/           landing, quiz, checkout, delivery, terms, privacy, cities.json
pdf_templates/      report.html + cover_emblem.png
assets/             cover artwork source
deploy/             VPS files (Docker Compose, Nginx vhost, deploy.sh)
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

**A. Render.com (easiest, free-ish tier)**
Push this repo to GitHub → Render → New + → **Blueprint** → select the repo →
Apply. `render.yaml` provisions the web service + a 1 GB disk for the database.
Then point `arvelos.cloud` at the Render URL (CNAME) in your DNS.

**B. Railway / Fly.io**
Connect the repo; both auto-detect the `Dockerfile` (`railway.json` sets the
start command). Add a persistent volume mounted at `/data`.

**C. Your Hostinger VPS (Docker)**
```bash
git clone <repo> arvelos && cd arvelos
docker build -t arvelos .
docker run -d --name arvelos -p 127.0.0.1:8801:8000 -v arvelos_data:/data arvelos
# then add the Nginx vhost in deploy/nginx.conf.template for arvelos.cloud + certbot
```

## Environment variables
| Var | Default | Purpose |
|-----|---------|---------|
| `PAYMENT_PROVIDER` | – | set to `mock` to force dummy payments for every currency regardless of the keys below (e.g. staging) |
| `STRIPE_API_KEY` / `STRIPE_WEBHOOK_SECRET` | – | live gateway for every currency except INR; unset = mock |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET` | – | live gateway for INR; unset = mock |
| `BASE_URL` | `https://astro.arvelos.cloud` | used in emails, gateway redirects, CORS |
| `ARVELOS_ALLOWED_ORIGINS` | – | comma-separated CORS origins; falls back to `BASE_URL` |
| `ARVELOS_FRONTEND` | – | path to `frontend/`; set to serve the site from the app |
| `ARVELOS_DB` | `../data/arvelos.db` | SQLite path (use `/data/...` on hosts) |
| `ARVELOS_DATA_DIR` | `../data` | base dir for the DB, generated reports, and the dev-mode email outbox — set to a persistent volume on hosts |
| `SMTP_HOST/PORT/USER/PASS/FROM` | – | email delivery; unset = write to outbox |

Gateway selection is automatic and per-order: an INR order goes to Razorpay
if its keys are set, a non-INR order goes to Stripe if its key is set;
either falls back to the built-in mock adapter (dummy payment, real
report) when its keys are absent — so the site works end-to-end with
zero payment config, and each gateway activates independently the moment
its keys are added.

Go-live checklist and the marketing/ads plan are in `DEPLOY_STEPS.md`,
`ARVELOS_HANDOFF.md`, and `marketing/CAMPAIGN.md`.

## Customer records & GDPR

Every order upserts a row in `customers` (deduped by lowercased email —
name, phone, order count, and the two separate opt-in flags/timestamps
for general updates and monthly Rashi/zodiac insights). It deliberately
excludes birth details, which stay in `orders` only. This is the table
to read from for anything community/outreach-related — never `orders`.

There's no admin UI or API for this yet — to handle a data access or
deletion request, run on the server (same env as the container):

```bash
python -m gdpr_tools export person@example.com   # full JSON of everything tied to that email
python -m gdpr_tools delete person@example.com    # scrubs PII, keeps only the accounting trail
python -m gdpr_tools optout person@example.com [marketing|zodiac|all]  # withdraw consent only —
                                                   # keeps the customer/order record, just stops
                                                   # future outreach; run this on any "stop emailing
                                                   # me" request until a real unsubscribe link exists
```

See the docstring in `backend/gdpr_tools.py` for exactly what each does.
