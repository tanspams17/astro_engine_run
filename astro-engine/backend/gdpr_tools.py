"""
GDPR export/delete/optout — admin-only. There is no admin auth system in
this app yet, so this is deliberately a CLI run directly on the server
(over SSH), not an HTTP endpoint — that avoids adding a new
unauthenticated surface that could export or delete anyone's data.

Nothing destructive happens automatically. `export` is read-only, so it
runs immediately. `delete` and `optout` are two-step by design: logging
a request never touches customer/order data — only `approve` does that,
and only once a human has looked at the pending list and explicitly
decided to. Every request, and what was ultimately done about it, is
kept forever in `gdpr_requests` — that table IS the audit trail.

Usage (from astro-engine/backend/, with the same env as the running
container — ARVELOS_DATA_DIR / ARVELOS_DB set):

    python -m gdpr_tools export person@example.com

    python -m gdpr_tools request delete person@example.com [note...]
    python -m gdpr_tools request optout person@example.com marketing|zodiac|all [note...]
    python -m gdpr_tools list [pending|approved|rejected|all]     # default: pending
    python -m gdpr_tools approve <request_id> [approved_by]
    python -m gdpr_tools reject <request_id> [reason...]

export prints a JSON document with everything tied to that email: the
`customers` row plus every matching `orders` row (this IS their personal
data, in full, including birth details — covers the GDPR right of
access).

approve on a 'delete' request scrubs personal fields from `orders`
(name, email, phone, birth details, consent flags, download token) but
keeps the non-identifying accounting trail — id, created_at, tier,
currency, amount_minor, status, payment_session_id/charge_id — since
that's a legitimate business record once it no longer identifies a
person. It also removes the `customers` row entirely, deletes any
generated report PDFs, and deletes any queued outbox emails for that
address. Covers the GDPR right to erasure.

approve on an 'optout' request is lighter than delete: it withdraws
consent (flips one or both opt-in flags to false) without touching the
customer record or order history — for "stop emailing me, but keep my
order on file for support" requests, which is a separate right
(withdrawal of consent) from erasure.
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


# ------------------------------------------------------------ read-only


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


# ------------------------------------------------------- request / review


def create_request(email: str, action: str, scope: str | None = None,
                   note: str | None = None) -> int:
    if action not in ("delete", "optout"):
        raise ValueError('action must be "delete" or "optout"')
    if action == "optout" and scope not in ("marketing", "zodiac", "all"):
        raise ValueError('scope must be "marketing", "zodiac", or "all"')
    with orders_module._conn() as c:
        cur = c.execute(
            "INSERT INTO gdpr_requests (email, action, scope, note,"
            " requested_at, status) VALUES (?,?,?,?,?,'pending')",
            (email, action, scope, note, orders_module._now()))
        return cur.lastrowid


def list_requests(status: str = "pending") -> list[dict]:
    with orders_module._conn() as c:
        if status == "all":
            rows = c.execute("SELECT * FROM gdpr_requests ORDER BY id DESC").fetchall()
        else:
            rows = c.execute("SELECT * FROM gdpr_requests WHERE status=?"
                             " ORDER BY id DESC", (status,)).fetchall()
    return [dict(r) for r in rows]


def approve(request_id: int, approved_by: str | None = None) -> dict:
    with orders_module._conn() as c:
        req = c.execute("SELECT * FROM gdpr_requests WHERE id=?",
                        (request_id,)).fetchone()
    if not req:
        raise ValueError(f"no request with id {request_id}")
    if req["status"] != "pending":
        raise ValueError(f"request {request_id} is already {req['status']}")

    if req["action"] == "delete":
        result = _execute_delete(req["email"])
    else:
        result = _execute_optout(req["email"], req["scope"] or "all")

    with orders_module._conn() as c:
        c.execute(
            "UPDATE gdpr_requests SET status='approved', decided_at=?,"
            " decided_by=?, result=? WHERE id=?",
            (orders_module._now(), approved_by,
             json.dumps(result, default=str), request_id))
    return {"request_id": request_id, "status": "approved", "result": result}


def reject(request_id: int, reason: str | None = None) -> dict:
    with orders_module._conn() as c:
        updated = c.execute(
            "UPDATE gdpr_requests SET status='rejected', decided_at=?,"
            " decided_by=?, result=? WHERE id=? AND status='pending'",
            (orders_module._now(), None, reason, request_id)).rowcount
    if not updated:
        raise ValueError(f"no pending request with id {request_id}")
    return {"request_id": request_id, "status": "rejected", "reason": reason}


# --------------------------------------------------- actual execution
# Only ever called from approve() above — never exposed directly on the
# CLI, so delete/optout can't happen without going through a request.


def _execute_delete(email: str) -> dict:
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


def _execute_optout(email: str, scope: str) -> dict:
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


# ------------------------------------------------------------------ CLI


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    orders_module.init_db()
    action = args[0]

    if action == "export":
        result = export(args[1])
    elif action == "request":
        sub, email = args[1], args[2]
        if sub == "optout":
            scope = args[3] if len(args) > 3 else "all"
            note = " ".join(args[4:]) or None
        else:
            scope = None
            note = " ".join(args[3:]) or None
        rid = create_request(email, sub, scope, note)
        result = {"request_id": rid, "status": "pending"}
    elif action == "list":
        result = list_requests(args[1] if len(args) > 1 else "pending")
    elif action == "approve":
        result = approve(int(args[1]), args[2] if len(args) > 2 else None)
    elif action == "reject":
        result = reject(int(args[1]), " ".join(args[2:]) or None)
    else:
        print(__doc__)
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
