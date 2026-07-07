# Arvelos — Go-Live Steps (10 minutes)

## Step 1 — Point the domain (hPanel, 2 min)
In https://hpanel.hostinger.com → Domains → arvelos.cloud → DNS records:

| Type | Name | Points to | TTL |
|---|---|---|---|
| A | @ | YOUR_VPS_IP | 300 |
| A | www | YOUR_VPS_IP | 300 |

(Your VPS IP is in hPanel → VPS → your server → IP address.)
Delete any conflicting A/AAAA/CNAME records for @ and www.

## Step 2 — Get the bundle onto the VPS (2 min)
From your Mac Terminal (the zip is in your Cowork outputs folder):

```bash
scp ~/path/to/arvelos_deploy.zip root@YOUR_VPS_IP:/root/
```

(Or use hPanel → VPS → File Manager and upload it to /root/.)

## Step 3 — One command (5 min)
In the VPS terminal (hPanel → VPS → Terminal, or `ssh root@YOUR_VPS_IP`):

```bash
cd /root && unzip -o arvelos_deploy.zip && sudo bash deploy.sh
```

The script installs Docker/Nginx/certbot if missing, starts the API
container, publishes the site, and issues the TLS certificate.
Safe to re-run any time.

## Step 4 — Smoke test
```bash
curl -s https://arvelos.cloud/api/health     # → {"ok":true,...}
```
Then open https://arvelos.cloud in a browser and run a test purchase
(mock mode: any card number works; one ending in 0 simulates a decline).

## Later — Switch on real payments (when Mollie account is approved)
1. Get written confirmation from Mollie that astrology reports are permitted.
2. On the VPS: edit `/opt/arvelos/deploy/docker-compose.yml`
   - `PAYMENT_PROVIDER=mollie`
   - `MOLLIE_API_KEY=test_...` (test first, then `live_...`)
3. `cd /opt/arvelos/deploy && docker compose up -d`
4. Test with Mollie test key (their checkout page offers fake payment
   methods), then swap to the live key.

## Later — Email delivery (any SMTP provider)
Uncomment and fill `SMTP_HOST/PORT/USER/PASS/FROM` in the same compose file,
`docker compose up -d`. Until then, delivery emails are written to
/opt/arvelos data volume outbox (download links still work on-site).
