"""
Order storage + lifecycle. SQLite (WAL) — swap for Postgres when volume demands.
States: pending -> paid -> delivered ; pending -> failed ; paid/delivered -> refunded
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
    "western": {"USD": 1900, "INR": 99900},
    "vedic": {"USD": 1900, "INR": 99900},
    "mixed": {"USD": 2900, "INR": 149900},
}

VALID_STATES = {"pending", "paid", "delivered", "failed", "refunded"}
_TRANSITIONS = {
    "pending": {"paid", "failed"},
    "paid": {"delivered", "refunded"},
    "delivered": {"refunded"},
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
    status TEXT NOT NULL DEFAULT 'pending',
    payment_session_id TEXT, charge_id TEXT,
    download_token TEXT, pdf_path TEXT,
    delivered_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    kind TEXT NOT NULL,                  -- quiz_start | quiz_complete | purchase
    quiz_session_id TEXT, order_id TEXT
);
"""


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db():
    with _conn() as c:
        c.executescript(SCHEMA)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


# ------------------------------------------------------------ quiz sessions


def start_quiz_session(utm: dict) -> str:
    sid = secrets.token_urlsafe(12)
    with _conn() as c:
        c.execute(
            "INSERT INTO quiz_sessions (id, created_at, utm_source, utm_medium,"
            " utm_campaign, utm_content, utm_term) VALUES (?,?,?,?,?,?,?)",
            (sid, _now(), utm.get("utm_source"), utm.get("utm_medium"),
             utm.get("utm_campaign"), utm.get("utm_content"),
             utm.get("utm_term")))
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
                 gender: str = "unspecified", amount_minor: int | None = None) -> dict:
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
            " tier, currency, amount_minor, birth_date, birth_time, gender,"
            " birth_place, lat, lon, tz, focus_areas, marketing_opt_in)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (oid, quiz_session_id, _now(), email, name, tier, currency,
             amount, birth_date, birth_time, gender, birth_place, lat, lon,
             tz, ",".join(focus_areas), int(marketing_opt_in)))
    return get_order(oid)


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
        if new_status == "paid":
            c.execute("INSERT INTO events (at, kind, order_id, quiz_session_id)"
                      " VALUES (?,?,?,?)",
                      (_now(), "purchase", order_id, order["quiz_session_id"]))


def mark_paid(order_id: str, payment_session_id: str, charge_id: str):
    transition(order_id, "paid", payment_session_id=payment_session_id,
               charge_id=charge_id)


def mark_delivered(order_id: str, pdf_path: str) -> str:
    token = secrets.token_urlsafe(24)
    transition(order_id, "delivered", pdf_path=pdf_path,
               download_token=token, delivered_at=_now())
    return token
