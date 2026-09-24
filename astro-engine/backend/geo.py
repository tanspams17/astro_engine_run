"""
IP -> country lookup, offline (geoip2fast bundles its own database, no
external API call, no key). Drives the phone-code default and, via
pricing_currency(), which currency a visitor is priced and charged in.
The currency is decided here on the server from the connection's IP and
never taken from the client, so there is no toggle or request field to
tamper with; a VPN can still change the apparent country.
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
    # Traefik sits in front of us and appends the address it actually saw
    # to X-Forwarded-For, so read the LAST entry: anything before it could
    # have been supplied by the client, and currency now depends on this.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[-1].strip()
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


INR_COUNTRIES = {"IN"}


def pricing_currency(request: Request) -> str:
    """INR for visitors in India, USD for everyone else (and whenever the
    country can't be determined)."""
    country = country_for_ip(client_ip(request))
    return "INR" if country in INR_COUNTRIES else "USD"
