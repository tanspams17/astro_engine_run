"""
Arvelos FastAPI backend.
Endpoints: quiz session (UTM capture), order creation, mock checkout,
webhook, report generation + delivery, download.
"""
from __future__ import annotations

import datetime as dt
import os

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

try:
    from . import orders
    from .delivery import send_report_email
    from .report_generator import generate_report, TIER_NAMES
    from .payment.mock_adapter import MockAdapter
except ImportError:
    import orders
    from delivery import send_report_email
    from report_generator import generate_report, TIER_NAMES
    from payment.mock_adapter import MockAdapter

app = FastAPI(title="Arvelos API", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

PROVIDER = os.environ.get("PAYMENT_PROVIDER", "mock")
if PROVIDER == "mollie":
    from payment.mollie_adapter import MollieAdapter
    payment = MollieAdapter()
else:
    payment = MockAdapter()
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "reports")

FREE_COUPON_CODE = "ASTRO100"


def _apply_coupon(amount_minor: int, coupon_code: str | None) -> int:
    if not coupon_code:
        return amount_minor
    code = coupon_code.strip().upper()
    if code == FREE_COUPON_CODE:
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
    focus_areas: list[str] = []
    marketing_opt_in: bool = False   # MUST default False (GDPR/PECR)


class PayIn(BaseModel):
    order_id: str
    payment_details: dict = {}


# ------------------------------------------------------------ endpoints


@app.get("/api/health")
def health():
    return {"ok": True, "service": "arvelos"}


@app.get("/api/config")
def config():
    return {"payment_provider": PROVIDER}


@app.get("/api/prices")
def prices():
    return orders.PRICES


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
        amount_minor=amount_minor)
    session = None
    if amount_minor > 0:
        kwargs = {}
        if PROVIDER == "mollie":
            kwargs["order_id"] = order["id"]
        session = payment.create_order(order["amount_minor"], order["currency"],
                                       order["tier"], order["email"], **kwargs)
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
    os.makedirs(REPORT_DIR, exist_ok=True)
    time_known = bool(order["birth_time"])
    birth = dt.datetime.strptime(
        order["birth_date"] + " " + (order["birth_time"] or "12:00"),
        "%Y-%m-%d %H:%M")
    pdf_path = os.path.join(REPORT_DIR, f"{order_id}.pdf")
    generate_report(
        order["name"], birth, order["tz"], order["birth_place"],
        order["lat"], order["lon"], order["tier"],
        [f for f in order["focus_areas"].split(",") if f], pdf_path,
        time_known=time_known, gender=order.get("gender", "unspecified"))
    token = orders.mark_delivered(order_id, pdf_path)
    send_report_email(order["email"], order["name"],
                      TIER_NAMES[order["tier"]], token)


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
    session = payment.create_order(order["amount_minor"], order["currency"],
                                   order["tier"], order["email"])
    result = payment.charge(session.session_id, p.payment_details)
    if not result.success:
        orders.transition(p.order_id, "failed")
        raise HTTPException(402, result.error or "payment failed")
    orders.mark_paid(p.order_id, session.session_id, result.charge_id)
    background.add_task(_fulfil, p.order_id)
    return {"ok": True, "order_id": p.order_id, "status": "paid",
            "message": "Payment received — your report is being generated "
                       "and will arrive by email within a few minutes."}


@app.post("/webhooks/payment")
async def payment_webhook(request: Request, background: BackgroundTasks):
    payload = await request.body()
    signature = request.headers.get("X-Signature", "")
    event = payment.verify_webhook(payload, signature)
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


@app.get("/api/orders/{order_id}/status")
def order_status(order_id: str):
    order = orders.get_order(order_id)
    if not order:
        raise HTTPException(404, "order not found")
    out = {"order_id": order_id, "status": order["status"]}
    if order["status"] == "delivered":
        out["download_url"] = f"/download/{order['download_token']}"
    return out


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
