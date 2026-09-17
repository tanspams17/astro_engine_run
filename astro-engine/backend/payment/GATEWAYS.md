# Going live: Stripe + Razorpay

Arvelos routes each order to a gateway **by currency**, automatically:

| Currency | Gateway | Adapter |
|---|---|---|
| `INR` | Razorpay | `razorpay_adapter.py` |
| `USD` (and any other currency added later) | Stripe | `stripe_adapter.py` |

Either falls back to `mock_adapter.py` (dummy payment, real report — the
site's current state) automatically whenever that gateway's keys aren't
set. There is no "flip a switch" step — adding a gateway's keys activates
it immediately for its currency, independent of the other gateway.

## Stripe (non-India)

1. Create a Stripe account, grab the **secret key** (`sk_test_...` to
   start, `sk_live_...` when ready) from the Dashboard → Developers → API keys.
2. Add a webhook endpoint in the Dashboard pointing at
   `https://astro.arvelos.cloud/webhooks/stripe`, subscribed to
   `checkout.session.completed` (and `checkout.session.expired` if you
   want failed/abandoned checkouts recorded). Copy the **signing secret**
   (`whsec_...`).
3. Set on the server: `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`.

## Razorpay (India)

1. Create a Razorpay account (needs India business KYC to accept live
   payments — test mode works without it). Grab the **Key ID** and **Key
   Secret** from Settings → API Keys.
2. Add a webhook in Settings → Webhooks pointing at
   `https://astro.arvelos.cloud/webhooks/razorpay`, subscribed to
   `payment_link.paid` (and `payment_link.expired`/`.cancelled` if
   wanted). Set the same secret you'll use for `RAZORPAY_WEBHOOK_SECRET`
   when creating the webhook — Razorpay doesn't generate this one for you.
3. Set on the server: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`,
   `RAZORPAY_WEBHOOK_SECRET`.

## Deploying the keys

Add the env vars to `deploy/docker-compose.yml` (commented placeholders
already there) and run `docker compose up -d` — no rebuild needed, it's
just an environment change. Test with each gateway's test-mode keys
first; a test-mode order goes through the exact same code path as a live
one, so it's a real end-to-end check before switching to live keys.

## Region default (not payment routing)

`/api/geo` does an offline IP→country lookup (via `geoip2fast`, no
external API call) purely to default the currency toggle — India visitors
see INR pre-selected, everyone else sees USD. It never decides which
gateway actually gets used; the **currency the order is placed in** does
that. A visitor can always switch currency manually before paying.
