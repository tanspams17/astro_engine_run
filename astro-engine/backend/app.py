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
from pydantic import BaseModel, EmailStr, Field

try:
    from . import orders, geo
    from .delivery import send_report_email
    from .report_generator import generate_report, TIER_NAMES
    from .payment.mock_adapter import MockAdapter
except ImportError:
    import orders
    import geo
    from delivery import send_report_email
    from report_generator import generate_report, TIER_NAMES
    from payment.mock_adapter import MockAdapter

app = FastAPI(title="Arvelos API", docs_url=None, redoc_url=None)
_local_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
_data_dir = os.environ.get("ARVELOS_DATA_DIR", _local_data_dir)
_allowed_origins = [origin.strip() for origin in os.environ.get(
    "ARVELOS_ALLOWED_ORIGINS", os.environ.get("BASE_URL", "")
).split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_allowed_origins,
                   allow_methods=["GET", "POST"],
                   allow_headers=["*"])


# ------------------------------------------------------------ payment gateway
#
# Gateway is chosen per order by currency, not globally: INR -> Razorpay
# (built for India), everything else -> Stripe. Either falls back to the
# mock adapter automatically if its keys aren't configured, so the site
# stays fully functional (dummy payment, real report) before go-live.
# PAYMENT_PROVIDER=mock forces mock for every currency regardless of keys
# (useful for staging).
_FORCE_MOCK = os.environ.get("PAYMENT_PROVIDER", "").strip().lower() == "mock"
_mock_adapter = MockAdapter()
_adapter_cache: dict[str, object] = {}


def _provider_name(currency: str) -> str:
    if _FORCE_MOCK:
        return "mock"
    if currency == "INR":
        return ("razorpay" if os.environ.get("RAZORPAY_KEY_ID")
                and os.environ.get("RAZORPAY_KEY_SECRET") else "mock")
    return "stripe" if os.environ.get("STRIPE_API_KEY") else "mock"


def get_adapter(currency: str):
    name = _provider_name(currency)
    if name == "mock":
        return _mock_adapter
    if name not in _adapter_cache:
        if name == "razorpay":
            from payment.razorpay_adapter import RazorpayAdapter
            _adapter_cache[name] = RazorpayAdapter()
        elif name == "stripe":
            from payment.stripe_adapter import StripeAdapter
            _adapter_cache[name] = StripeAdapter()
    return _adapter_cache[name]


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
    raise ValueError("invalid coupon code")


orders.init_db()


# ------------------------------------------------------------ models


class QuizStart(BaseModel):
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None


class OrderIn(BaseModel):
    quiz_session_id: str | None = None
    email: EmailStr
    name: str = Field(min_length=1, max_length=80)
    phone: str | None = Field(default=None, max_length=32)  # optional, support reference only
    tier: str = Field(pattern="^(western|vedic|mixed)$")
    currency: str = Field(pattern="^(USD|INR)$")
    coupon_code: str | None = None
    birth_date: str            # YYYY-MM-DD
    birth_time: str | None = None   # HH:MM, or None if unknown
    gender: str = Field(default="unspecified",
                        pattern="^(male|female|unspecified)$")
    birth_place: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    tz: str                    # IANA name, e.g. Asia/Kolkata
    focus_areas: list[str] = Field(default_factory=list)
    marketing_opt_in: bool = False   # MUST default False (GDPR/PECR)
    zodiac_insights_opt_in: bool = False   # separate consent, MUST default False


class PayIn(BaseModel):
    order_id: str
    payment_details: dict = Field(default_factory=dict)


class CouponCheckIn(BaseModel):
    tier: str = Field(pattern="^(western|vedic|mixed)$")
    currency: str = Field(pattern="^(USD|INR)$")
    coupon_code: str = Field(min_length=1)


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
    providers = {cur: _provider_name(cur) for cur in ("USD", "INR")}
    return {"providers": providers,
            # legacy field some older clients may still read
            "payment_provider": providers["USD"]}


@app.get("/api/geo")
def geo_lookup(request: Request):
    country = geo.country_for_ip(geo.client_ip(request))
    return {"country": country, "currency": "INR" if country == "IN" else "USD"}


@app.get("/api/prices")
def prices():
    return orders.PRICES


@app.post("/api/coupon/check")
def coupon_check(c: CouponCheckIn):
    """Read-only — lets the checkout form validate a code and preview the
    resulting price before the customer commits to an order."""
    base = orders.PRICES[c.tier][c.currency]
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
def create_order(o: OrderIn):
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
    focus = [f for f in o.focus_areas
             if f in ("personality", "love", "career", "growth")]
    try:
        amount_minor = _apply_coupon(orders.PRICES[o.tier][o.currency], o.coupon_code)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    order = orders.create_order(
        o.quiz_session_id, o.email, o.name, o.tier, o.currency,
        o.birth_date, o.birth_time or "", o.birth_place, o.lat, o.lon,
        o.tz, focus, o.marketing_opt_in, o.gender,
        amount_minor=amount_minor, phone=o.phone,
        zodiac_insights_opt_in=o.zodiac_insights_opt_in)
    session = None
    if amount_minor > 0:
        adapter = get_adapter(order["currency"])
        try:
            session = adapter.create_order(order["amount_minor"], order["currency"],
                                           order["tier"], order["email"],
                                           order_id=order["id"])
        except Exception:
            logger.exception("Gateway create_order failed for order %s (%s)",
                             order["id"], order["currency"])
            raise HTTPException(502, "payment gateway unavailable — please try again shortly")
        if session.checkout_url:  # hosted checkout: remember session on the order
            orders.set_payment_session(order["id"], session.session_id)
    return {"order_id": order["id"], "payment_session_id": session.session_id if session else None,
            "amount_minor": order["amount_minor"],
            "currency": order["currency"], "checkout_url": session.checkout_url if session else None}


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
        time_known = bool(order["birth_time"])
        birth = dt.datetime.strptime(
            order["birth_date"] + " " + (order["birth_time"] or "12:00"),
            "%Y-%m-%d %H:%M")
        generate_report(
            order["name"], birth, order["tz"], order["birth_place"],
            order["lat"], order["lon"], order["tier"],
            [f for f in order["focus_areas"].split(",") if f], pdf_path,
            time_known=time_known, gender=order.get("gender", "unspecified"))
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
        send_report_email(order["email"], order["name"],
                          TIER_NAMES[order["tier"]], token)
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
    adapter = get_adapter(order["currency"])
    try:
        session = adapter.create_order(order["amount_minor"], order["currency"],
                                       order["tier"], order["email"],
                                       order_id=order["id"])
        result = adapter.charge(session.session_id, p.payment_details)
    except Exception:
        logger.exception("Gateway call failed for order %s (%s)",
                         p.order_id, order["currency"])
        raise HTTPException(502, "payment gateway unavailable — please try again shortly")
    if not result.success:
        orders.transition(p.order_id, "failed")
        raise HTTPException(402, result.error or "payment failed")
    orders.mark_paid(p.order_id, session.session_id, result.charge_id)
    background.add_task(_fulfil, p.order_id)
    return {"ok": True, "order_id": p.order_id, "status": "paid",
            "message": "Payment received — your report is being generated "
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
    event = get_adapter("USD").verify_webhook(payload, signature)
    return _handle_webhook_event(event, background)


@app.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, background: BackgroundTasks):
    payload = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")
    event = get_adapter("INR").verify_webhook(payload, signature)
    return _handle_webhook_event(event, background)


@app.get("/api/orders/{order_id}/status")
def order_status(order_id: str):
    order = orders.get_order(order_id)
    if not order:
        raise HTTPException(404, "order not found")
    out = {"order_id": order_id, "status": order["status"]}
    if order["status"] == "delivered":
        out["download_url"] = f"/download/{order['download_token']}"
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
