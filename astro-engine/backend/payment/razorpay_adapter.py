"""
Razorpay payment adapter — hosted Payment Links flow. Used for INR only
(everything else goes through Stripe — see stripe_adapter.py).

Set env: RAZORPAY_KEY_ID=rzp_test_xxx, RAZORPAY_KEY_SECRET=xxx
         RAZORPAY_WEBHOOK_SECRET=xxx (set to the same value in the
         Razorpay dashboard's webhook config)

Flow: create_order() creates a Payment Link and returns its hosted
checkout_url (short_url); the customer pays there (cards/UPI/wallets);
Razorpay calls /webhooks/razorpay with a payment_link.paid event, signed
with RAZORPAY_WEBHOOK_SECRET.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request

from .interface import (PaymentAdapter, OrderSession, ChargeResult,
                        WebhookEvent, RefundResult)

API = "https://api.razorpay.com/v1"


class RazorpayAdapter(PaymentAdapter):
    def __init__(self, key_id: str | None = None, key_secret: str | None = None,
                 webhook_secret: str | None = None, base_url: str | None = None):
        self.key_id = key_id or os.environ["RAZORPAY_KEY_ID"]
        self.key_secret = key_secret or os.environ["RAZORPAY_KEY_SECRET"]
        self.webhook_secret = webhook_secret or os.environ.get(
            "RAZORPAY_WEBHOOK_SECRET", "")
        self.base_url = (base_url or
                         os.environ.get("BASE_URL", "https://astro.arvelos.cloud"))

    # ---------------------------------------------------------- http
    def _auth_header(self) -> str:
        token = base64.b64encode(
            f"{self.key_id}:{self.key_secret}".encode()).decode()
        return f"Basic {token}"

    def _req(self, method: str, path: str, payload: dict | None = None):
        req = urllib.request.Request(
            API + path,
            data=json.dumps(payload).encode() if payload else None,
            method=method,
            headers={"Authorization": self._auth_header(),
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = json.loads(e.read())
            raise RuntimeError(
                (detail.get("error") or {}).get("description", str(e))) from e

    # ---------------------------------------------------------- api
    def create_order(self, amount_minor, currency, tier, customer_email,
                     order_id=None):
        if currency != "INR":
            raise ValueError("RazorpayAdapter only supports INR")
        payload = {
            "amount": amount_minor,
            "currency": currency,
            "description": f"Arvelos {tier.title()} Report",
            "customer": {"email": customer_email},
            "notify": {"email": False, "sms": False},
            "reminder_enable": False,
            "callback_url": f"{self.base_url}/?order={order_id or ''}",
            "callback_method": "get",
            "notes": {"order_id": order_id or "", "tier": tier},
        }
        link = self._req("POST", "/payment_links", payload)
        return OrderSession(
            session_id=link["id"], checkout_url=link["short_url"],
            amount_minor=amount_minor, currency=currency, tier=tier)

    def charge(self, order_session_id, payment_details):
        # Hosted checkout: charging happens on Razorpay's page, not via API.
        return ChargeResult(False, None,
                            "hosted checkout — customer pays on Razorpay page")

    def verify_webhook(self, payload: bytes, signature: str) -> WebhookEvent:
        expected = hmac.new(self.webhook_secret.encode(), payload,
                            hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature or ""):
            return WebhookEvent(valid=False, event_type=None,
                                order_session_id=None)
        data = json.loads(payload)
        rp_event = data.get("event")
        event = {
            "payment_link.paid": "payment.paid",
            "payment_link.cancelled": "payment.failed",
            "payment_link.expired": "payment.failed",
        }.get(rp_event)
        link_entity = ((data.get("payload") or {}).get("payment_link") or {}).get("entity") or {}
        order_id = (link_entity.get("notes") or {}).get("order_id")
        return WebhookEvent(
            valid=True, event_type=event, order_session_id=link_entity.get("id"),
            raw={"order_id": order_id, "razorpay_event": rp_event})

    def refund(self, order_id, amount_minor=None):
        try:
            payload = {}
            if amount_minor is not None:
                payload["amount"] = amount_minor
            # order_id here is the Razorpay *payment* id (pay_xxx), which the
            # caller must have captured from the payment.paid webhook —
            # payment links don't refund by link id.
            r = self._req("POST", f"/payments/{order_id}/refund", payload)
            return RefundResult(True, r.get("id"))
        except Exception as e:
            return RefundResult(False, None, str(e))
