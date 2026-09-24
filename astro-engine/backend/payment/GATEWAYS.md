# Going live: Stripe

Arvelos sells via Stripe in **USD, or INR for visitors in India**. The
currency is chosen on the server from the visitor's IP
(`geo.pricing_currency()`); `/api/prices`, `/api/coupon/check` and
`/api/orders` all use it and ignore any `currency` the client sends. INR
prices live next to USD in `orders.PRICES`.

History: the site once had an INR/Razorpay path where the *client* picked
the currency (a frontend toggle, or any direct API call), so anyone could
check out at the India price. That was removed on 2026-09-20; INR came back
on 2026-09-24 as a server-decided currency on Stripe, with no toggle.
Razorpay is not used. Indian cards need international/online transactions
enabled, since the charge is processed by a UK company.

Falls back to `mock_adapter.py` (dummy payment, real report) automatically
whenever `STRIPE_API_KEY` isn't set.

## Stripe

`stripe_adapter.py` uses the official `stripe` Python SDK (`StripeClient`,
v1 namespace) — Stripe's own recommended pattern, not raw HTTP.

1. Create a Stripe account, then create a **restricted API key** (RAK,
   `rk_test_.../rk_live_...`) at Dashboard → Developers → API keys →
   Create restricted key — Stripe's recommended alternative to a full
   secret key, especially when handing a key to an AI agent. This
   integration only needs: **Checkout Sessions: Write**, **Refunds:
   Write**. A plain secret key (`sk_test_.../sk_live_...`) works too as a
   drop-in if you'd rather skip this step.
2. Add a webhook endpoint in the Dashboard pointing at
   `https://astro.arvelos.cloud/webhooks/stripe`, subscribed to
   `checkout.session.completed`, `checkout.session.async_payment_succeeded`,
   `checkout.session.async_payment_failed`, and `checkout.session.expired`
   (the async ones cover delayed payment methods like bank transfers —
   funds aren't confirmed until later for those). Copy the **signing
   secret** (`whsec_...`).
3. Set on the server: `STRIPE_API_KEY` (works for either an `sk_` or `rk_`
   key — same env var), `STRIPE_WEBHOOK_SECRET`.

## Deploying the keys

Copy `deploy/.env.example` to `deploy/.env` on the VPS and fill in the
real values there — `.env` is gitignored, so secrets never enter version
control; `docker-compose.yml` only references `${STRIPE_API_KEY}` etc.
Then `docker compose up -d` — no rebuild needed, it's just an environment
change. Test with Stripe's test-mode keys first; a test-mode order goes
through the exact same code path as a live one, so it's a real end-to-end
check before switching to live keys.

## Why not Stripe Invoicing

Invoicing (Stripe's `Invoice`/`InvoiceItem` API) is for billing someone
after the fact — recurring/subscription charges, or B2B where a customer
expects a formal invoice with payment terms (net-30, etc.). Arvelos sells
a single digital report for immediate card payment; Checkout already
handles that up front and Stripe auto-emails a receipt on successful
payment (toggle at Dashboard → Settings → Customer emails). Adding
Invoicing on top would mean generating an invoice for a purchase that's
already been paid, which doesn't fit the flow and adds another API
surface for no benefit here. Revisit this only if Arvelos ever sells to
businesses that specifically require invoice documents (e.g. a corporate
bulk-report purchase with PO/NET terms) — that's a real Invoicing use
case, this isn't it.

## Region detection (not payment routing)

`/api/geo` does an offline IP→country lookup (via `geoip2fast`, no
external API call) purely to default the phone country-code dropdown in
the order form. It doesn't affect pricing or currency at all — every
order is USD, regardless of where the visitor is.
