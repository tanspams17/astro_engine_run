# Arvelos — Personalized Astrology Report Engine

One-time-payment personalized astrology reports (Western / Vedic / Mixed),
calculated with Swiss Ephemeris, delivered as PDF. No subscription — that's
the product.

## Structure

```
/frontend          static site: landing + quiz + checkout + legal pages
/backend           FastAPI: orders, mock payment, chart engine, PDF, delivery
  /payment         gateway-agnostic PaymentAdapter (mock adapter shipped)
/pdf_templates     WeasyPrint HTML/CSS report template
/deploy            Dockerfile, docker-compose, nginx template
/marketing         ad videos, scripts, campaign plan, workflow diagram
```

## Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload           # API on :8000
# serve frontend: python3 -m http.server 8080 -d ../frontend
```

Dev mode (no SMTP_HOST set): delivery emails are written to `data/outbox/`.
Mock payments: any card number succeeds unless it ends in 0 (declined path).

## Deploy to VPS (arvelos.cloud)

1. DNS: A record `arvelos.cloud` (+ `www`) → VPS IP (Hostinger hPanel).
2. `rsync -a astro-engine/ user@vps:/opt/arvelos/`
3. `sudo mkdir -p /var/www/arvelos && sudo cp -r /opt/arvelos/frontend /var/www/arvelos/`
4. `cd /opt/arvelos/deploy && docker compose up -d --build`
5. Nginx: copy `deploy/nginx.conf.template` → `/etc/nginx/sites-available/arvelos.cloud`,
   symlink into `sites-enabled`, `nginx -t && systemctl reload nginx`.
6. TLS: `sudo certbot --nginx -d arvelos.cloud -d www.arvelos.cloud`
7. Smoke test: `curl https://arvelos.cloud/api/health`

## Going live checklist (account-gated)

- [ ] Payment gateway (Mollie recommended): account + KYB, then implement
      `backend/payment/mollie_adapter.py` against `interface.py`, swap one line
      in `app.py`. Confirm astrology is permitted in writing (spec §7).
- [ ] Transactional email (Postmark/SES): set SMTP_* env vars in compose file.
- [ ] Meta Business Manager: verify domain, install Pixel + Conversions API
      firing quiz_start / quiz_complete / purchase (backend events table
      already records these).
- [ ] Legal review of terms.html / privacy.html wording.

## Order lifecycle

`pending → paid → delivered`, `pending → failed`, `paid|delivered → refunded`.
Amounts stored in minor units, fixed at order creation. UTM params captured at
quiz-start (not just purchase) so drop-off is measurable per creative.
