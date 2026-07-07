# Mollie drop-in plan (when the account + KYB exist)

Before signing anything: get written confirmation from Mollie that astrology
/ personalized spiritual reports are permitted merchandise (spec §7).

## Steps

1. `pip install mollie-api-python`, add to requirements.txt.
2. Create `mollie_adapter.py` implementing `PaymentAdapter`:
   - `create_order` → Mollie Payments API (`amount`, `description`,
     `redirectUrl=https://arvelos.cloud/?paid=1`, `webhookUrl=
     https://arvelos.cloud/webhooks/payment`, `metadata={order_id}`) —
     return its `checkout_url`; frontend redirects to hosted checkout
     instead of collecting card fields (drop the card inputs, keep email).
3. `verify_webhook`: Mollie webhooks send a payment id; re-fetch the payment
   from the API (that IS the verification) and map status →
   `payment.paid` / `payment.failed`.
4. In `app.py`: `payment = MollieAdapter(api_key=os.environ["MOLLIE_KEY"])`,
   and move fulfilment (`_fulfil`) from `/api/pay` to the webhook handler.
5. Set `MOLLIE_KEY` via docker-compose env. Test mode key first
   (`test_...`), full flow, then live key after KYB.

Order states, amounts-in-minor-units, and UTM plumbing all stay unchanged —
that's what the interface was for.
