"""
IP -> country lookup for the region-default UX (which currency/gateway a
visitor sees first). Offline (geoip2fast bundles its own database, no
external API call, no key) — this is a convenience default only, never a
security or payment-authorization boundary: the customer's chosen
currency at checkout is what actually selects the gateway.
"""
from __future__ import annotations

from fastapi import Request

_geo = None


def _engine():
    global _geo
    if _geo is None:
        from geoip2fast import GeoIP2Fast
        _geo = GeoIP2Fast()
    return _geo


def client_ip(request: Request) -> str:
    # Traefik sits in front of us; trust the first hop of X-Forwarded-For.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


def country_for_ip(ip: str) -> str | None:
    if not ip:
        return None
    try:
        result = _engine().lookup(ip)
        code = result.country_code
        return code if code and code != "--" else None
    except Exception:
        return None
