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

import html
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

Download it here (the link is private to you, so keep it safe):
{link}

A few notes:
- The report was calculated individually from your exact birth details.
- This was a one-time payment. No subscription, no renewals, nothing to cancel.
- If anything looks wrong (a typo in your birth details, a broken link),
  just reply to this email and we'll fix it: {SUPPORT_EMAIL}

Warmly,
Arvelos
Your NextGen Astral Report
"""


def _email_html(name: str, tier_name: str, token: str) -> str:
    # `name` is free-text customer input (checkout puts no charset limits on
    # it beyond length) and this HTML goes straight to a real inbox via
    # Resend — without escaping, a name like `<a href=evil>click</a>` would
    # render as a live phishing link inside an email sent from a domain
    # Arvelos' own verified sender, to whatever address the orderer typed
    # in (not necessarily their own). tier_name is always one of our own
    # fixed TIER_NAMES strings, but escaping it too costs nothing.
    safe_name = html.escape(name)
    safe_tier_name = html.escape(tier_name)
    link = f"{BASE_URL}/download/{token}"
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:32px 20px;background:#191735;
font-family:Georgia,serif;color:#e9e4f5;">
<div style="max-width:480px;margin:0 auto;">
<p style="color:#d4920a;font-size:13px;letter-spacing:.08em;
text-transform:uppercase;margin:0 0 20px;">Arvelos</p>
<p style="font-size:16px;">Hi {safe_name},</p>
<p style="font-size:16px;">Your Arvelos <strong>{safe_tier_name}</strong> is ready.</p>
<p style="margin:28px 0;">
<a href="{link}" style="background:#d4920a;color:#191735;text-decoration:none;
padding:14px 28px;border-radius:8px;font-weight:bold;display:inline-block;">
Download your report (PDF)</a></p>
<p style="font-size:13px;color:#a9a3c9;">This link is private to you, so keep it safe.</p>
<hr style="border:none;border-top:1px solid #35325a;margin:28px 0;">
<p style="font-size:13px;color:#a9a3c9;">
The report was calculated individually from your exact birth details.
This was a one-time payment. No subscription, no renewals, nothing to cancel.<br><br>
If anything looks wrong (a typo in your birth details, a broken link),
just reply to this email and we'll fix it: {SUPPORT_EMAIL}</p>
<p style="font-size:13px;color:#a9a3c9;">Warmly,<br>Arvelos<br>Your NextGen Astral Report</p>
<p style="text-align:center;margin:20px 0 0;">
<img src="{BASE_URL}/email-logo.png" alt="Arvelos" width="40" height="40"
style="width:40px;height:40px;border-radius:50%;"><br>
<span style="font-size:10.5px;color:#5d5885;">© 2026 Arvelos</span></p>
</div></body></html>"""


def _email_text_hi(name: str, token: str) -> str:
    link = f"{BASE_URL}/download/{token}"
    return f"""नमस्ते {name},

आपकी अरवेलोस कुंडली मिलान रिपोर्ट (हिन्दी) तैयार है।

इसे यहाँ से डाउनलोड करें (यह लिंक केवल आपके लिए है, कृपया इसे सुरक्षित रखें):
{link}

कुछ बातें:
- रिपोर्ट आपके दिए गए सटीक जन्म विवरण से व्यक्तिगत रूप से तैयार की गई है।
- यह एक बार का भुगतान था। कोई सदस्यता नहीं, कोई नवीनीकरण नहीं, रद्द करने के लिए कुछ नहीं।
- यदि कुछ गलत दिखे (जन्म विवरण में त्रुटि या लिंक न खुले), तो इस ईमेल का उत्तर दें और हम ठीक कर देंगे: {SUPPORT_EMAIL}

सादर,
अरवेलोस
"""


def _email_html_hi(name: str, token: str) -> str:
    safe_name = html.escape(name)
    link = f"{BASE_URL}/download/{token}"
    return f"""<!DOCTYPE html>
<html lang="hi"><body style="margin:0;padding:32px 20px;background:#191735;
font-family:Georgia,serif;color:#e9e4f5;">
<div style="max-width:480px;margin:0 auto;">
<p style="color:#d4920a;font-size:13px;letter-spacing:.08em;
text-transform:uppercase;margin:0 0 20px;">Arvelos</p>
<p style="font-size:16px;">नमस्ते {safe_name},</p>
<p style="font-size:16px;">आपकी अरवेलोस <strong>कुंडली मिलान रिपोर्ट (हिन्दी)</strong> तैयार है।</p>
<p style="margin:28px 0;">
<a href="{link}" style="background:#d4920a;color:#191735;text-decoration:none;
padding:14px 28px;border-radius:8px;font-weight:bold;display:inline-block;">
अपनी रिपोर्ट डाउनलोड करें (PDF)</a></p>
<p style="font-size:13px;color:#a9a3c9;">यह लिंक केवल आपके लिए है, कृपया इसे सुरक्षित रखें।</p>
<hr style="border:none;border-top:1px solid #35325a;margin:28px 0;">
<p style="font-size:13px;color:#a9a3c9;">
रिपोर्ट आपके सटीक जन्म विवरण से व्यक्तिगत रूप से तैयार की गई है।
यह एक बार का भुगतान था। कोई सदस्यता नहीं, कोई नवीनीकरण नहीं।<br><br>
यदि कुछ गलत दिखे, तो इस ईमेल का उत्तर दें: {SUPPORT_EMAIL}</p>
<p style="font-size:13px;color:#a9a3c9;">सादर,<br>अरवेलोस</p>
<p style="text-align:center;margin:20px 0 0;">
<img src="{BASE_URL}/email-logo.png" alt="Arvelos" width="40" height="40"
style="width:40px;height:40px;border-radius:50%;"><br>
<span style="font-size:10.5px;color:#5d5885;">© 2026 Arvelos</span></p>
</div></body></html>"""


def _format_expiry(expires_at_iso: str) -> str:
    import datetime as _dt
    when = _dt.datetime.fromisoformat(expires_at_iso)
    return when.strftime("%-I:%M %p, %-d %B %Y (UTC)")


def _claim_link(discount_code: str, primary_focus: str | None) -> str:
    focus = f"&focus={primary_focus}" if primary_focus else ""
    return f"{BASE_URL}/?coupon={discount_code}&tier=mixed{focus}#order"


def _lead_text(name: str, token: str, discount_code: str, discount_pct: int,
               expires_at: str, primary_focus: str | None = None) -> str:
    link = f"{BASE_URL}/download/lead/{token}"
    claim_link = _claim_link(discount_code, primary_focus)
    expiry = _format_expiry(expires_at)
    return f"""Hi {name},

Your free birth chart preview is ready — calculated from your real birth
details, not a template:
{link}

As a thank-you for trying it, we've reserved {discount_pct}% off your full report — it's yours,
you just need to claim it:

  CODE: {discount_code}
  Gone after {expiry} — {discount_pct}% off any report, one time only, then this price won't come back.

Claim your reserved discount here (the code fills in automatically):
{claim_link}

Warmly,
Arvelos
Your NextGen Astral Report

P.S. Your code is reserved for you specifically — it can only be used once, by whoever claims it first.
"""


def _lead_html(name: str, token: str, discount_code: str, discount_pct: int,
              expires_at: str, primary_focus: str | None = None) -> str:
    safe_name = html.escape(name)
    link = f"{BASE_URL}/download/lead/{token}"
    claim_link = _claim_link(discount_code, primary_focus)
    expiry = _format_expiry(expires_at)
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:32px 20px;background:#191735;
font-family:Georgia,serif;color:#e9e4f5;">
<div style="max-width:480px;margin:0 auto;">
<p style="color:#d4920a;font-size:13px;letter-spacing:.08em;
text-transform:uppercase;margin:0 0 20px;">Arvelos</p>
<p style="font-size:16px;">Hi {safe_name},</p>
<p style="font-size:16px;">Your free birth chart preview is ready — calculated
from your real birth details, not a template.</p>
<p style="margin:20px 0;">
<a href="{link}" style="background:#3a3568;color:#f5eedc;text-decoration:none;
padding:12px 24px;border-radius:8px;font-weight:bold;display:inline-block;
font-size:14px;">Download your free preview (PDF)</a></p>
<div style="margin:28px 0;padding:20px;border:1.5px dashed #d4920a;border-radius:10px;
background:rgba(212,146,10,0.08);">
<p style="margin:0 0 8px;font-size:13px;letter-spacing:.06em;text-transform:uppercase;
color:#d4920a;font-weight:bold;">Reserved for you — {discount_pct}% off your full report</p>
<p style="margin:0 0 10px;font-family:Georgia,serif;font-size:22px;letter-spacing:.04em;
color:#f5eedc;font-weight:bold;">{discount_code}</p>
<p style="margin:0 0 14px;font-size:12.5px;color:#a9a3c9;">Gone after {expiry} —
one-time use, then this price won't come back.</p>
<a href="{claim_link}" style="background:#d4920a;color:#191735;text-decoration:none;
padding:12px 26px;border-radius:8px;font-weight:bold;display:inline-block;
font-size:14px;">Claim your reserved {discount_pct}% off &rarr;</a>
</div>
<p style="font-size:12px;color:#8b84a8;margin:0 0 20px;">P.S. This code is reserved for you
specifically — it can only be used once, by whoever claims it first.</p>
<p style="font-size:13px;color:#a9a3c9;">Questions? Reply to this email: {SUPPORT_EMAIL}</p>
<p style="font-size:13px;color:#a9a3c9;">Warmly,<br>Arvelos<br>Your NextGen Astral Report</p>
<p style="text-align:center;margin:20px 0 0;">
<img src="{BASE_URL}/email-logo.png" alt="Arvelos" width="40" height="40"
style="width:40px;height:40px;border-radius:50%;"><br>
<span style="font-size:10.5px;color:#5d5885;">© 2026 Arvelos</span></p>
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
                      token: str, language: str = "en") -> bool:
    if language == "hi":
        subject = "आपकी अरवेलोस कुंडली मिलान रिपोर्ट तैयार है"
        text, body_html = _email_text_hi(name, token), _email_html_hi(name, token)
    else:
        subject = f"Your Arvelos {tier_name} is ready"
        text, body_html = _email_text(name, tier_name, token), _email_html(name, tier_name, token)

    if os.environ.get("RESEND_API_KEY"):
        _send_via_resend(to_email, subject, body_html, text)
    elif os.environ.get("SMTP_HOST"):
        _send_via_smtp(to_email, subject, text)
    else:  # dev mode: write to outbox instead of sending
        _write_to_outbox(to_email, subject, text, token)
    return True


def send_lead_teaser_email(to_email: str, name: str, token: str,
                           discount_code: str, discount_pct: int,
                           expires_at: str, primary_focus: str | None = None) -> bool:
    subject = f"Your free birth chart preview + {discount_pct}% off (48h only)"
    text = _lead_text(name, token, discount_code, discount_pct, expires_at,
                      primary_focus)

    if os.environ.get("RESEND_API_KEY"):
        _send_via_resend(to_email, subject,
                         _lead_html(name, token, discount_code, discount_pct, expires_at,
                                    primary_focus),
                         text)
    elif os.environ.get("SMTP_HOST"):
        _send_via_smtp(to_email, subject, text)
    else:  # dev mode: write to outbox instead of sending
        _write_to_outbox(to_email, subject, text, token)
    return True
