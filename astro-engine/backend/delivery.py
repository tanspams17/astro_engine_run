"""
Email delivery. PDF is sent as a download LINK (not attachment) for
deliverability, per spec §4.

Provider priority: RESEND_API_KEY (HTTP API, no SMTP — see below) ->
SMTP_HOST (plain SMTP, any provider) -> outbox (dev mode, writes to
<data>/outbox/ instead of sending). <data> is ARVELOS_DATA_DIR when set
(so the outbox lands on the persistent volume, not an ephemeral
container path), otherwise the repo-local data/ directory.

Env (Resend):
  RESEND_API_KEY, RESEND_FROM (default: reports@arvelos.cloud —
  must be on a domain verified in the Resend dashboard; sending from an
  unverified domain either fails outright or, on the default
  onboarding@resend.dev sender, only delivers to your own Resend
  signup address — useless for real customers).

Env (legacy SMTP, only used if RESEND_API_KEY is unset):
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
"""
from __future__ import annotations

import json
import os
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

BASE_URL = os.environ.get("BASE_URL", "https://arvelos.cloud")
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@arvelos.cloud")
_DATA_DIR = os.environ.get("ARVELOS_DATA_DIR", os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data")))
OUTBOX = os.environ.get("ARVELOS_OUTBOX_DIR", os.path.join(_DATA_DIR, "outbox"))

RESEND_API = "https://api.resend.com/emails"


def _email_text(name: str, tier_name: str, token: str) -> str:
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


def _email_html(name: str, tier_name: str, token: str) -> str:
    link = f"{BASE_URL}/download/{token}"
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:32px 20px;background:#191735;
font-family:Georgia,serif;color:#e9e4f5;">
<div style="max-width:480px;margin:0 auto;">
<p style="color:#d4920a;font-size:13px;letter-spacing:.08em;
text-transform:uppercase;margin:0 0 20px;">Arvelos</p>
<p style="font-size:16px;">Hi {name},</p>
<p style="font-size:16px;">Your Arvelos <strong>{tier_name}</strong> is ready.</p>
<p style="margin:28px 0;">
<a href="{link}" style="background:#d4920a;color:#191735;text-decoration:none;
padding:14px 28px;border-radius:8px;font-weight:bold;display:inline-block;">
Download your report (PDF)</a></p>
<p style="font-size:13px;color:#a9a3c9;">This link is private to you — keep it safe.</p>
<hr style="border:none;border-top:1px solid #35325a;margin:28px 0;">
<p style="font-size:13px;color:#a9a3c9;">
The report was calculated individually from your exact birth details.
This was a one-time payment — no subscription, no renewals, nothing to cancel.<br><br>
If anything looks wrong (a typo in your birth details, a broken link),
just reply to this email and we'll fix it: {SUPPORT_EMAIL}</p>
<p style="font-size:13px;color:#a9a3c9;">Warmly,<br>Arvelos · {BASE_URL}</p>
</div></body></html>"""


def _send_via_resend(to_email: str, subject: str, html: str, text: str):
    api_key = os.environ["RESEND_API_KEY"]
    sender = os.environ.get("RESEND_FROM", f"Arvelos <reports@arvelos.cloud>")
    payload = json.dumps({
        "from": sender, "to": [to_email], "subject": subject,
        "html": html, "text": text,
    }).encode()
    req = urllib.request.Request(
        RESEND_API, data=payload, method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json",
                 # Cloudflare (in front of api.resend.com) blocks
                 # urllib's default User-Agent as a bot signature
                 # (error code 1010) — a real UA is required.
                 "User-Agent": "Arvelos/1.0 (+https://astro.arvelos.cloud)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            message = json.loads(body).get("message", body.decode(errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            message = body.decode(errors="replace") or str(e)
        raise RuntimeError(message) from e


def _send_via_smtp(to_email: str, subject: str, text: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("SMTP_FROM", f"Arvelos <{SUPPORT_EMAIL}>")
    msg["To"] = to_email
    msg.set_content(text)

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port) as s:
        s.starttls()
        user = os.environ.get("SMTP_USER")
        if user:
            s.login(user, os.environ.get("SMTP_PASS", ""))
        s.send_message(msg)


def _write_to_outbox(to_email: str, subject: str, text: str, token: str):
    os.makedirs(OUTBOX, exist_ok=True)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"Arvelos <{SUPPORT_EMAIL}>"
    msg["To"] = to_email
    msg.set_content(text)
    path = os.path.join(OUTBOX, f"{token[:12]}_{to_email}.eml")
    with open(path, "w") as f:
        f.write(str(msg))


def send_report_email(to_email: str, name: str, tier_name: str,
                      token: str) -> bool:
    subject = f"Your Arvelos {tier_name} is ready"
    text = _email_text(name, tier_name, token)

    if os.environ.get("RESEND_API_KEY"):
        _send_via_resend(to_email, subject, _email_html(name, tier_name, token), text)
    elif os.environ.get("SMTP_HOST"):
        _send_via_smtp(to_email, subject, text)
    else:  # dev mode: write to outbox instead of sending
        _write_to_outbox(to_email, subject, text, token)
    return True
