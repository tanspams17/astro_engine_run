"""
Mock payment adapter — makes the full flow testable end-to-end with dummy
payments. Swap for mollie_adapter.py (same interface) when the gateway
account exists. See MOLLIE_INTEGRATION.md for the drop-in plan.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid

from .interface import (PaymentAdapter, OrderSession, ChargeResult,
                        WebhookEvent, RefundResult)

MOCK_WEBHOOK_SECRET = b"arvelos-mock-secret-change-me"


class MockAdapter(PaymentAdapter):
    """In-memory sessions; approves any charge unless card number ends in 0."""

    def __init__(self):
        self._sessions: dict[str, OrderSession] = {}

    def create_order(self, amount_minor, currency, tier, customer_email):
        sid = f"mock_{uuid.uuid4().hex[:16]}"
        session = OrderSession(session_id=sid, checkout_url=None,
                               amount_minor=amount_minor, currency=currency,
                               tier=tier)
        self._sessions[sid] = session
        return session

    def charge(self, order_session_id, payment_details):
        if order_session_id not in self._sessions:
            return ChargeResult(False, None, "unknown session")
        card = str(payment_details.get("card_number", "4242"))
        if card.endswith("0"):  # deterministic failure path for testing
            return ChargeResult(False, None, "card declined (mock rule)")
        return ChargeResult(True, f"ch_{uuid.uuid4().hex[:12]}")

    def verify_webhook(self, payload, signature):
        expected = hmac.new(MOCK_WEBHOOK_SECRET, payload,
                            hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return WebhookEvent(valid=False, event_type=None,
                                order_session_id=None)
        data = json.loads(payload)
        return WebhookEvent(valid=True, event_type=data.get("type"),
                            order_session_id=data.get("session_id"),
                            raw=data)

    def refund(self, order_id, amount_minor=None):
        return RefundResult(True, f"re_{uuid.uuid4().hex[:12]}")
