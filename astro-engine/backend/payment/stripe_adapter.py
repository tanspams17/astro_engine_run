"""
Stripe payment adapter — hosted Checkout flow. Used for every currency
except INR (Razorpay handles India — see razorpay_adapter.py).

Set env: STRIPE_API_KEY=sk_test_xxx (later sk_live_xxx),
         STRIPE_WEBHOOK_SECRET=whsec_xxx

Flow: create_order() creates a Checkout Session and returns its hosted
checkout_url; the customer pays on Stripe's page; Stripe calls
/webhooks/stripe with a checkout.session.completed event, signed with
STRIPE_WEBHOOK_SECRET (verify_webhook checks that signature — no API
re-fetch needed, unlike Mollie).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from .interface import (PaymentAdapter, OrderSession, ChargeResult,
                        WebhookEvent, RefundResult)

API = "https://api.stripe.com/v1"


class StripeAdapter(PaymentAdapter):
    def __init__(self, api_key: str | None = None,
                 webhook_secret: str | None = None,
                 base_url: str | None = None):
        self.key = api_key or os.environ["STRIPE_API_KEY"]
        self.webhook_secret = webhook_secret or os.environ.get(
            "STRIPE_WEBHOOK_SECRET", "")
        self.base_url = (base_url or
                         os.environ.get("BASE_URL", "https://astro.arvelos.cloud"))

    # ---------------------------------------------------------- http
    def _req(self, method: str, path: str, form: dict | None = None):
        body = urllib.parse.urlencode(form or {}).encode() if form else None
        req = urllib.request.Request(
            API + path, data=body, method=method,
            headers={"Authorization": f"Bearer {self.key}",
                     "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = json.loads(e.read())
            raise RuntimeError(
                detail.get("error", {}).get("message", str(e))) from e

    # ---------------------------------------------------------- api
    def create_order(self, amount_minor, currency, tier, customer_email,
                     order_id=None):
        form = {
            "mode": "payment",
            "success_url": f"{self.base_url}/?order={order_id or ''}",
            "cancel_url": f"{self.base_url}/?order={order_id or ''}",
            "customer_email": customer_email,
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": currency.lower(),
            "line_items[0][price_data][unit_amount]": str(amount_minor),
            "line_items[0][price_data][product_data][name]":
                f"Arvelos {tier.title()} Report",
            "metadata[order_id]": order_id or "",
            "payment_intent_data[metadata][order_id]": order_id or "",
        }
        session = self._req("POST", "/checkout/sessions", form)
        return OrderSession(
            session_id=session["id"], checkout_url=session["url"],
            amount_minor=amount_minor, currency=currency, tier=tier)

    def charge(self, order_session_id, payment_details):
        # Hosted checkout: charging happens on Stripe's page, not via API.
        return ChargeResult(False, None,
                            "hosted checkout — customer pays on Stripe page")

    def verify_webhook(self, payload: bytes, signature: str) -> WebhookEvent:
        # Stripe-Signature header: "t=<ts>,v1=<hmac_hex>[,v1=<hmac_hex>...]"
        # Verify by recomputing HMAC-SHA256(webhook_secret, f"{t}.{payload}")
        # and comparing against every v1 value present (Stripe may send
        # more than one during secret rotation).
        try:
            pairs = [p.split("=", 1) for p in signature.split(",") if "=" in p]
            ts = next(v for k, v in pairs if k == "t")
            candidates = [v for k, v in pairs if k == "v1"]
            signed_payload = f"{ts}.{payload.decode()}".encode()
            expected = hmac.new(self.webhook_secret.encode(), signed_payload,
                                hashlib.sha256).hexdigest()
            if not any(hmac.compare_digest(expected, c) for c in candidates):
                return WebhookEvent(valid=False, event_type=None,
                                    order_session_id=None)
            # reject stale signatures (>5 min) to limit replay risk
            if abs(time.time() - int(ts)) > 300:
                return WebhookEvent(valid=False, event_type=None,
                                    order_session_id=None)
        except Exception:
            return WebhookEvent(valid=False, event_type=None,
                                order_session_id=None)

        data = json.loads(payload)
        stripe_type = data.get("type")
        obj = (data.get("data") or {}).get("object") or {}
        event = {
            "checkout.session.completed": "payment.paid",
            "checkout.session.expired": "payment.failed",
        }.get(stripe_type)
        order_id = (obj.get("metadata") or {}).get("order_id")
        return WebhookEvent(
            valid=True, event_type=event, order_session_id=obj.get("id"),
            raw={"order_id": order_id, "stripe_type": stripe_type})

    def refund(self, order_id, amount_minor=None):
        try:
            payload = {"payment_intent": order_id}
            if amount_minor is not None:
                payload["amount"] = str(amount_minor)
            r = self._req("POST", "/refunds", payload)
            return RefundResult(True, r.get("id"))
        except Exception as e:
            return RefundResult(False, None, str(e))
