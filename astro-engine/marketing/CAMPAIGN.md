# Arvelos — Campaign Plan (per spec §8–9)

## Launch creatives (produced, in /videos)

| File | Market | Hook | Voice |
|---|---|---|---|
| diaspora_vedic_s1_textoverlay.mp4 | Indian diaspora (UK/US/CA) | Authenticity ("wrong zodiac") | Liam |
| domestic_vedic_s2_textoverlay.mp4 | India domestic | Curiosity ("nakshatra") | Matilda |
| wellness_western_s3_textoverlay.mp4 | US/UK wellness | Honesty (anti-subscription) | Sarah |

All compliance-checked: no predictive or personalized-outcome claims (Meta
spiritual/wellness policy, spec §7). Regenerate any variant with
`python3 gen_videos.py` after editing scripts/voices.

## Destination links (paste as each ad's URL)

```
https://arvelos.cloud/?utm_source=meta&utm_medium=paid-social&utm_campaign=diaspora&utm_content=s1_textoverlay&utm_term=authenticity
https://arvelos.cloud/?utm_source=meta&utm_medium=paid-social&utm_campaign=domestic&utm_content=s2_textoverlay&utm_term=curiosity
https://arvelos.cloud/?utm_source=meta&utm_medium=paid-social&utm_campaign=wellness&utm_content=s3_textoverlay&utm_term=honesty
```

For organic Reels / bio link, use `utm_medium=organic-social`.
UTMs are captured at quiz-start and stored against the order — CAC per
creative is queryable from the events table without Meta's dashboard.

## Campaign structure (when Meta account exists)

Campaign (CBO) per market → Ad set per hook → Ad per format variant.
Naming: `[market]_[tier-focus]_[script#]_[format]`.

## Phase plan
- **Phase 0 (now, £0):** organic Reels 3–4×/week per the content track,
  seed diaspora WhatsApp/FB groups, collect first sales + reviews.
- **Phase 1 (test):** ~£400–700 across the 3 launch ad sets, £15–30/day/ad
  set, 4–7 days minimum before judging. Kill below account-average CPA;
  let CBO consolidate into winners.
- **Phase 2 (scale):** reinvest converting revenue; re-run the test cycle
  for every new script/market variant.

## Organic content batch ideas (no spend, same brand kit)
- "Which nakshatra are you?" carousel series (27 posts — one per nakshatra,
  text from content_vedic.py, one per day for a month)
- Western vs Vedic explainer reels (educational, doubles as ad R&D)
- Planetary-theme quote graphics (reuse PDF's gold/indigo brand kit)
