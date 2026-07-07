#!/usr/bin/env bash
# =============================================================================
# Arvelos one-command deployment — Ubuntu 22/24 VPS (Hostinger)
# Usage:  sudo bash deploy.sh
# Expects this script to sit next to the unzipped astro-engine/ folder,
# OR next to arvelos_deploy.zip (it will unzip it).
# Idempotent: safe to re-run after changes.
# =============================================================================
set -euo pipefail

DOMAIN="arvelos.cloud"
APP_DIR="/opt/arvelos"
WEB_DIR="/var/www/arvelos"
EMAIL="tanspams17@gmail.com"   # for certbot notices

echo "==> [1/7] Locating bundle"
cd "$(dirname "$0")"
if [ ! -d astro-engine ] && [ -f arvelos_deploy.zip ]; then
  apt-get install -y -qq unzip >/dev/null 2>&1 || true
  unzip -oq arvelos_deploy.zip
fi
[ -d astro-engine ] || { echo "ERROR: astro-engine/ not found next to deploy.sh"; exit 1; }

echo "==> [2/7] Installing prerequisites (docker, nginx, certbot)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh
docker compose version >/dev/null 2>&1 || apt-get install -y -qq docker-compose-plugin
apt-get install -y -qq nginx certbot python3-certbot-nginx rsync

echo "==> [3/7] Syncing application to $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete astro-engine/ "$APP_DIR/"

echo "==> [4/7] Publishing static frontend to $WEB_DIR"
mkdir -p "$WEB_DIR"
rsync -a --delete "$APP_DIR/frontend/" "$WEB_DIR/frontend/"

echo "==> [5/7] Building + starting API container"
cd "$APP_DIR/deploy"
docker compose up -d --build
sleep 5
curl -sf http://127.0.0.1:8801/api/health >/dev/null \
  && echo "    API container healthy" \
  || { echo "ERROR: API health check failed"; docker compose logs --tail 30; exit 1; }

echo "==> [6/7] Configuring Nginx for $DOMAIN"
sed "s|/var/www/arvelos/frontend|$WEB_DIR/frontend|" nginx.conf.template \
  > /etc/nginx/sites-available/$DOMAIN
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "==> [7/7] TLS certificate (requires DNS A record already pointing here)"
if certbot certificates 2>/dev/null | grep -q "$DOMAIN"; then
  echo "    Certificate already present"
else
  certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
    --non-interactive --agree-tos -m "$EMAIL" --redirect \
    || echo "WARN: certbot failed — check that the DNS A record for $DOMAIN points to this VPS, then re-run: certbot --nginx -d $DOMAIN -d www.$DOMAIN"
fi

echo
echo "============================================================"
echo " Deployed. Smoke test:"
echo "   curl -s https://$DOMAIN/api/health"
echo
echo " To go live with Mollie later, edit $APP_DIR/deploy/docker-compose.yml:"
echo "   PAYMENT_PROVIDER=mollie / MOLLIE_API_KEY=live_xxx / SMTP_* vars"
echo " then: cd $APP_DIR/deploy && docker compose up -d"
echo "============================================================"
