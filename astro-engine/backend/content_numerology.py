"""
Numerology + monthly-forecast interpretive text. Warm, grounded, no health
claims, no gemstone selling. Number essences are shared across contexts
(mulank / bhagyank / name) with context-specific framing.
"""

NUMBER_ESSENCE = {
    1: "the Sun's number — leadership, originality, and self-made momentum. Ones initiate; they'd rather build their own path than inherit one, and they light up when given real responsibility. The watch-out is ego crowding out listening.",
    2: "the Moon's number — sensitivity, diplomacy, and imagination. Twos read moods with uncanny accuracy and hold relationships together quietly. Their strength looks soft but isn't: patience, timing, and emotional intelligence. The watch-out is absorbing everyone's weather and calling it their own.",
    3: "Jupiter's number — wisdom, expression, and natural optimism. Threes teach, entertain, and expand whatever room they're in; luck seems to follow their generosity. The watch-out is scattering energy across too many enthusiasms at once.",
    4: "Rahu's number — the unconventional builder. Fours think differently, question rules, and often live lives with sudden turns that end up making sense only in hindsight. They are grounded, hardworking, and quietly rebellious. The watch-out is stubbornness and a tendency to expect the worst.",
    5: "Mercury's number — quickness, communication, and versatility. Fives learn fast, sell well, adapt anywhere, and need variety like air. Money and ideas both move quickly around them. The watch-out is restlessness — finishing is their acquired skill.",
    6: "Venus's number — love, beauty, and responsibility for others. Sixes create harmony, host, heal rifts, and attract comfort. People trust them instinctively with what matters. The watch-out is over-giving, then quietly resenting it.",
    7: "Ketu's number — depth, intuition, and the researcher's mind. Sevens are curious, spiritually inclined, and see through surfaces; they need solitude the way others need company. The watch-out is distance — seeming unreachable to the very people who love them.",
    8: "Saturn's number — discipline, endurance, and late-blooming success. Eights carry heavy loads early and build things that last; their word is their contract. Life tests them more, then pays better. The watch-out is all work, delayed joy.",
    9: "Mars's number — courage, drive, and humanitarian fire. Nines fight for people and finish what others abandon; their energy is contagious. The watch-out is a short fuse and taking on battles that were never theirs.",
}

MULANK_INTRO = ("Your Mulank (psychic number) comes from your day of birth. "
                "It describes how you see yourself — your instinctive nature, "
                "the you that shows up before thinking.")
BHAGYANK_INTRO = ("Your Bhagyank (destiny number) comes from your complete "
                  "date of birth. It describes the road: the themes, lessons "
                  "and opportunities life keeps arranging for you.")
NAME_INTRO = ("Your name number comes from the Chaldean value of the name "
              "you actually use. It colours how the world receives you — "
              "your public frequency.")
SOUL_INTRO = "Your soul urge number (vowels of your name) is what quietly motivates you beneath every goal:"
PERSONALITY_INTRO = "Your personality number (consonants) is the first impression you give before people know you:"

KARMIC_DEBT_TEXT = {
    13: "Born on the 13th, you carry karmic number 13 — the lesson of honest work. Shortcuts collapse for you faster than for others; steady, transparent effort compounds unusually well. It's a strict teacher that produces genuinely durable success.",
    14: "Born on the 14th, you carry karmic number 14 — the lesson of freedom with self-control. Life gives you variety and temptation in equal measure; moderation is your multiplier. When you master your appetites, your adaptability becomes a superpower.",
    16: "Born on the 16th, you carry karmic number 16 — the lesson of the rebuilt tower. Plans in your life sometimes collapse so that something truer can be built; each rebuild leaves you wiser and harder to shake. Ego-checks come early so that authenticity can arrive sooner.",
    19: "Born on the 19th, you carry karmic number 19 — the lesson of independence learned the full way round: standing alone, then discovering you never had to. Self-reliance is your gift; letting others contribute is your graduation.",
}

COMBO_TEXT = (
    "Read together, your Mulank {m} ({mp}) and Bhagyank {b} ({bp}) form the "
    "core dialogue of your numbers: how you instinctively act, versus what "
    "life keeps asking of you. {verdict}")
COMBO_FRIENDLY = ("These two numbers are natural allies — your instincts and "
                  "your life-path pull in the same direction, which usually "
                  "shows as decisions that 'click' once you stop second-guessing them.")
COMBO_NEUTRAL = ("These two numbers are neither allies nor rivals — your "
                 "instincts and your life-path negotiate. The pattern to watch: "
                 "what you want fast versus what life delivers on its own "
                 "schedule. Maturity here is learning both clocks.")

MISSING_NUMBER = {
    1: "Missing 1 (Sun): self-assertion is a learned skill rather than a reflex. Practice stating opinions early in conversations; leadership grows with each rep.",
    2: "Missing 2 (Moon): emotional expression may need deliberate effort. Naming feelings out loud — even clumsily — builds the muscle this grid runs light on.",
    3: "Missing 3 (Jupiter): guidance and mentorship may feel scarce. Actively seek teachers and be one — teaching others is the classical remedy for a missing 3.",
    4: "Missing 4 (Rahu): structure and routine don't come pre-installed. External systems — lists, fixed hours, one place for everything — return outsized dividends.",
    5: "Missing 5 (Mercury): flexibility and quick pivots take practice. Small deliberate changes of routine keep this muscle warm; travel helps more than average.",
    6: "Missing 6 (Venus): domestic ease and self-care need scheduling, not mood. Beautifying your space is functional, not indulgent, for this grid.",
    7: "Missing 7 (Ketu): stillness and reflection must be chosen deliberately. Ten quiet minutes daily does for you what an hour does for others.",
    8: "Missing 8 (Saturn): money discipline and long-game patience benefit from external structure — automatic savings, written plans, fixed review dates.",
    9: "Missing 9 (Mars): drive arrives in waves rather than a steady current. Physical activity is the most reliable way to summon it on demand.",
}

GRID_PLANE_NOTE = (
    "Practitioners also read the grid's rows and columns as 'planes' — mind "
    "(4-9-2), emotion (3-5-7) and practicality (8-1-6). Where your digits "
    "cluster shows where your energy naturally pools; where they're sparse "
    "shows what benefits from conscious practice.")

# ---------------------------------------------------------------- monthly

PERSONAL_MONTH = {
    1: dict(theme="Beginnings",
            positive="high initiative, fresh starts, visibility, decisions that set the tone for months ahead",
            negative="impatience, going it alone when help is available",
            tips="Start the thing. Send the first message, file the application, open the account. Choose one priority and let it lead."),
    2: dict(theme="Patience & partnership",
            positive="cooperation, useful slow-downs, relationships deepening, details surfacing",
            negative="oversensitivity, indecision, waiting for perfect certainty",
            tips="Don't force outcomes this month — nurture them. Listen twice as much; partnerships formed now tend to hold."),
    3: dict(theme="Expression & luck",
            positive="creativity, social expansion, communication landing well, optimism returning",
            negative="scattered focus, overcommitment, saying more than needed",
            tips="Publish, present, host, pitch. Your words carry further than usual — aim them at what you actually want."),
    4: dict(theme="Foundation work",
            positive="discipline paying off, systems clicking into place, practical progress",
            negative="feeling boxed in, all effort and no applause",
            tips="Do the unglamorous work: paperwork, health routines, budgets, repairs. What you organize now supports the whole year."),
    5: dict(theme="Change & movement",
            positive="opportunities through travel and new contacts, quick wins, welcome surprises",
            negative="restlessness, impulsive commitments, spreading thin",
            tips="Say yes to movement — trips, meetings, experiments — but keep contracts short. Flexibility is the asset this month."),
    6: dict(theme="Home & responsibility",
            positive="family matters resolving, domestic upgrades, being genuinely needed, love strengthening",
            negative="over-obligation, carrying what isn't yours",
            tips="Invest in home and close relationships. Beautify your space. Choose which duties are truly yours before accepting more."),
    7: dict(theme="Reflection & study",
            positive="insight, learning, spiritual recharge, answers arriving in quiet",
            negative="isolation read as rejection, overthinking",
            tips="Step back deliberately. Study, research, rest. Big decisions clarify on their own if you give them two quiet weeks."),
    8: dict(theme="Power & harvest",
            positive="money matters foregrounded, recognition, authority, karmic returns on old effort",
            negative="power friction with seniors, all-or-nothing thinking",
            tips="Negotiate, invoice, ask for the raise, settle accounts. Act like the executive of your own life — the month rewards it."),
    9: dict(theme="Completion & release",
            positive="closure, generosity returning, clearing space, emotional resolution",
            negative="endings feeling heavier than they are, nostalgia steering decisions",
            tips="Finish and release: complete projects, forgive balances, declutter. Don't plant new seeds yet — clear the field for next month's 1."),
}

# transit framing (relative house from natal Moon, classical Vedic results)
JUPITER_GOOD = {2, 5, 7, 9, 11}
SATURN_GOOD = {3, 6, 11}

JUPITER_NOTE_GOOD = ("Jupiter transits your {h} house from the Moon — a classically supportive placement for growth, support from mentors, and doors opening with less pushing.")
JUPITER_NOTE_HARD = ("Jupiter transits your {h} house from the Moon — expansion this month works quietly rather than loudly; growth comes through consolidation, not leaps.")
SATURN_NOTE_GOOD = ("Saturn transits your {h} house from the Moon — a strong position for disciplined effort; work done properly now builds unusually durable results.")
SATURN_NOTE_HARD = ("Saturn transits your {h} house from the Moon — Saturn asks for patience here; keep commitments modest, honour routines, and let slow be smooth.")
SADE_SATI_NOTE = ("You are in a Sade Sati window (Saturn near your natal Moon). Tradition reads this not as bad luck but as a maturing pressure: simplify, keep your word, protect rest, and this period becomes a forge rather than a burden.")

MONTHLY_INTRO = (
    "This section maps your coming twelve months through two independent "
    "lenses at once: your numerology personal-month cycle (a 1–9 rhythm "
    "personal to your birth date) and the real transits of Jupiter and "
    "Saturn — the two slow planets classical astrology weights most — "
    "measured from your natal Moon. Read each month as weather guidance: "
    "what the month favours, what it resists, and how to work with it. "
    "Nothing here is a prediction of events; it is timing intelligence.")
