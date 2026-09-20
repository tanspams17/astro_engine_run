# Compatibility Reports — Design Spec

Date: 2026-09-21
Status: Approved by product owner, proceeding to implementation.

## 1. Purpose

Add a second paid product line to Arvelos: a **compatibility report** comparing
two people's birth details, sold alongside the existing single-person
Western/Vedic/Mixed reports. Three new tiers:

| Tier key         | Label                    | Price (USD) |
|-------------------|--------------------------|-------------|
| `zodiac_compat`   | Zodiac Compatibility     | $24.00      |
| `vedic_compat`    | Vedic Compatibility      | $30.00      |
| `mixed_compat`    | Combined Compatibility   | $39.00      |

This is a standalone product (its own pricing cards, its own form), not a
feature gated behind an existing single-person purchase — chosen because the
site has no accounts/login system, and gating it behind a prior purchase
would either require building one or an awkward token-based add-on flow.
A cross-sell link to it may be added later on the delivered-report page and
in the delivery email, but that is out of scope for this implementation.

## 2. Non-goals (explicitly out of scope)

- Full Western synastry (planet-to-planet cross-chart aspects). The Western
  side of the compatibility report uses **numerology comparison + zodiac
  element/modality compatibility** instead — simpler, and reuses existing
  engines almost entirely.
- Accounts/login, or any "add this to a report you already bought" flow.
- A combined single numeric score across both traditions — Western stays
  descriptive, Vedic stays numeric (Guna Milan, out of 36).
- Any third-party purchase flow ("buy about two other people") — the buyer
  is always one of the two people. Fields are labeled "Your details" /
  "Your Partner's details", not "Person A" / "Person B".
- Razorpay/INR — inherits the USD-only, Stripe-only checkout already in
  place (see `backend/payment/GATEWAYS.md`).

## 3. Data model

Extend the existing `orders` table (chosen over a parallel table or a JSON
blob — see design discussion — specifically to inherit the existing GDPR
scrub logic, payment pipeline, and order lifecycle without duplicating any
of it):

New columns (all nullable; blank/unused on every existing and future
single-person order):

```
product_type    TEXT NOT NULL DEFAULT 'individual'   -- 'individual' | 'compatibility'
partner_name           TEXT
partner_birth_date     TEXT
partner_birth_time     TEXT
partner_birth_place    TEXT
partner_lat            REAL
partner_lon            REAL
partner_tz             TEXT
partner_gender         TEXT
```

`tier` keeps its existing meaning for `product_type='individual'`
(`western|vedic|mixed`) and takes the three new values above for
`product_type='compatibility'`. `orders.PRICES` gets the three new entries
alongside the existing six USD prices.

Migration follows the existing pattern in `orders.init_db()` (checks
`PRAGMA table_info`, `ALTER TABLE ADD COLUMN` for anything missing) — no new
migration tooling needed.

## 4. API

`OrderIn` (in `app.py`) gains the partner fields, all optional, plus
`product_type` inferred server-side from `tier` (client never sends
`product_type` directly — it's derived, the same way pricing is derived
from `tier` today, not trusted from the client). A Pydantic model validator
requires all partner fields when `tier` is one of the three `*_compat`
values, and forbids them (must be absent/None) otherwise — this keeps a
single `/api/orders` endpoint and a single order lifecycle, per the
approved Option 1, rather than a second endpoint.

Partner birth date/time/timezone get the exact same validation `/api/orders`
already applies to the primary person's birth details (parseable date+time,
valid IANA tz) before any payment step — same reasoning as today: payment
must never precede a chart the engine can't actually calculate.

`/api/pay`, the Stripe webhook handler, `/api/orders/{id}/status`,
`/api/orders/{id}/retry`, and `/download/{token}` are **unchanged** — they
already operate generically on `orders` rows regardless of what's in them.

## 5. Compatibility calculation (`backend/compatibility_engine.py`, new)

Two independent pieces, each usable alone (`zodiac_compat`/`vedic_compat`)
or together (`mixed_compat`):

**Zodiac + numerology** (`zodiac_compare()`):
- Numerology: compares each person's Mulank/Bhagyank using the existing
  `FRIENDS` lookup table in `numerology.py` (already models which numbers
  get along), now applied across two people instead of one person's own
  numbers.
- Zodiac: compares each person's Sun-sign element (Fire/Earth/Air/Water)
  and modality (Cardinal/Fixed/Mutable) using the same `ELEMENTS`/`MODES`
  tables `report_generator.py`'s `_balance_section()` already has for a
  single chart.
- Output: descriptive, not a numeric score (matches Western tradition,
  which doesn't have one) — a set of interpretive sections, same shape as
  the existing report sections (`{"title":..., "body":...}`).

**Vedic Guna Milan** (`guna_milan()`):
- The classical 8-koota Ashtakoota system, scored out of 36: Varna (1),
  Vashya (2), Tara (3), Yoni (4), Graha Maitri (5), Gana (6), Bhakoot (7),
  Nadi (8).
- Inputs are each person's moon-sign (rashi) and moon-nakshatra — both
  already computed by `chart_engine.py` for every Vedic chart today; no new
  astronomical calculation.
- Implemented as reference lookup tables (nakshatra→yoni, nakshatra→gana,
  nakshatra→nadi, rashi→varna, rashi-pair→vashya score, rashi-lord
  friendship→graha maitri, rashi-distance→bhakoot, nakshatra-distance→tara),
  the same shape as the lookup tables `numerology.py` already has
  (`LUCKY`, `KUA_DIRECTIONS`, `FRIENDS`).
- **Known simplification, flagged explicitly**: several classical rules
  (Varna, Gana, Vashya) are traditionally direction-dependent (scored
  differently depending on which person is considered "the groom"). Since
  this product has no gendered framing, the implementation scores each
  koota using the more favorable of the two directions where the classical
  rule is asymmetric. This is a defensible, commonly-used modern
  adaptation, but it means results won't always match a strictly
  traditional groom/bride calculation — worth a spot-check against a
  couple of known reference calculations before this is trusted commercially,
  the same way any new astrological calculation in this codebase should be
  sanity-checked.

## 6. Report generation

`report_generator.py` gains `build_compatibility_report_context()` and a
new PDF template section set, reusing the existing Jinja2/WeasyPrint
pipeline (including the `autoescape=True` fix from this session's security
pass — both people's names are free-text customer input, same injection
surface as the existing `name` field, and must be escaped the same way).

Content shown depends on tier:
- `zodiac_compat`: numerology + zodiac sections only.
- `vedic_compat`: Guna Milan score + koota-by-koota breakdown only.
- `mixed_compat`: both.

Cover page shows both names. No individual natal-chart wheels/tables are
duplicated in the compatibility report — those already exist in the
single-person reports; this stays focused on the *comparison*.

## 7. Frontend

New section on the existing landing page (not a separate route), placed
after the existing Order section. Three pricing cards matching the existing
`.price-card` pattern. Selecting one reveals a form (same reveal/scroll
mechanic `chooseTier()` already drives) with two side-by-side field groups:
**Your details** and **Your Partner's details** — same fields as the
existing order form (name, DOB, time + "don't know exact time" checkbox,
place with the same city autocomplete), minus email/phone on the partner
side (only the buyer needs to be reachable). Coupon, opt-ins, and the pay
button are the existing components, wired to the new tier/pricing.

## 8. GDPR

`gdpr_tools.py`'s `_SCRUB_ORDER_FIELDS` gets the eight new `partner_*`
columns added to the scrub set — a one-line extension, not a new code path,
which is the concrete payoff of using named columns on the existing table
instead of a JSON blob.

## 9. Testing

- Unit tests for `compatibility_engine.py`: each koota scoring function
  against hand-computed expected values for a few fixed nakshatra/rashi
  pairs; total score bounds (0–36); zodiac/numerology comparison against
  known friend/non-friend number pairs.
- API-level negative tests (matching this session's established pattern):
  compat order missing partner fields → 422; individual order with partner
  fields present → 422; unknown tier still 422; oversized partner fields
  rejected by the same length caps as the primary person's fields.
- End-to-end: create each of the 3 new tiers with the mock/free-coupon
  path, confirm PDF generation succeeds and contains both names, confirm
  GDPR scrub removes partner fields on `approve`.
- Regression: full existing single-person order flow (all three original
  tiers) re-verified unaffected.

## 10. Explicitly deferred (future work, not this implementation)

- Cross-sell link from the delivered single-person report to the
  compatibility product.
- Any bundling/discount when buying both an individual and a compatibility
  report.
