"""
Email delivery. PDF is sent as a download LINK (not attachment) for
deliverability, per spec §4. SMTP config via env vars — works with any
transactional provider (Postmark/SES) or plain SMTP.

Env:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, BASE_URL
If SMTP_HOST is unset, emails are written to data/outbox/ for inspection
(dev mode) instead of being sent.
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

BASE_URL = os.environ.get("BASE_URL", "https://arvelos.cloud")
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@arvelos.cloud")
OUTBOX = os.path.join(os.path.dirname(__file__), "..", "data", "outbox")


def _email_body(name: str, tier_name: str, token: str) -> str:
    link = f"{BASE_URL}/download/{token}"
    return f"""Hi {name},

Your Arvelos {tier_name} is ready.

Download it here (link is private to you — keep it safe):
{link}

A few notes:
- The report was calculated individually from your exact birth details.
- This was a one-time payment. No subscription, no renewals, nothing to cancel.
- If anything looks wrong (a typo in your birth details, a broken link),
  just reply to this email and we'll fix it: {SUPPORT_EMAIL}

Warmly,
Arvelos
{BASE_URL}
"""


def send_report_email(to_email: str, name: str, tier_name: str,
                      token: str) -> bool:
    msg = EmailMessage()
    msg["Subject"] = f"Your Arvelos {tier_name} is ready"
    msg["From"] = os.environ.get("SMTP_FROM", f"Arvelos <{SUPPORT_EMAIL}>")
    msg["To"] = to_email
    msg.set_content(_email_body(name, tier_name, token))

    host = os.environ.get("SMTP_HOST")
    if not host:  # dev mode: write to outbox
        os.makedirs(OUTBOX, exist_ok=True)
        path = os.path.join(OUTBOX, f"{token[:12]}_{to_email}.eml")
        with open(path, "w") as f:
            f.write(str(msg))
        return True

    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port) as s:
        s.starttls()
        user = os.environ.get("SMTP_USER")
        if user:
            s.login(user, os.environ.get("SMTP_PASS", ""))
        s.send_message(msg)
    return True
