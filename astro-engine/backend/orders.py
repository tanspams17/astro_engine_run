"""
Order storage + lifecycle. SQLite (WAL) — swap for Postgres when volume demands.
States: pending -> paid -> delivered ; paid -> fulfilment_failed -> paid
pending -> failed ; paid/delivered -> refunded
UTM params are captured at quiz-start (not just purchase) per spec §9.2/9.3,
so drop-off is measurable per creative.
"""
from __future__ import annotations

import datetime as dt
import os
import sqlite3
import secrets

DB_PATH = os.environ.get("ARVELOS_DB", os.path.join(
    os.path.dirname(__file__), "..", "data", "arvelos.db"))

PRICES = {  # minor units, fixed at order creation — never recomputed mid-checkout
    # Full price list set 2026-09-24 per the account owner's fixed table
    # (own currency per market, not converted from USD). Western/Vedic
    # and Zodiac/Vedic Compatibility each share one price per currency,
    # in all three currencies now — no longer just GBP/INR.
    "western": {"USD": 999, "INR": 99900, "GBP": 799},
    "vedic": {"USD": 999, "INR": 99900, "GBP": 799},
    "mixed": {"USD": 1499, "INR": 129900, "GBP": 1199},
    "zodiac_compat": {"USD": 1899, "INR": 149900, "GBP": 1499},
    "vedic_compat": {"USD": 1899, "INR": 149900, "GBP": 1499},
    "mixed_compat": {"USD": 2499, "INR": 199900, "GBP": 1999},
}

VALID_STATES = {"pending", "paid", "delivered", "fulfilment_failed", "failed", "refunded"}
_TRANSITIONS = {
    "pending": {"paid", "failed"},
    "paid": {"delivered", "fulfilment_failed", "refunded"},
    "delivered": {"refunded"},
    "fulfilment_failed": {"paid"},
    "failed": set(), "refunded": set(),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    utm_source TEXT, utm_medium TEXT, utm_campaign TEXT,
    utm_content TEXT, utm_term TEXT,
    quiz_completed_at TEXT
);
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    quiz_session_id TEXT REFERENCES quiz_sessions(id),
    created_at TEXT NOT NULL,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,                          -- optional, support reference only
    tier TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    birth_date TEXT NOT NULL,
    birth_time TEXT NOT NULL DEFAULT '',   -- '' = time unknown
    gender TEXT NOT NULL DEFAULT 'unspecified',
    birth_place TEXT NOT NULL,
    lat REAL NOT NULL, lon REAL NOT NULL, tz TEXT NOT NULL,
    focus_areas TEXT NOT NULL,           -- comma-separated
    marketing_opt_in INTEGER NOT NULL DEFAULT 0,  -- unticked by default (GDPR/PECR)
    zodiac_insights_opt_in INTEGER NOT NULL DEFAULT 0,  -- separate consent, unticked by default
    product_type TEXT NOT NULL DEFAULT 'individual',  -- 'individual' | 'compatibility'
    partner_name TEXT,
    partner_birth_date TEXT,
    partner_birth_time TEXT,
    partner_birth_place TEXT,
    partner_lat REAL,
    partner_lon REAL,
    partner_tz TEXT,
    partner_gender TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    payment_session_id TEXT, charge_id TEXT,
    download_token TEXT, pdf_path TEXT,
    delivered_at TEXT,
    fulfilment_error TEXT,
    email_error TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    kind TEXT NOT NULL,                  -- quiz_start | quiz_complete | purchase
    quiz_session_id TEXT, order_id TEXT
);
-- One row per unique customer (keyed by lowercased email), built up from
-- orders. Deliberately excludes birth details (data minimization — those
-- stay in `orders`, the only place they're actually needed). This is the
-- table community/support tooling should read from, not `orders`.
CREATE TABLE IF NOT EXISTS customers (
    email TEXT PRIMARY KEY,              -- lowercased
    name TEXT NOT NULL,
    phone TEXT,
    created_at TEXT NOT NULL,
    first_order_at TEXT NOT NULL,
    last_order_at TEXT NOT NULL,
    order_count INTEGER NOT NULL DEFAULT 0,
    marketing_opt_in INTEGER NOT NULL DEFAULT 0,
    marketing_opt_in_at TEXT,             -- when consent was given (GDPR proof)
    zodiac_insights_opt_in INTEGER NOT NULL DEFAULT 0,
    zodiac_insights_opt_in_at TEXT
);
-- GDPR delete/optout requests. Nothing in gdpr_tools.py executes
-- automatically: a request just sits here as 'pending' until a human
-- explicitly runs `approve` (or `reject`) on it. This table IS the
-- permanent audit trail of what was requested, by whom, when, and what
-- was actually done about it — kept forever, independent of whatever
-- happens to the underlying customer/order data.
CREATE TABLE IF NOT EXISTS gdpr_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    action TEXT NOT NULL,                -- 'delete' | 'optout'
    scope TEXT,                          -- optout only: 'marketing'|'zodiac'|'all'
    note TEXT,                           -- free text, e.g. how the request arrived
    requested_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected'
    decided_at TEXT,
    decided_by TEXT,
    result TEXT                          -- JSON: what approve() actually did
);
-- "Free 2-page preview" lead magnet (added 2026-09-29): captures an email
-- before any payment, in exchange for a short teaser PDF and a time-boxed,
-- single-use discount code toward a real report. Deliberately a separate
-- table from `orders`, not a fake $0 order — a lead never had a tier,
-- amount or payment lifecycle, and mixing it into `orders` would make
-- every order-stats query have to filter it back out.
CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    birth_date TEXT NOT NULL,
    birth_time TEXT NOT NULL DEFAULT '',   -- '' = time unknown
    birth_place TEXT NOT NULL,
    lat REAL NOT NULL, lon REAL NOT NULL, tz TEXT NOT NULL,
    gender TEXT NOT NULL DEFAULT 'unspecified',
    currency TEXT NOT NULL,                -- for the price shown on the teaser
    discount_code TEXT NOT NULL UNIQUE,
    discount_pct INTEGER NOT NULL DEFAULT 40,
    expires_at TEXT NOT NULL,
    redeemed_at TEXT,
    redeemed_order_id TEXT,
    download_token TEXT,
    pdf_path TEXT,
    delivered_at TEXT,
    fulfilment_error TEXT,
    email_error TEXT
);
"""


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def _add_column(c, table: str, column: str, ddl: str = "TEXT"):
    # Every uvicorn worker runs init_db() at startup, so two can race to add
    # the same column; losing that race is harmless, not a startup failure.
    if column in {row[1] for row in c.execute(f"PRAGMA table_info({table})")}:
        return
    try:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
    except sqlite3.OperationalError as e:
        if "duplicate column" not in str(e):
            raise


def init_db():
    with _conn() as c:
        c.executescript(SCHEMA)
        for column in ("fulfilment_error", "email_error", "phone",
                       "partner_name", "partner_birth_date", "partner_birth_time",
                       "partner_birth_place", "partner_tz", "partner_gender",
                       "discount_code", "primary_focus"):
            _add_column(c, "orders", column)
        _add_column(c, "orders", "zodiac_insights_opt_in", "INTEGER NOT NULL DEFAULT 0")
        _add_column(c, "orders", "product_type", "TEXT NOT NULL DEFAULT 'individual'")
        _add_column(c, "orders", "partner_lat", "REAL")
        _add_column(c, "orders", "partner_lon", "REAL")
        for column in ("primary_focus", "quiz_session_id"):
            _add_column(c, "leads", column)
        for column in ("gclid", "gbraid", "wbraid"):
            _add_column(c, "quiz_sessions", column)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


# ------------------------------------------------------------ quiz sessions


def start_quiz_session(utm: dict) -> str:
    sid = secrets.token_urlsafe(12)
    with _conn() as c:
        c.execute(
            "INSERT INTO quiz_sessions (id, created_at, utm_source, utm_medium,"
            " utm_campaign, utm_content, utm_term, gclid, gbraid, wbraid)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sid, _now(), utm.get("utm_source"), utm.get("utm_medium"),
             utm.get("utm_campaign"), utm.get("utm_content"),
             utm.get("utm_term"), utm.get("gclid"), utm.get("gbraid"),
             utm.get("wbraid")))
        c.execute("INSERT INTO events (at, kind, quiz_session_id)"
                  " VALUES (?,?,?)", (_now(), "quiz_start", sid))
    return sid


def complete_quiz(session_id: str):
    with _conn() as c:
        c.execute("UPDATE quiz_sessions SET quiz_completed_at=? WHERE id=?",
                  (_now(), session_id))
        c.execute("INSERT INTO events (at, kind, quiz_session_id)"
                  " VALUES (?,?,?)", (_now(), "quiz_complete", session_id))


# ------------------------------------------------------------ orders


def create_order(quiz_session_id: str | None, email: str, name: str,
                 tier: str, currency: str, birth_date: str, birth_time: str,
                 birth_place: str, lat: float, lon: float, tz: str,
                 focus_areas: list[str], marketing_opt_in: bool,
                 gender: str = "unspecified", amount_minor: int | None = None,
                 phone: str | None = None,
                 zodiac_insights_opt_in: bool = False,
                 product_type: str = "individual",
                 partner_name: str | None = None,
                 partner_birth_date: str | None = None,
                 partner_birth_time: str | None = None,
                 partner_birth_place: str | None = None,
                 partner_lat: float | None = None,
                 partner_lon: float | None = None,
                 partner_tz: str | None = None,
                 partner_gender: str | None = None,
                 discount_code: str | None = None,
                 primary_focus: str | None = None) -> dict:
    if tier not in PRICES:
        raise ValueError(f"unknown tier {tier}")
    if currency not in PRICES[tier]:
        raise ValueError(f"unsupported currency {currency}")
    oid = f"ord_{secrets.token_urlsafe(10)}"
    amount = amount_minor if amount_minor is not None else PRICES[tier][currency]
    if amount < 0:
        raise ValueError("invalid amount")
    with _conn() as c:
        c.execute(
            "INSERT INTO orders (id, quiz_session_id, created_at, email, name,"
            " phone, tier, currency, amount_minor, birth_date, birth_time,"
            " gender, birth_place, lat, lon, tz, focus_areas,"
            " marketing_opt_in, zodiac_insights_opt_in, product_type,"
            " partner_name, partner_birth_date, partner_birth_time,"
            " partner_birth_place, partner_lat, partner_lon, partner_tz,"
            " partner_gender, discount_code, primary_focus)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (oid, quiz_session_id, _now(), email, name, phone, tier, currency,
             amount, birth_date, birth_time, gender, birth_place, lat, lon,
             tz, ",".join(focus_areas), int(marketing_opt_in),
             int(zodiac_insights_opt_in), product_type,
             partner_name, partner_birth_date, partner_birth_time,
             partner_birth_place, partner_lat, partner_lon, partner_tz,
             partner_gender, discount_code, primary_focus))
        _upsert_customer(c, email, name, phone, marketing_opt_in,
                         zodiac_insights_opt_in)
    return get_order(oid)


def _upsert_customer(c, email: str, name: str, phone: str | None,
                     marketing_opt_in: bool, zodiac_insights_opt_in: bool):
    key = email.strip().lower()
    now = _now()
    existing = c.execute("SELECT * FROM customers WHERE email=?",
                         (key,)).fetchone()
    if existing is None:
        c.execute(
            "INSERT INTO customers (email, name, phone, created_at,"
            " first_order_at, last_order_at, order_count, marketing_opt_in,"
            " marketing_opt_in_at, zodiac_insights_opt_in,"
            " zodiac_insights_opt_in_at) VALUES (?,?,?,?,?,?,1,?,?,?,?)",
            (key, name, phone, now, now, now, int(marketing_opt_in),
             now if marketing_opt_in else None, int(zodiac_insights_opt_in),
             now if zodiac_insights_opt_in else None))
        return
    # Opt-ins only ever flip false -> true here (explicit re-tick); an
    # unticked box on a later order is not a withdrawal of prior consent.
    sets = ["name=?", "phone=?", "last_order_at=?", "order_count=order_count+1"]
    vals = [name, phone or existing["phone"], now]
    if marketing_opt_in and not existing["marketing_opt_in"]:
        sets += ["marketing_opt_in=1", "marketing_opt_in_at=?"]
        vals.append(now)
    if zodiac_insights_opt_in and not existing["zodiac_insights_opt_in"]:
        sets += ["zodiac_insights_opt_in=1", "zodiac_insights_opt_in_at=?"]
        vals.append(now)
    vals.append(key)
    c.execute(f"UPDATE customers SET {', '.join(sets)} WHERE email=?", vals)


def get_order(order_id: str) -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM orders WHERE id=?",
                        (order_id,)).fetchone()
    return dict(row) if row else None


def set_payment_session(order_id: str, session_id: str):
    with _conn() as c:
        c.execute("UPDATE orders SET payment_session_id=? WHERE id=?",
                  (session_id, order_id))


def get_order_by_session(session_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM orders WHERE payment_session_id=?",
                        (session_id,)).fetchone()
    return dict(row) if row else None


def get_order_by_token(token: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM orders WHERE download_token=?",
                        (token,)).fetchone()
    return dict(row) if row else None


def transition(order_id: str, new_status: str, **fields):
    order = get_order(order_id)
    if not order:
        raise ValueError("no such order")
    if new_status not in _TRANSITIONS.get(order["status"], set()):
        raise ValueError(
            f"illegal transition {order['status']} -> {new_status}")
    sets = ["status=?"]
    vals = [new_status]
    for k, v in fields.items():
        sets.append(f"{k}=?")
        vals.append(v)
    vals.append(order_id)
    with _conn() as c:
        c.execute(f"UPDATE orders SET {', '.join(sets)} WHERE id=?", vals)
        if new_status == "paid" and order["status"] == "pending":
            c.execute("INSERT INTO events (at, kind, order_id, quiz_session_id)"
                      " VALUES (?,?,?,?)",
                      (_now(), "purchase", order_id, order["quiz_session_id"]))


def mark_paid(order_id: str, payment_session_id: str, charge_id: str):
    transition(order_id, "paid", payment_session_id=payment_session_id,
               charge_id=charge_id)
    order = get_order(order_id)
    if order and order.get("discount_code"):
        # Burn the lead-magnet discount code only on confirmed payment, not
        # at order creation — an abandoned Stripe Checkout must not waste
        # the customer's one-time code.
        with _conn() as c:
            c.execute(
                "UPDATE leads SET redeemed_at=?, redeemed_order_id=?"
                " WHERE discount_code=? AND redeemed_at IS NULL",
                (_now(), order_id, order["discount_code"]))


def mark_delivered(order_id: str, pdf_path: str) -> str:
    token = secrets.token_urlsafe(24)
    transition(order_id, "delivered", pdf_path=pdf_path,
               download_token=token, delivered_at=_now(),
               fulfilment_error=None)
    return token


def mark_fulfilment_failed(order_id: str, error: str):
    transition(order_id, "fulfilment_failed", fulfilment_error=error)


def retry_fulfilment(order_id: str):
    transition(order_id, "paid", fulfilment_error=None, email_error=None)


# -------------------------------------------------------- lead magnet
#
# "Free 2-page preview": no payment, just birth details + email. In
# exchange, the visitor gets a short personal teaser PDF and a discount
# code good for DISCOUNT_PCT off a real report, valid for CODE_LIFETIME
# from generation. Deliberately short-lived and single-use (see mark_paid
# above) — a long-lived or shared code would just become a permanent
# price cut for anyone who found it, not a lead-nurture tool.

DISCOUNT_PCT = 40
CODE_LIFETIME = dt.timedelta(hours=48)


def _gen_discount_code() -> str:
    # Short, easy to type/read off a PDF or forward in an email; not
    # security-sensitive (worst case of a guess is one 40%-off code that
    # still requires a real order to redeem, single-use, 48h-lived).
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I confusion
    return "ARVELOS-" + "".join(secrets.choice(alphabet) for _ in range(6))


def create_lead(email: str, name: str, birth_date: str, birth_time: str,
                birth_place: str, lat: float, lon: float, tz: str,
                currency: str, gender: str = "unspecified",
                primary_focus: str | None = None,
                quiz_session_id: str | None = None) -> dict:
    lid = f"lead_{secrets.token_urlsafe(10)}"
    code = _gen_discount_code()
    expires = (dt.datetime.now(dt.timezone.utc) + CODE_LIFETIME).isoformat()
    with _conn() as c:
        c.execute(
            "INSERT INTO leads (id, created_at, email, name, birth_date,"
            " birth_time, birth_place, lat, lon, tz, gender, currency,"
            " discount_code, discount_pct, expires_at, primary_focus,"
            " quiz_session_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (lid, _now(), email, name, birth_date, birth_time, birth_place,
             lat, lon, tz, gender, currency, code, DISCOUNT_PCT, expires,
             primary_focus, quiz_session_id))
    return get_lead(lid)


def get_lead(lead_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    return dict(row) if row else None


def get_lead_by_token(token: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM leads WHERE download_token=?",
                        (token,)).fetchone()
    return dict(row) if row else None


def mark_lead_delivered(lead_id: str, pdf_path: str) -> str:
    token = secrets.token_urlsafe(24)
    with _conn() as c:
        c.execute(
            "UPDATE leads SET pdf_path=?, download_token=?, delivered_at=?,"
            " fulfilment_error=NULL WHERE id=?",
            (pdf_path, token, _now(), lead_id))
    return token


def mark_lead_fulfilment_failed(lead_id: str, error: str):
    with _conn() as c:
        c.execute("UPDATE leads SET fulfilment_error=? WHERE id=?",
                  (error, lead_id))


def validate_discount_code(code: str) -> dict | None:
    """Returns the lead row if `code` is a live, unredeemed, unexpired
    discount code, else None. Case-insensitive; the stored code is always
    upper-case (see _gen_discount_code)."""
    with _conn() as c:
        row = c.execute("SELECT * FROM leads WHERE discount_code=?",
                        (code.strip().upper(),)).fetchone()
    if not row:
        return None
    lead = dict(row)
    if lead["redeemed_at"]:
        return None
    if dt.datetime.now(dt.timezone.utc) > dt.datetime.fromisoformat(lead["expires_at"]):
        return None
    return lead
