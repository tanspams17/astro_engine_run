"""
Arvelos FastAPI backend.
Endpoints: quiz session (UTM capture), order creation, mock checkout,
webhook, report generation + delivery, download.
"""
from __future__ import annotations

import datetime as dt
import logging
import os

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, EmailStr, Field, model_validator

try:
    from . import orders, geo
    from .delivery import send_report_email, send_lead_teaser_email
    from .report_generator import (generate_report, TIER_NAMES,
                                   generate_compatibility_report, COMPAT_TIER_NAMES,
                                   generate_lead_teaser)
    from .payment.mock_adapter import MockAdapter
except ImportError:
    import orders
    import geo
    from delivery import send_report_email, send_lead_teaser_email
    from report_generator import (generate_report, TIER_NAMES,
                                  generate_compatibility_report, COMPAT_TIER_NAMES,
                                  generate_lead_teaser)
    from payment.mock_adapter import MockAdapter

# openapi_url=None too: /docs and /redoc were already disabled, but the raw
# schema was still served at /openapi.json regardless — same information
# disclosure via a different door.
app = FastAPI(title="Arvelos API", docs_url=None, redoc_url=None, openapi_url=None)


# Reject oversized request bodies before they're parsed — checked from
# Content-Length so it costs nothing to enforce. Every real payload here
# (an order, a coupon check) is at most a few KB; this caps it two orders
# of magnitude above that, purely to stop someone lobbing multi-MB/GB
# bodies at a JSON endpoint. Not a substitute for a reverse-proxy body
# limit (a client can omit/lie about Content-Length with chunked
# transfer), but it's a free, cheap first line of defense.
_MAX_BODY_BYTES = 256_000


@app.middleware("http")
async def _limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > _MAX_BODY_BYTES:
                return JSONResponse({"detail": "request body too large"}, status_code=413)
        except ValueError:
            pass
    return await call_next(request)
_local_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
_data_dir = os.environ.get("ARVELOS_DATA_DIR", _local_data_dir)
_allowed_origins = [origin.strip() for origin in os.environ.get(
    "ARVELOS_ALLOWED_ORIGINS", os.environ.get("BASE_URL", "")
).split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_allowed_origins,
                   allow_methods=["GET", "POST"],
                   allow_headers=["*"])
# cities.json alone is ~12MB uncompressed (150k cities for birth-place
# autocomplete) — gzip cuts that to ~2.5MB on the wire for any client
# that sends Accept-Encoding: gzip (i.e. every real browser).
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ------------------------------------------------------------ payment gateway
#
# Stripe only. Visitors in India are priced and charged in INR, everyone
# else in USD; the currency is decided server-side from the visitor's IP
# (geo.pricing_currency) and never taken from the client. (An earlier
# INR/Razorpay path let the client pick the currency, so anyone could
# check out at the India price; any `currency` a client still sends is
# now ignored.) Falls back to the
# mock adapter automatically if STRIPE_API_KEY isn't configured, so the
# site stays fully functional (dummy payment, real report) before go-live.
# PAYMENT_PROVIDER=mock forces mock regardless (useful for staging).
_FORCE_MOCK = os.environ.get("PAYMENT_PROVIDER", "").strip().lower() == "mock"
_mock_adapter = MockAdapter()
_stripe_adapter = None


def _provider_name() -> str:
    if _FORCE_MOCK:
        return "mock"
    return "stripe" if os.environ.get("STRIPE_API_KEY") else "mock"


def get_adapter():
    global _stripe_adapter
    if _provider_name() == "mock":
        return _mock_adapter
    if _stripe_adapter is None:
        from payment.stripe_adapter import StripeAdapter
        _stripe_adapter = StripeAdapter()
    return _stripe_adapter


REPORT_DIR = os.environ.get(
    "ARVELOS_REPORT_DIR",
    os.path.join(_data_dir, "reports"),
)

# Coupon codes that make an order free (amount_minor=0 — bypasses the
# payment gateway entirely, see /api/orders and /api/pay below).
# FREENOW07 is temporary, added 2026-09-20 at Raj's request — remove it
# from this set whenever he says to stop it, nothing else references it.
FREE_COUPON_CODES = {"ASTRO100", "FREENOW07"}
logger = logging.getLogger(__name__)


def _apply_coupon(amount_minor: int, coupon_code: str | None) -> int:
    if not coupon_code:
        return amount_minor
    code = coupon_code.strip().upper()
    if code in FREE_COUPON_CODES:
        return 0
    lead = orders.validate_discount_code(code)
    if lead:
        return round(amount_minor * (100 - lead["discount_pct"]) / 100)
    raise ValueError("invalid coupon code")


orders.init_db()


# ------------------------------------------------------------ models


class QuizStart(BaseModel):
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None
    gclid: str | None = Field(default=None, max_length=200)
    gbraid: str | None = Field(default=None, max_length=200)
    wbraid: str | None = Field(default=None, max_length=200)


FOCUS_PATTERN = "^(personality|love|career|growth)$"

COMPAT_TIERS = {"zodiac_compat", "vedic_compat", "mixed_compat"}
ALL_TIERS_PATTERN = "^(western|vedic|mixed|zodiac_compat|vedic_compat|mixed_compat)$"
# Tiers that have a Hindi report. The server, not the form, decides.
HINDI_TIERS = {"vedic", "vedic_compat"}


class OrderIn(BaseModel):
    quiz_session_id: str | None = Field(default=None, max_length=64)
    email: EmailStr
    name: str = Field(min_length=1, max_length=80)
    phone: str | None = Field(default=None, max_length=32)  # optional, support reference only
    tier: str = Field(pattern=ALL_TIERS_PATTERN)
    # Ignored: currency is set server-side from the visitor's IP (see
    # geo.pricing_currency). Kept optional so older clients don't break.
    currency: str | None = Field(default=None, max_length=3)
    coupon_code: str | None = Field(default=None, max_length=40)
    birth_date: str = Field(max_length=10)          # YYYY-MM-DD
    birth_time: str | None = Field(default=None, max_length=5)   # HH:MM, or None if unknown
    gender: str = Field(default="unspecified",
                        pattern="^(male|female|unspecified)$")
    # Free text — the frontend's city picker is UI only, never enforced
    # server-side, so this stays a plain string; capped only to keep a
    # malicious/junk payload from bloating storage and the generated PDF.
    birth_place: str = Field(max_length=200)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    tz: str = Field(max_length=64)                  # IANA name, e.g. Asia/Kolkata
    focus_areas: list[str] = Field(default_factory=list, max_length=8)
    primary_focus: str | None = Field(default=None, pattern=FOCUS_PATTERN)
    marketing_opt_in: bool = False   # MUST default False (GDPR/PECR)
    zodiac_insights_opt_in: bool = False   # separate consent, MUST default False
    language: str = Field(default="en", pattern="^(en|hi)$")

    # Compatibility-report tiers only — "Your Partner's details". Optional
    # here at the field level; the validator below enforces presence/
    # absence based on `tier`, the same way pricing is derived from tier
    # rather than trusted from the client.
    partner_name: str | None = Field(default=None, min_length=1, max_length=80)
    partner_birth_date: str | None = Field(default=None, max_length=10)
    partner_birth_time: str | None = Field(default=None, max_length=5)
    partner_birth_place: str | None = Field(default=None, max_length=200)
    partner_lat: float | None = Field(default=None, ge=-90, le=90)
    partner_lon: float | None = Field(default=None, ge=-180, le=180)
    partner_tz: str | None = Field(default=None, max_length=64)
    partner_gender: str | None = Field(default="unspecified",
                                       pattern="^(male|female|unspecified)$")

    @model_validator(mode="after")
    def _language_available_for_tier(self):
        if self.language == "hi" and self.tier not in HINDI_TIERS:
            raise ValueError("Hindi is not available for this report")
        return self

    @model_validator(mode="after")
    def _partner_fields_match_tier(self):
        is_compat = self.tier in COMPAT_TIERS
        required = (self.partner_name, self.partner_birth_date, self.partner_birth_place,
                   self.partner_lat, self.partner_lon, self.partner_tz)
        if is_compat and any(v is None for v in required):
            raise ValueError("partner details are required for a compatibility report")
        if not is_compat and any(v is not None for v in required):
            raise ValueError("partner details are only accepted for a compatibility report")
        return self


class PayIn(BaseModel):
    order_id: str = Field(max_length=64)
    payment_details: dict = Field(default_factory=dict)


class CouponCheckIn(BaseModel):
    tier: str = Field(pattern=ALL_TIERS_PATTERN)
    currency: str | None = Field(default=None, max_length=3)  # ignored, see OrderIn
    coupon_code: str = Field(min_length=1, max_length=40)


class LeadIn(BaseModel):
    """Free 2-page preview: no payment, no tier — just enough to compute a
    real (if short) chart and email it, plus a discount code toward a
    real report."""
    email: EmailStr
    name: str = Field(min_length=1, max_length=80)
    birth_date: str = Field(max_length=10)
    birth_time: str | None = Field(default=None, max_length=5)
    birth_place: str = Field(max_length=200)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    tz: str = Field(max_length=64)
    gender: str = Field(default="unspecified",
                        pattern="^(male|female|unspecified)$")
    primary_focus: str | None = Field(default=None, pattern=FOCUS_PATTERN)
    quiz_session_id: str | None = Field(default=None, max_length=64)


# ------------------------------------------------------------ endpoints


@app.get("/api/health")
def health():
    try:
        os.makedirs(REPORT_DIR, exist_ok=True)
        probe = os.path.join(REPORT_DIR, ".healthcheck")
        with open(probe, "w") as handle:
            handle.write("ok")
        os.remove(probe)
    except OSError as exc:
        raise HTTPException(503, f"report storage unavailable: {exc}")
    return {"ok": True, "service": "arvelos"}


@app.get("/api/config")
def config():
    provider = _provider_name()
    return {"provider": provider,
            # legacy field some older clients may still read
            "payment_provider": provider}


@app.get("/api/geo")
def geo_lookup(request: Request):
    # Phone-country-code default in the order form. Pricing currency comes
    # from /api/prices, decided by the same IP lookup.
    country = geo.country_for_ip(geo.client_ip(request))
    return {"country": country}


CURRENCY_SYMBOL = {"USD": "$", "INR": "₹", "GBP": "£"}


@app.get("/api/prices")
def prices(request: Request):
    currency = geo.pricing_currency(request)
    return {"currency": currency, "symbol": CURRENCY_SYMBOL[currency],
            "prices": {tier: by_cur[currency]
                       for tier, by_cur in orders.PRICES.items()}}


@app.post("/api/coupon/check")
def coupon_check(c: CouponCheckIn, request: Request):
    """Read-only: lets the checkout form validate a code and preview the
    resulting price before the customer commits to an order."""
    base = orders.PRICES[c.tier][geo.pricing_currency(request)]
    try:
        amount_minor = _apply_coupon(base, c.coupon_code)
    except ValueError:
        return {"valid": False, "amount_minor": base}
    return {"valid": True, "amount_minor": amount_minor}


@app.post("/api/quiz/start")
def quiz_start(q: QuizStart):
    sid = orders.start_quiz_session(q.model_dump())
    return {"quiz_session_id": sid}


@app.post("/api/quiz/complete/{session_id}")
def quiz_complete(session_id: str):
    orders.complete_quiz(session_id)
    return {"ok": True}


@app.post("/api/orders")
def create_order(o: OrderIn, request: Request):
    # validate birth datetime + tz early, so payment never precedes a
    # chart we can't calculate
    try:
        dt.datetime.strptime(
            o.birth_date + " " + (o.birth_time or "12:00"),
            "%Y-%m-%d %H:%M")
        from zoneinfo import ZoneInfo
        ZoneInfo(o.tz)
    except Exception:
        raise HTTPException(400, "invalid birth date/time/timezone")

    is_compat = o.tier in COMPAT_TIERS
    if is_compat:
        # Same reasoning as the primary person above: payment must never
        # precede a chart the engine can't actually calculate.
        try:
            dt.datetime.strptime(
                o.partner_birth_date + " " + (o.partner_birth_time or "12:00"),
                "%Y-%m-%d %H:%M")
            from zoneinfo import ZoneInfo
            ZoneInfo(o.partner_tz)
        except Exception:
            raise HTTPException(400, "invalid partner birth date/time/timezone")

    focus = [f for f in o.focus_areas
             if f in ("personality", "love", "career", "growth")]
    # An unrecognized coupon code shouldn't block checkout: the field is
    # optional and its text is submitted as-is even if the visitor never
    # pressed "Apply" (see the coupon UI in the frontend), so anything
    # invalid here just falls back to full price rather than erroring out
    # the whole order.
    currency = geo.pricing_currency(request)
    try:
        amount_minor = _apply_coupon(orders.PRICES[o.tier][currency], o.coupon_code)
    except ValueError:
        amount_minor = orders.PRICES[o.tier][currency]
    # Record a lead-magnet discount code on the order (not a FREE_COUPON_
    # CODES freebie) so mark_paid() can burn it once, only on confirmed
    # payment — never at order creation, since a Stripe Checkout can be
    # abandoned.
    discount_code = None
    if o.coupon_code and o.coupon_code.strip().upper() not in FREE_COUPON_CODES:
        if orders.validate_discount_code(o.coupon_code):
            discount_code = o.coupon_code.strip().upper()
    order = orders.create_order(
        o.quiz_session_id, o.email, o.name, o.tier, currency,
        o.birth_date, o.birth_time or "", o.birth_place, o.lat, o.lon,
        o.tz, focus, o.marketing_opt_in, o.gender,
        amount_minor=amount_minor, phone=o.phone,
        zodiac_insights_opt_in=o.zodiac_insights_opt_in,
        product_type="compatibility" if is_compat else "individual",
        partner_name=o.partner_name, partner_birth_date=o.partner_birth_date,
        partner_birth_time=o.partner_birth_time, partner_birth_place=o.partner_birth_place,
        partner_lat=o.partner_lat, partner_lon=o.partner_lon, partner_tz=o.partner_tz,
        partner_gender=o.partner_gender, discount_code=discount_code,
        primary_focus=o.primary_focus, language=o.language)
    session = None
    if amount_minor > 0:
        adapter = get_adapter()
        try:
            session = adapter.create_order(order["amount_minor"], order["currency"],
                                           order["tier"], order["email"],
                                           order_id=order["id"])
        except Exception:
            logger.exception("Gateway create_order failed for order %s (%s)",
                             order["id"], order["currency"])
            raise HTTPException(502, "payment gateway unavailable, please try again shortly")
        if session.checkout_url:  # hosted checkout: remember session on the order
            orders.set_payment_session(order["id"], session.session_id)
    return {"order_id": order["id"], "payment_session_id": session.session_id if session else None,
            "amount_minor": order["amount_minor"],
            "currency": order["currency"], "checkout_url": session.checkout_url if session else None}


@app.post("/api/leads")
def create_lead(lead_in: LeadIn, request: Request, background: BackgroundTasks):
    """Free 2-page preview lead magnet: no payment. Computes a real (short)
    chart in the background, emails it with a 48h/40%-off discount code
    toward a full report. Same birth-data validation as /api/orders, for
    the same reason — never hand a chart the engine can't calculate."""
    try:
        dt.datetime.strptime(
            lead_in.birth_date + " " + (lead_in.birth_time or "12:00"),
            "%Y-%m-%d %H:%M")
        from zoneinfo import ZoneInfo
        ZoneInfo(lead_in.tz)
    except Exception:
        raise HTTPException(400, "invalid birth date/time/timezone")

    currency = geo.pricing_currency(request)
    lead = orders.create_lead(
        lead_in.email, lead_in.name, lead_in.birth_date,
        lead_in.birth_time or "", lead_in.birth_place, lead_in.lat,
        lead_in.lon, lead_in.tz, currency, gender=lead_in.gender,
        primary_focus=lead_in.primary_focus,
        quiz_session_id=lead_in.quiz_session_id)
    background.add_task(_fulfil_lead, lead["id"])
    return {"ok": True, "lead_id": lead["id"]}


def _fulfil_lead(lead_id: str):
    """Generate the 2-page teaser PDF + email it. Mirrors _fulfil() below,
    just for the free lead-magnet flow (no payment, no orders row)."""
    lead = orders.get_lead(lead_id)
    if not lead:
        return
    pdf_path = os.path.join(REPORT_DIR, f"{lead_id}.pdf")
    try:
        os.makedirs(REPORT_DIR, exist_ok=True)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        time_known = bool(lead["birth_time"])
        birth = dt.datetime.strptime(
            lead["birth_date"] + " " + (lead["birth_time"] or "12:00"),
            "%Y-%m-%d %H:%M")
        generate_lead_teaser(
            lead["name"], birth, lead["tz"], lead["birth_place"],
            lead["lat"], lead["lon"], pdf_path, time_known=time_known,
            gender=lead.get("gender", "unspecified"),
            currency=lead["currency"], discount_code=lead["discount_code"],
            discount_pct=lead["discount_pct"], expires_at=lead["expires_at"],
            primary_focus=lead.get("primary_focus"))
        if not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) == 0:
            raise RuntimeError("teaser generator did not create a PDF")
    except Exception as exc:
        logger.exception("Lead teaser generation failed for lead %s", lead_id)
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            orders.mark_lead_fulfilment_failed(lead_id, str(exc))
        except Exception:
            logger.exception("Could not record fulfilment failure for lead %s", lead_id)
        return

    try:
        token = orders.mark_lead_delivered(lead_id, pdf_path)
    except Exception:
        logger.exception("Could not mark lead teaser delivered for %s", lead_id)
        return

    try:
        send_lead_teaser_email(lead["email"], lead["name"], token,
                               lead["discount_code"], lead["discount_pct"],
                               lead["expires_at"],
                               primary_focus=lead.get("primary_focus"))
    except Exception as exc:
        logger.exception("Lead teaser email delivery failed for %s", lead_id)
        with orders._conn() as connection:
            connection.execute("UPDATE leads SET email_error=? WHERE id=?",
                               (str(exc), lead_id))


def _fulfil(order_id: str):
    """Generate PDF + email download link. Runs in background post-payment."""
    order = orders.get_order(order_id)
    if not order or order["status"] != "paid":
        return
    pdf_path = os.path.join(REPORT_DIR, f"{order_id}.pdf")
    try:
        os.makedirs(REPORT_DIR, exist_ok=True)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if order.get("product_type") == "compatibility":
            generate_compatibility_report(order, pdf_path)
        else:
            time_known = bool(order["birth_time"])
            birth = dt.datetime.strptime(
                order["birth_date"] + " " + (order["birth_time"] or "12:00"),
                "%Y-%m-%d %H:%M")
            generate_report(
                order["name"], birth, order["tz"], order["birth_place"],
                order["lat"], order["lon"], order["tier"],
                [f for f in order["focus_areas"].split(",") if f], pdf_path,
                time_known=time_known, gender=order.get("gender", "unspecified"),
                primary_focus=order.get("primary_focus"),
                language=order.get("language") or "en")
        if not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) == 0:
            raise RuntimeError("report generator did not create a PDF")
    except Exception as exc:
        logger.exception("Report generation failed for paid order %s", order_id)
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            orders.mark_fulfilment_failed(order_id, str(exc))
        except Exception:
            logger.exception("Could not record fulfilment failure for order %s", order_id)
        return

    try:
        token = orders.mark_delivered(order_id, pdf_path)
    except Exception:
        logger.exception("Could not mark generated report delivered for order %s", order_id)
        return

    try:
        tier_name = (COMPAT_TIER_NAMES[order["tier"]]
                    if order.get("product_type") == "compatibility"
                    else TIER_NAMES[order["tier"]])
        send_report_email(order["email"], order["name"], tier_name, token,
                          language=order.get("language") or "en")
    except Exception as exc:
        logger.exception("Report email delivery failed for order %s", order_id)
        with orders._conn() as connection:
            connection.execute("UPDATE orders SET email_error=? WHERE id=?",
                               (str(exc), order_id))


@app.post("/api/pay")
def pay(p: PayIn, background: BackgroundTasks):
    order = orders.get_order(p.order_id)
    if not order:
        raise HTTPException(404, "order not found")
    if order["status"] != "pending":
        raise HTTPException(409, f"order is {order['status']}")
    if order["amount_minor"] <= 0:
        orders.mark_paid(p.order_id, "free", "free")
        background.add_task(_fulfil, p.order_id)
        return {"ok": True, "order_id": p.order_id, "status": "paid",
                "message": "Your free report is being generated and will arrive by email within a few minutes."}
    adapter = get_adapter()
    try:
        session = adapter.create_order(order["amount_minor"], order["currency"],
                                       order["tier"], order["email"],
                                       order_id=order["id"])
        result = adapter.charge(session.session_id, p.payment_details)
    except Exception:
        logger.exception("Gateway call failed for order %s (%s)",
                         p.order_id, order["currency"])
        raise HTTPException(502, "payment gateway unavailable, please try again shortly")
    if not result.success:
        orders.transition(p.order_id, "failed")
        raise HTTPException(402, result.error or "payment failed")
    orders.mark_paid(p.order_id, session.session_id, result.charge_id)
    background.add_task(_fulfil, p.order_id)
    return {"ok": True, "order_id": p.order_id, "status": "paid",
            "message": "Payment received. Your report is being generated "
                       "and will arrive by email within a few minutes."}


def _handle_webhook_event(event, background: BackgroundTasks):
    if not event.valid:
        raise HTTPException(400, "invalid webhook")
    if event.event_type == "payment.paid":
        order_id = (event.raw or {}).get("order_id")
        if not order_id and event.order_session_id:
            o = orders.get_order_by_session(event.order_session_id)
            order_id = o["id"] if o else None
        if order_id:
            order = orders.get_order(order_id)
            if order and order["status"] == "pending":
                orders.mark_paid(order_id, event.order_session_id or "",
                                 event.order_session_id or "")
                background.add_task(_fulfil, order_id)
    elif event.event_type == "payment.failed":
        order_id = (event.raw or {}).get("order_id")
        if order_id:
            order = orders.get_order(order_id)
            if order and order["status"] == "pending":
                orders.transition(order_id, "failed")
    return {"received": True, "type": event.event_type}


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, background: BackgroundTasks):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    event = get_adapter().verify_webhook(payload, signature)
    return _handle_webhook_event(event, background)


@app.get("/api/orders/{order_id}/status")
def order_status(order_id: str):
    order = orders.get_order(order_id)
    if not order:
        raise HTTPException(404, "order not found")
    out = {"order_id": order_id, "status": order["status"]}
    if order["status"] == "delivered":
        out["download_url"] = f"/download/{order['download_token']}"
        out["tier"] = order["tier"]
        # for the analytics purchase event on the success screen
        out["amount_minor"] = order["amount_minor"]
        out["currency"] = order["currency"]
    if order["status"] == "fulfilment_failed":
        out["retryable"] = True
        out["error"] = order.get("fulfilment_error") or "report generation failed"
    return out


@app.post("/api/orders/{order_id}/retry")
def retry_order(order_id: str, background: BackgroundTasks):
    order = orders.get_order(order_id)
    if not order:
        raise HTTPException(404, "order not found")
    if order["status"] != "fulfilment_failed":
        raise HTTPException(409, f"order is {order['status']}")
    orders.retry_fulfilment(order_id)
    background.add_task(_fulfil, order_id)
    return {"ok": True, "order_id": order_id, "status": "paid"}


@app.get("/download/{token}")
def download(token: str):
    order = orders.get_order_by_token(token)
    if not order or not order["pdf_path"] or not os.path.exists(order["pdf_path"]):
        raise HTTPException(404, "report not found")
    fname = f"Arvelos_{order['tier'].title()}_Report.pdf"
    return FileResponse(order["pdf_path"], media_type="application/pdf",
                        filename=fname)


@app.get("/download/lead/{token}")
def download_lead(token: str):
    lead = orders.get_lead_by_token(token)
    if not lead or not lead["pdf_path"] or not os.path.exists(lead["pdf_path"]):
        raise HTTPException(404, "preview not found")
    return FileResponse(lead["pdf_path"], media_type="application/pdf",
                        filename="Arvelos_Free_Preview.pdf")


# Optional: serve the static frontend from this same process (test/simple
# deploys without Nginx). Mounted LAST so all /api, /download, /webhooks
# routes above take precedence. Enabled by setting ARVELOS_FRONTEND.
_FRONTEND = os.environ.get("ARVELOS_FRONTEND")
if _FRONTEND and os.path.isdir(_FRONTEND):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True),
              name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
