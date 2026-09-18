"""
GDPR export/delete — admin-only. There is no admin auth system in this
app yet, so this is deliberately a CLI run directly on the server (over
SSH), not an HTTP endpoint — that avoids adding a new unauthenticated
surface that could export or delete anyone's data.

Usage (from astro-engine/backend/, with the same env as the running
container — ARVELOS_DATA_DIR / ARVELOS_DB set):

    python -m gdpr_tools export person@example.com
    python -m gdpr_tools delete person@example.com
    python -m gdpr_tools optout person@example.com [marketing|zodiac|all]

export prints a JSON document with everything tied to that email: the
`customers` row plus every matching `orders` row (this IS their personal
data, in full, including birth details — covers the GDPR right of
access).

delete scrubs personal fields from `orders` (name, phone, birth details,
consent flags, download token) but keeps the non-identifying accounting
trail — id, created_at, tier, currency, amount_minor, status,
payment_session_id/charge_id — since that's a legitimate business record
once it no longer identifies a person. It also removes the `customers`
row entirely, deletes any generated report PDFs, and deletes any queued
outbox emails for that address. Covers the GDPR right to erasure.

optout is lighter than delete: it withdraws consent (flips one or both
opt-in flags to false) without touching the customer record or order
history — for "please stop emailing me, but I still want my past order
on file for support" requests, which is a separate right (withdrawal of
consent) from erasure. `scope` defaults to "all" if omitted. Until real
outbound email exists, this is the only way consent gets withdrawn —
there's no unsubscribe link yet; support runs this by hand on request.
"""
from __future__ import annotations

import glob
import json
import os
import sys

import orders as orders_module

_DATA_DIR = os.environ.get("ARVELOS_DATA_DIR", os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data")))
REPORT_DIR = os.environ.get("ARVELOS_REPORT_DIR", os.path.join(_DATA_DIR, "reports"))
OUTBOX = os.environ.get("ARVELOS_OUTBOX_DIR", os.path.join(_DATA_DIR, "outbox"))

_SCRUB_ORDER_FIELDS = {
    "name": "[deleted]", "email": "[deleted]", "phone": None, "birth_date": "[deleted]",
    "birth_time": "", "gender": "unspecified", "birth_place": "[deleted]",
    "lat": 0.0, "lon": 0.0, "tz": "UTC", "focus_areas": "",
    "marketing_opt_in": 0, "zodiac_insights_opt_in": 0,
    "download_token": None, "pdf_path": None,
}


def _matching_orders(c, email: str) -> list[dict]:
    rows = c.execute("SELECT * FROM orders WHERE lower(email)=lower(?)",
                     (email,)).fetchall()
    return [dict(r) for r in rows]


def export(email: str) -> dict:
    with orders_module._conn() as c:
        customer = c.execute("SELECT * FROM customers WHERE lower(email)=lower(?)",
                             (email,)).fetchone()
        order_rows = _matching_orders(c, email)
    files = []
    for o in order_rows:
        pdf = os.path.join(REPORT_DIR, f"{o['id']}.pdf")
        if os.path.exists(pdf):
            files.append(pdf)
    files += glob.glob(os.path.join(OUTBOX, f"*_{email}.eml"))
    return {
        "customer": dict(customer) if customer else None,
        "orders": order_rows,
        "files": files,
    }


def delete(email: str) -> dict:
    with orders_module._conn() as c:
        order_rows = _matching_orders(c, email)
        for o in order_rows:
            sets = ", ".join(f"{k}=?" for k in _SCRUB_ORDER_FIELDS)
            c.execute(f"UPDATE orders SET {sets} WHERE id=?",
                     (*_SCRUB_ORDER_FIELDS.values(), o["id"]))
        deleted_customer = c.execute(
            "DELETE FROM customers WHERE lower(email)=lower(?)",
            (email,)).rowcount

    removed_files = []
    for o in order_rows:
        pdf = os.path.join(REPORT_DIR, f"{o['id']}.pdf")
        if os.path.exists(pdf):
            os.remove(pdf)
            removed_files.append(pdf)
    for path in glob.glob(os.path.join(OUTBOX, f"*_{email}.eml")):
        os.remove(path)
        removed_files.append(path)

    return {
        "customer_row_deleted": bool(deleted_customer),
        "orders_scrubbed": [o["id"] for o in order_rows],
        "files_removed": removed_files,
    }


def optout(email: str, scope: str = "all") -> dict:
    if scope not in ("marketing", "zodiac", "all"):
        raise ValueError('scope must be "marketing", "zodiac", or "all"')
    now = orders_module._now()
    sets, vals = [], []
    if scope in ("marketing", "all"):
        sets += ["marketing_opt_in=0", "marketing_opt_in_at=?"]
        vals.append(now)
    if scope in ("zodiac", "all"):
        sets += ["zodiac_insights_opt_in=0", "zodiac_insights_opt_in_at=?"]
        vals.append(now)
    vals.append(email)
    with orders_module._conn() as c:
        updated = c.execute(
            f"UPDATE customers SET {', '.join(sets)} WHERE lower(email)=lower(?)",
            vals).rowcount
    return {"customer_found": bool(updated), "scope": scope, "withdrawn_at": now}


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("export", "delete", "optout"):
        print(__doc__)
        sys.exit(1)
    action, email = sys.argv[1], sys.argv[2]
    orders_module.init_db()
    if action == "export":
        result = export(email)
    elif action == "delete":
        result = delete(email)
    else:
        scope = sys.argv[3] if len(sys.argv) > 3 else "all"
        result = optout(email, scope)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
