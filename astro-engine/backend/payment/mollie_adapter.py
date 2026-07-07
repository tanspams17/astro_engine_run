"""
Mollie payment adapter — hosted checkout flow.
Set env: PAYMENT_PROVIDER=mollie, MOLLIE_API_KEY=test_xxx (later live_xxx).

Flow: create_order() creates a Mollie Payment and returns its hosted
checkout_url; the customer pays on Mollie's page; Mollie calls our
webhook with the payment id; verify_webhook() re-fetches the payment
from the API (that re-fetch IS the verification — Mollie webhooks are
deliberately unsigned) and reports paid/failed.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from .interface import (PaymentAdapter, OrderSession, ChargeResult,
                        WebhookEvent, RefundResult)

API = "https://api.mollie.com/v2"


class MollieAdapter(PaymentAdapter):
    def __init__(self, api_key: str | None = None,
                 base_url: str | None = None):
        self.key = api_key or os.environ["MOLLIE_API_KEY"]
        self.base_url = (base_url or
                         os.environ.get("BASE_URL", "https://arvelos.cloud"))

    # ---------------------------------------------------------- http
    def _req(self, method: str, path: str, payload: dict | None = None):
        req = urllib.request.Request(
            API + path,
            data=json.dumps(payload).encode() if payload else None,
            method=method,
            headers={"Authorization": f"Bearer {self.key}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())

    # ---------------------------------------------------------- api
    def create_order(self, amount_minor, currency, tier, customer_email,
                     order_id: str | None = None):
        value = f"{amount_minor / 100:.2f}"
        payment = self._req("POST", "/payments", {
            "amount": {"currency": currency, "value": value},
            "description": f"Arvelos {tier.title()} Report",
            "redirectUrl": f"{self.base_url}/?order={order_id or ''}",
            "webhookUrl": f"{self.base_url}/webhooks/payment",
            "metadata": {"order_id": order_id, "tier": tier,
                         "email": customer_email},
        })
        return OrderSession(
            session_id=payment["id"],
            checkout_url=payment["_links"]["checkout"]["href"],
            amount_minor=amount_minor, currency=currency, tier=tier)

    def charge(self, order_session_id, payment_details):
        # Hosted checkout: charging happens on Mollie's page, not via API.
        return ChargeResult(False, None,
                            "hosted checkout — customer pays on Mollie page")

    def verify_webhook(self, payload: bytes, signature: str) -> WebhookEvent:
        # Mollie posts form-encoded: id=tr_xxx. Verification = API re-fetch.
        try:
            params = urllib.parse.parse_qs(payload.decode())
            payment_id = params["id"][0]
        except Exception:
            return WebhookEvent(valid=False, event_type=None,
                                order_session_id=None)
        payment = self._req("GET", f"/payments/{payment_id}")
        status = payment.get("status")
        event = {"paid": "payment.paid",
                 "failed": "payment.failed",
                 "canceled": "payment.failed",
                 "expired": "payment.failed"}.get(status)
        return WebhookEvent(
            valid=True, event_type=event, order_session_id=payment_id,
            raw={"order_id": (payment.get("metadata") or {}).get("order_id"),
                 "status": status})

    def refund(self, order_id, amount_minor=None):
        try:
            payload = {}
            if amount_minor is not None:
                payment = self._req("GET", f"/payments/{order_id}")
                payload["amount"] = {
                    "currency": payment["amount"]["currency"],
                    "value": f"{amount_minor / 100:.2f}"}
            r = self._req("POST", f"/payments/{order_id}/refunds", payload)
            return RefundResult(True, r.get("id"))
        except Exception as e:
            return RefundResult(False, None, str(e))
