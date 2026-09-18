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

Copy `deploy/.env.example` to `deploy/.env` on the VPS and fill in the
real values there — `.env` is gitignored, so secrets never enter version
control; `docker-compose.yml` only references `${STRIPE_API_KEY}` etc.
Then `docker compose up -d` — no rebuild needed, it's just an environment
change. Test with each gateway's test-mode keys first; a test-mode order
goes through the exact same code path as a live one, so it's a real
end-to-end check before switching to live keys.

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

## Region default (not payment routing)

`/api/geo` does an offline IP→country lookup (via `geoip2fast`, no
external API call) purely to default the currency toggle — India visitors
see INR pre-selected, everyone else sees USD. It never decides which
gateway actually gets used; the **currency the order is placed in** does
that. A visitor can always switch currency manually before paying.
