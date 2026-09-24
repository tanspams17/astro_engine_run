"""
Stripe payment adapter — hosted Checkout flow. The only real gateway in
use. Charges in USD, or INR for visitors in India (see geo.pricing_currency()).

Set env: STRIPE_API_KEY=sk_test_xxx (later sk_live_xxx, or preferably a
         restricted key rk_... scoped to Checkout Sessions + Refunds
         write — see backend/payment/GATEWAYS.md)
         STRIPE_WEBHOOK_SECRET=whsec_xxx

Flow: create_order() creates a Checkout Session and returns its hosted
checkout_url; the customer pays on Stripe's page; Stripe calls
/webhooks/stripe with a checkout.session.completed (or, for delayed
payment methods like bank transfers, checkout.session.async_payment_
succeeded) event, signed with STRIPE_WEBHOOK_SECRET — verify_webhook
checks that signature via the official SDK, no API re-fetch needed.

Uses the official `stripe` SDK (StripeClient, v1 namespace) per Stripe's
own integration guidance, not raw HTTP — see GATEWAYS.md.
"""
from __future__ import annotations

import os
import random
import string

import stripe

from .interface import (PaymentAdapter, OrderSession, ChargeResult,
                        WebhookEvent, RefundResult)

# Tags every Checkout Session created by this integration so it's
# identifiable in the Stripe Dashboard (see "Critical rules" in Stripe's
# integration guidance) — fixed per process, not per request.
_INTEGRATION_ID = "arvelos_hosted_checkout_" + "".join(
    random.choices(string.ascii_lowercase, k=8))

_EVENT_MAP = {
    "checkout.session.completed": "payment.paid",
    "checkout.session.async_payment_succeeded": "payment.paid",
    "checkout.session.expired": "payment.failed",
    "checkout.session.async_payment_failed": "payment.failed",
}


class StripeAdapter(PaymentAdapter):
    def __init__(self, api_key: str | None = None,
                 webhook_secret: str | None = None,
                 base_url: str | None = None):
        self.key = api_key or os.environ["STRIPE_API_KEY"]
        self.webhook_secret = webhook_secret or os.environ.get(
            "STRIPE_WEBHOOK_SECRET", "")
        self.base_url = (base_url or
                         os.environ.get("BASE_URL", "https://astro.arvelos.cloud"))
        self.client = stripe.StripeClient(self.key)

    # ---------------------------------------------------------- api
    def create_order(self, amount_minor, currency, tier, customer_email,
                     order_id=None):
        try:
            session = self.client.v1.checkout.sessions.create({
                "mode": "payment",
                "success_url": f"{self.base_url}/?order={order_id or ''}",
                "cancel_url": f"{self.base_url}/?cancelled={order_id or ''}",
                "customer_email": customer_email,
                "line_items": [{
                    "quantity": 1,
                    "price_data": {
                        "currency": currency.lower(),
                        "unit_amount": amount_minor,
                        "product_data": {"name": f"Arvelos {tier.title()} Report"},
                    },
                }],
                "metadata": {"order_id": order_id or ""},
                "payment_intent_data": {"metadata": {"order_id": order_id or ""}},
                "integration_identifier": _INTEGRATION_ID,
            })
        except stripe.StripeError as exc:
            raise RuntimeError(str(exc)) from exc
        return OrderSession(
            session_id=session.id, checkout_url=session.url,
            amount_minor=amount_minor, currency=currency, tier=tier)

    def charge(self, order_session_id, payment_details):
        # Hosted checkout: charging happens on Stripe's page, not via API.
        return ChargeResult(False, None,
                            "hosted checkout — customer pays on Stripe page")

    def verify_webhook(self, payload: bytes, signature: str) -> WebhookEvent:
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret)
        except (stripe.SignatureVerificationError, ValueError):
            return WebhookEvent(valid=False, event_type=None,
                                order_session_id=None)

        # .to_dict() up front: StripeObject supports attribute/item access
        # but not .get(), and metadata keys are caller-defined, not fixed
        # SDK fields, so a plain dict is the simplest safe shape here.
        obj = event["data"]["object"].to_dict()
        stripe_type = event["type"]
        mapped = _EVENT_MAP.get(stripe_type)
        order_id = (obj.get("metadata") or {}).get("order_id")
        return WebhookEvent(
            valid=True, event_type=mapped, order_session_id=obj.get("id"),
            raw={"order_id": order_id, "stripe_type": stripe_type,
                 "payment_status": obj.get("payment_status")})

    def refund(self, order_id, amount_minor=None):
        try:
            params = {"payment_intent": order_id}
            if amount_minor is not None:
                params["amount"] = amount_minor
            r = self.client.v1.refunds.create(params)
            return RefundResult(True, r.id)
        except stripe.StripeError as exc:
            return RefundResult(False, None, str(exc))
