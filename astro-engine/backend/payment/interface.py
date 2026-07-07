"""
Payment adapter interface — gateway-agnostic by design.
A real gateway (Mollie recommended) implements this ABC later without
touching the rest of the system. No card data ever touches this codebase.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OrderSession:
    session_id: str
    checkout_url: str | None   # hosted checkout page, if gateway provides one
    amount_minor: int          # cents / paise — fixed at order creation
    currency: str
    tier: str


@dataclass
class ChargeResult:
    success: bool
    charge_id: str | None
    error: str | None = None


@dataclass
class WebhookEvent:
    valid: bool
    event_type: str | None     # "payment.paid" | "payment.failed" | "refund"
    order_session_id: str | None
    raw: dict | None = None


@dataclass
class RefundResult:
    success: bool
    refund_id: str | None
    error: str | None = None


class PaymentAdapter(ABC):
    @abstractmethod
    def create_order(self, amount_minor: int, currency: str, tier: str,
                     customer_email: str) -> OrderSession: ...

    @abstractmethod
    def charge(self, order_session_id: str,
               payment_details: dict) -> ChargeResult: ...

    @abstractmethod
    def verify_webhook(self, payload: bytes,
                       signature: str) -> WebhookEvent: ...

    @abstractmethod
    def refund(self, order_id: str,
               amount_minor: int | None = None) -> RefundResult: ...
