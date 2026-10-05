# Hindi Reports (English / हिन्दी) Design

Status: draft for approval. No code changed yet.

## Goal

Let a customer choose the language of their report, English or Hindi, with English as the default. Hindi reports are written natively in the vocabulary and structure Hindi-reading customers expect from a Kundli, not translated from the English text.

## Scope

**Phase 1 (this spec): Kundli Matching in Hindi** (`vedic_compat`), plus all the shared plumbing: the language option, backend field, Devanagari PDF fonts, delivery email.
**Phase 2: Vedic Kundli report in Hindi** (`vedic`), including the North Indian chart.
**Not in scope:** Hindi for Western, Mixed, Zodiac Matching or Kundli + Zodiac tiers; a Hindi version of the website itself; Hindi ads (a follow-up once a Hindi product exists).

Why Kundli Matching first: it is what the India ads sell, and its content surface is small and fixed (eight kootas, a total, a verdict). That makes it the cheapest place to prove the Hindi approach and get an astrologer's sign-off before the 30+ page Kundli.

## 1. The language option (site)

- A single "Report language / रिपोर्ट की भाषा" select with two options, **English** (selected by default) and **हिन्दी**.
- Placed directly **below the Place of Birth (city) field** on the individual order form. On the Kundli Matching form it appears once, directly below the partner's Place of Birth, so it sits after both people's details.
- It is a report language only. The rest of the page stays English in this phase.
- Hindi is offered only for tiers that have a Hindi report. If the customer picks Hindi and a tier without one, the form shows a short note ("Hindi is available for Vedic and Kundli Matching reports") and does not let them continue, instead of silently producing English. The note appears whichever of the two they chose first.
- Pricing is identical in both languages.

## 2. Backend

- `OrderIn` gains `language`, pattern `^(en|hi)$`, default `en`.
- `orders` table gets `language TEXT NOT NULL DEFAULT 'en'`, added with the existing `_add_column` helper, so existing rows and old clients keep working.
- The server decides what is allowed, as it already does for price: it rejects `hi` on a tier with no Hindi report. The frontend note is a courtesy, not the control.
- `generate_report` and `generate_compatibility_report` take the language and pick the Hindi context builder, template and fonts. The calculation engine is unchanged: the same planets, degrees and gunas feed both languages, so numbers can never differ between them.
- The delivery email subject and body and the success page labels follow the order's language.
- Analytics events add the language, with the report type only, as today.

## 3. Hindi content: native, from one reviewed source

There is no AI at runtime today, and I would keep it that way. Hindi text is authored once, reviewed, and shipped as data.

- New package `backend/content_hi/`, written in Hindi, not derived from `content_*.py`.
- A single **glossary** file is the source for every term (planets, signs, nakshatras, houses, kootas, dosha names). Templates read from it, so a term is spelled one way everywhere.
- Register: respectful second person (आप), traditional vocabulary (जातक/जातिका where a third-person phrase is needed), Sanskrit-derived terms as Hindi readers know them. Numerals stay 0-9 for tables to keep columns aligned and avoid mixed-digit confusion.
- Names entered in Latin script print as typed.

### Hindi Kundli Matching outline (Phase 1)

1. आवरण: दोनों नाम, जन्म विवरण
2. एक नज़र में: कुल गुण (36 में से), निष्कर्ष, चंद्र राशि और नक्षत्र दोनों के
3. अष्टकूट मिलान तालिका: वर्ण 1, वश्य 2, तारा 3, योनि 4, ग्रह मैत्री 5, गण 6, भकूट 7, नाड़ी 8, with the score for each
4. हर कूट का विवरण: what it measures and what this pair's score means, in plain Hindi
5. भकूट और नाड़ी: stated plainly, with the traditional note on when they are considered cancelled, only if the engine computes the cancellation
6. मांगलिक स्थिति: both charts, shown separately from the 36 (the convention on Drik Panchang and others)
7. दोनों का संक्षिप्त परिचय
8. सार और अगला कदम, plus the reflection-and-entertainment disclaimer in Hindi

The verdict bands must be fixed by us and stated once in the glossary. Published sources differ. Drik Panchang uses 31-36 अति उत्तम, 21-30 बहुत अच्छा, 17-20 साधारण, 0-16 अशुभ, while many families treat 18 as the traditional minimum. Wording must stay "personalised insight", with no claim that a marriage will or won't succeed.

### Hindi Vedic Kundli outline (Phase 2)

जन्म विवरण; एक नज़र में (लग्न, चंद्र राशि, नक्षत्र और पद); लग्न कुंडली (North Indian diamond chart); नवांश; ग्रह स्थिति तालिका (ग्रह, राशि, अंश, नक्षत्र, भाव, वक्री); 12 भाव फल; 9 ग्रह फल; विंशोत्तरी महादशा with the current दशा-अंतर्दशा read; उपाय (practice, mantra, charity, framed as tradition, no guarantees); disclaimer.
It is deliberately Moon, Lagna and Nakshatra centred, with no Sun-sign or numerology sections, because that is what Hindi Kundlis lead with.

## 4. PDF and fonts

- The Docker image has only `fonts-dejavu-core`, which has no Devanagari, so Hindi would print blank boxes. Add a Noto Devanagari font package to the `Dockerfile` and `Aptfile`.
- Separate Hindi templates (`report_hi.html`, `compatibility_report_hi.html`), same navy and gold design.
- Test render in the production image: WeasyPrint with Pango must shape conjuncts (क्ष, त्र, ज्ञ) and matras correctly. This is checked visually page by page before launch.
- Phase 2 adds a North Indian chart SVG function in `chart_graphics.py`.

## 5. Accuracy and review

- Calculation is shared, so the check is on text: a golden test renders the same chart in both languages and asserts that every number, planet position and score matches.
- An astrologer who reads Hindi reviews the glossary and every section template before launch. This is the one gate I can't do myself.
- The Guna Milan engine has not been checked against a trusted reference (an open item from the original build). That check is needed before we sell the Hindi version as well.
- Dosha detection (मंगल दोष, कालसर्प, साढ़ेसाती) is not in the current engine as a validated feature. Phase 1 shows मांगलिक status only if it can be computed and verified; otherwise it is left out, not guessed.

## 6. Rollout

1. Approve this spec and answer the open questions below.
2. Build the language field and plumbing behind the English default. English behaviour must not change, and existing tests and orders stay valid.
3. Build Hindi Kundli Matching content and template, render samples, send to the reviewer.
4. Deploy after sign-off. Then Hindi ad copy and a Hindi creative for India.

## Decisions (2026-10-05)

1. **No astrologer reviewer is available.** Mitigation: every term comes from the single glossary, taken from established published Hindi sources (Hindi Wikipedia's ज्योतिष शब्दावली, Drik Panchang, classical Parashari wording). Text is conservative and non-predictive. A native-reader proofread is still recommended before the Hindi tier is advertised; it is not a technical gate.
2. **Length: each Hindi report is 20 to 24 pages.** The outline above is sized to that. Verdict bands: the published Drik Panchang bands (31-36 अति उत्तम, 21-30 बहुत अच्छा, 17-20 साधारण, 0-16 अशुभ), stated once in the glossary, since no other preference was given.
3. **मांगलिक status is in Phase 1**, using the standard, widely published rule (Mars in the 1st, 2nd, 4th, 7th, 8th or 12th house from the Lagna, also checked from the Moon), verified against reference charts before use. Cancellation (भंग) rules are shown only if implemented and verified.
4. **Tone: formal Hindi (शुद्ध हिन्दी) for about 80% of the text, everyday Hindi for about 20%** (headlines of each section's plain-language takeaway, the summary and next steps).
