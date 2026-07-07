"""
Arvelos content library — Vedic (Jyotish) interpretive text.
27 nakshatras, 9 dasha lords, Vedic framing passages.
Tone: warm, grounded, respectful of the tradition, no predictions.
"""

VEDIC_INTRO = (
    "Vedic astrology — Jyotish, 'the science of light' — uses the sidereal "
    "zodiac, anchored to the actual positions of the stars rather than the "
    "seasons. This report uses the Lahiri ayanamsa, the standard correction "
    "used across India, which is why your Vedic placements may differ from "
    "the Western signs you know. Neither system is 'wrong' — they measure "
    "from different starting points. Jyotish adds two lenses Western "
    "astrology doesn't use: your nakshatra (birth star), a finer 27-fold "
    "division of the sky, and the dasha system, a timeline of planetary "
    "periods that describes which themes are foregrounded in different "
    "chapters of life."
)

NAKSHATRA_INTRO = (
    "Your janma nakshatra — the lunar mansion occupied by the Moon at your "
    "birth — is considered by many Jyotish practitioners to be more "
    "personally descriptive than the sun sign. There are 27 nakshatras, each "
    "spanning 13°20' of the sky, each with its own symbol, ruling deity, and "
    "temperament."
)

# nakshatra: (symbol, ruling planet, passage)
NAKSHATRAS = {
    "Ashwini": ("a horse's head", "Ketu",
        "Ashwini is the first nakshatra — the spark of the whole wheel. Ruled by the celestial physicians, the Ashvins, it carries themes of speed, healing, and fresh starts. People born under it are often quick to act and quick to help: the friend who arrives before you finish asking. The temperament is youthful and direct, impatient with slow processes. Its lesson is pacing — knowing that not everything worth doing can be done fast, and that healers must also let themselves be healed."),
    "Bharani": ("the yoni, gateway of birth", "Venus",
        "Bharani carries the energy of the threshold — birth, death, and the passages between. Ruled by Yama, lord of dharma, it gives a strong inner moral compass and the capacity to bear what others can't. People born under it often carry responsibility early and feel life's stakes vividly. The temperament is intense, creative, and loyal. Its lesson is discernment about burdens: you can carry almost anything, which means you must choose carefully what you agree to carry."),
    "Krittika": ("a blade or flame", "Sun",
        "Krittika, home of the fire god Agni, cuts and purifies. People born under it tend to have sharp perception — they see through pretense quickly and can't easily unsee it. There's a protective fierceness here, especially toward the vulnerable, and real capacity for leadership once the sharpness is tempered with warmth. Its lesson is the difference between cutting away what's false and simply cutting: fire that cooks nourishes; fire that only burns, doesn't."),
    "Rohini": ("a chariot, or the red star Aldebaran", "Moon",
        "Rohini is the Moon's favorite residence — the nakshatra of growth, beauty, and fertile ground. People born under it often have natural magnetism and a gift for making things flourish: gardens, businesses, families, rooms. The temperament is sensual, steady, and quietly determined. Material life tends to matter and tends to respond. Its lesson is holding abundance lightly — attachment to comfort can root you in soil you've outgrown."),
    "Mrigashira": ("a deer's head", "Mars",
        "Mrigashira is the searching nakshatra — the deer following a scent through the forest. It gives lifelong curiosity, restlessness, and a gentle, alert temperament that others find easy company. People born under it are seekers: of knowledge, of places, of the better version just over the ridge. Its lesson is recognizing when the search has become the habit — some of what you're looking for is found by staying still long enough to receive it."),
    "Ardra": ("a teardrop", "Rahu",
        "Ardra, ruled by Rudra the storm god, is the nakshatra of the clearing storm. People born under it tend to live through real upheavals and emerge genuinely renewed — there's an intellectual sharpness and emotional depth here that shallow lives never develop. The temperament is penetrating, honest, sometimes turbulent. Its lesson is trusting the storm's function: what it strips away was usually ready to go, and the fresh air afterward is the point."),
    "Punarvasu": ("a quiver of arrows", "Jupiter",
        "Punarvasu means 'return of the light' — the nakshatra of renewal after the storm. It gives resilience of a rare kind: the ability to lose ground and genuinely begin again, often better. People born under it tend to be philosophical, adaptable, and fundamentally decent; homes and hearts recover in their presence. Its lesson is commitment — when you know you can always start over, finishing becomes the challenge worth choosing."),
    "Pushya": ("a cow's udder, a lotus", "Saturn",
        "Pushya is traditionally called the most nourishing of the nakshatras. It gives a caretaker's temperament with a spine of discipline — people born under it tend to become the dependable center of families and institutions, the one who actually shows up. Spiritual inclination is common and usually practical rather than showy. Its lesson is receiving: perpetual providers must learn to be nourished too, or the well runs quietly dry."),
    "Ashlesha": ("a coiled serpent", "Mercury",
        "Ashlesha is the serpent nakshatra — penetrating insight, hypnotic charm, and an instinctive grasp of human motivation. People born under it read subtext fluently; very little gets past them. That awareness can heal (they make superb counselors and strategists) or entangle, depending on how it's used. The temperament is private and perceptive. Its lesson is straightness: the serpent's wisdom is real, but trust is built in straight lines, not coils."),
    "Magha": ("a royal throne", "Ketu",
        "Magha is the nakshatra of ancestry and rightful authority. People born under it often carry a natural dignity and a strong pull toward legacy — family history matters, lineage matters, doing right by those who came before. Leadership tends to find them. The temperament is generous, proud, and tradition-respecting. Its lesson is that thrones are seats of service: authority kept for its own sake hollows out; authority used for others compounds."),
    "Purva Phalguni": ("the front legs of a bed", "Venus",
        "Purva Phalguni is the nakshatra of rest, pleasure, and creative delight — the well-earned ease after work. People born under it have warmth, charm, and a gift for enjoyment that makes others' lives brighter; art and romance come naturally. The temperament is sociable and generous. Its lesson is the relationship between pleasure and purpose: ease is a beautiful reward and a poor foundation. Build first; the bed is sweeter for it."),
    "Uttara Phalguni": ("the back legs of a bed", "Sun",
        "Uttara Phalguni is the nakshatra of the reliable ally — patronage, partnership, and promises kept. People born under it tend to be the ones others build with: generous, organized, and constant once committed. Marriages and long alliances are central themes. The temperament is warm but steady, kind but exacting. Its lesson is choosing commitments as carefully as it keeps them — a nature this loyal must aim its loyalty well."),
    "Hasta": ("an open hand", "Moon",
        "Hasta is the nakshatra of the skilled hand — craft, dexterity, wit, and the ability to make ideas tangible. People born under it are often good at nearly everything they practice: quick learners with clever hands and cleverer humor. There's a purity to Hasta's intent; it wants to do things well. Its lesson is scattering — ten skills at eighty percent is a hobby collection, one or two at mastery is a life. The hand works best when it grips."),
    "Chitra": ("a bright jewel", "Mars",
        "Chitra is the celestial architect — the nakshatra of design, brilliance, and beautiful structure. People born under it have an eye: for aesthetics, for how things fit together, for the striking detail everyone else missed. They tend to stand out without trying. The temperament is independent and creative with real technical ability underneath. Its lesson is depth over dazzle: the jewel's surface catches light, but its value is in the cut."),
    "Swati": ("a young shoot swaying in wind", "Rahu",
        "Swati is the nakshatra of independence — the single blade of grass that bends in every wind and breaks in none. People born under it need room to move; they resist control, learn by their own experiments, and often flourish in trade, negotiation, and self-made paths. The temperament is flexible, diplomatic, quietly strong. Its lesson is rootedness: freedom without a root system is just drift. The shoot that stays planted becomes the tree."),
    "Vishakha": ("a triumphal archway", "Jupiter",
        "Vishakha is the nakshatra of determined pursuit — the archway you pass under after the campaign is won. People born under it have exceptional goal-focus: patient, strategic, and genuinely undeterred by obstacles that stop others. Ambition here is real and usually earned. The temperament is purposeful and passionate. Its lesson is presence: a life aimed entirely at the next archway forgets to notice the road, and the road is most of the life."),
    "Anuradha": ("a lotus blooming in mud", "Saturn",
        "Anuradha is the nakshatra of friendship and devotion — the lotus that blooms precisely because of the mud. People born under it have a gift for loyalty and for cooperation across differences; they build bridges others thought impossible and thrive far from where they started. The temperament is warm, disciplined, and softly courageous. Its lesson is self-worth independent of usefulness: you are the friend everyone calls; let some calls be yours."),
    "Jyeshtha": ("an earring or umbrella", "Mercury",
        "Jyeshtha means 'the eldest' — the nakshatra of seniority, protection, and hard-won authority. People born under it often become responsible early and carry an air of having seen more than their years. There's sharp intelligence and a protective instinct toward their circle. The temperament is proud, capable, and private about its struggles. Its lesson is softness: the eldest child learns to seem invulnerable, and unlearning that is where intimacy begins."),
    "Mula": ("a bundle of roots", "Ketu",
        "Mula means 'root' — the nakshatra that digs to the bottom of things. People born under it are natural investigators of foundations: of ideas, of institutions, of themselves. They can dismantle what's false with startling thoroughness, and their lives often include a genuine reinvention. The temperament is direct, philosophical, and unafraid of endings. Its lesson is gentleness in the digging — not everything that can be uprooted needs to be."),
    "Purva Ashadha": ("a fan, or water rising", "Venus",
        "Purva Ashadha is the invincible nakshatra — early victory, rising water, undefeatable optimism. People born under it carry genuine confidence and persuasive power; they lift rooms and rally teams, and they rarely accept that something can't be done. The temperament is proud, buoyant, and ambitious. Its lesson is listening: conviction this strong can stop taking in new information. The water that rises highest is fed by many streams."),
    "Uttara Ashadha": ("an elephant's tusk", "Sun",
        "Uttara Ashadha is the nakshatra of the lasting victory — not the quick win but the one that stands. People born under it tend toward integrity that others eventually organize around; they may start slow, but what they build endures. Leadership here is earned through consistency rather than charisma. The temperament is honorable, patient, and quietly immovable. Its lesson is starting before certainty: the tusk grows while the elephant walks."),
    "Shravana": ("an ear", "Moon",
        "Shravana is the nakshatra of listening — sacred learning received through hearing. People born under it are natural students and eventually natural teachers: they absorb, connect, and transmit knowledge, and others trust their counsel. The temperament is thoughtful, orderly, and genuinely curious about people. Its lesson is acting on what's heard: perpetual students can hide in the next course, the next book. At some point, the ear must inform the hand."),
    "Dhanishta": ("a drum", "Mars",
        "Dhanishta is the drum — the nakshatra of rhythm, resonance, and wealth that gathers around skill. People born under it often have musical or rhythmic gifts, literal or metaphorical: timing, cadence, knowing when to move. Group endeavors amplify them. The temperament is energetic, ambitious, and performance-ready. Its lesson is inner resonance: a drum is hollow by design, but a person isn't — fill the private life as carefully as the public one."),
    "Shatabhisha": ("an empty circle, a hundred healers", "Rahu",
        "Shatabhisha means 'a hundred physicians' — the nakshatra of healing, secrecy, and vast systems. People born under it are drawn to what's hidden: medicine, research, technology, the workings behind the visible. They often prefer solitude and think in ways that take others years to catch up to. The temperament is independent, perceptive, and reserved. Its lesson is letting yourself be found: the healer who hides needs a healer too."),
    "Purva Bhadrapada": ("the front legs of a funeral cot", "Jupiter",
        "Purva Bhadrapada is the nakshatra of intensity in service of transformation — the fire that burns toward something higher. People born under it tend to have philosophical depth and a certain fierceness of conviction; they're drawn to causes and questions bigger than comfort. The temperament is passionate, principled, and sometimes stormy. Its lesson is warmth: ideals held too hotly can scorch the people nearest them. The cause includes the humans in the room."),
    "Uttara Bhadrapada": ("the back legs of a funeral cot", "Saturn",
        "Uttara Bhadrapada is the nakshatra of the deep, still water — wisdom that comes from restraint and long patience. People born under it have unusual emotional depth and self-control; they anchor others in crises and keep confidences like vaults. Kundalini and contemplative themes run through this star's tradition. The temperament is calm, kind, and quietly formidable. Its lesson is expression: stillness this complete can be mistaken for absence. Let people see the depth."),
    "Revati": ("a fish swimming in the sea", "Mercury",
        "Revati is the final nakshatra — the fish in the boundless sea, the safe passage at journey's end. People born under it are natural protectors of travelers, animals, and anyone in transition; compassion here is instinctive, not performed. Creative and spiritual gifts are common. The temperament is gentle, generous, and dreamier than the world always accommodates. Its lesson is boundaries: a heart open to every current needs a shore of its own."),
}

# ------------------------------------------------------------- DASHAS

DASHA_INTRO = (
    "The Vimshottari dasha system divides life into planetary chapters — "
    "major periods (mahadashas) ruled by each of the nine grahas, in a fixed "
    "sequence totalling 120 years, with your starting point set by the Moon's "
    "position at birth. A dasha doesn't make events happen; Jyotish reads it "
    "as which themes are foregrounded — which teacher is at the front of the "
    "classroom in this chapter of your life."
)

DASHA_LORDS = {
    "Sun": "A Sun mahadasha foregrounds identity, visibility, and authority. Themes of this chapter tend to include stepping into leadership, clarifying who you are apart from others' expectations, and dealings with father figures, institutions, and status. It rewards self-definition and honest ambition; it exposes borrowed identities. The classical advice for Sun periods: build a self worth being seen, then let it be seen.",
    "Moon": "A Moon mahadasha foregrounds the emotional life: home, mother and maternal figures, belonging, and the state of your inner tides. This chapter tends to soften priorities — relationships and nourishment come forward, achievement recedes slightly. It rewards tending: to family, to feelings, to the physical home. Its challenge is fluctuation; the practice is riding tides without calling every low tide a crisis.",
    "Mars": "A Mars mahadasha foregrounds energy, courage, and contest. This chapter tends to bring more drive and more friction — projects that need a fighter, situations that need a spine, sometimes conflicts that need choosing wisely. Physical vitality and technical skill often sharpen. It rewards disciplined action and honest competition; it punishes aimless aggression. The classical counsel: give Mars a mission, or it will find a fight.",
    "Rahu": "A Rahu mahadasha foregrounds ambition and unfamiliar territory. Rahu is the hungry node — this chapter tends to pull you toward what you've never had: new fields, foreign places, larger stages, unconventional paths. Gains can be substantial and fast; so can obsession. It rewards bold experiments held with self-awareness; its trap is mistaking appetite for direction. Keep asking what the hunger is actually for.",
    "Jupiter": "A Jupiter mahadasha foregrounds growth, wisdom, and fortune-through-alignment. This chapter tends to expand whatever you sincerely invest in: learning, teaching, family, faith, long-term ventures. Mentors and opportunities appear more readily. It rewards generosity and principled choices; its subtle trap is complacency — Jupiter's ease can make effort feel optional. Classical counsel: in the season of favor, plant heavily.",
    "Saturn": "A Saturn mahadasha foregrounds structure, endurance, and the long game. This chapter tends to slow things down and test foundations — what's solid consolidates, what's hollow is revealed. Responsibility increases; shortcuts stop working. It is, by tradition, the great maturer: people often emerge from Saturn periods with their most durable achievements and their clearest sense of what actually matters. The counsel is simple: do the work, keep your word, rest properly.",
    "Mercury": "A Mercury mahadasha foregrounds intellect, communication, and commerce. This chapter tends to accelerate learning, writing, trade, and networks — ideas become assets. Wit sharpens and options multiply. It rewards skill-building and clear speech; its trap is scatter — Mercury opens many doors and closes none. The practice of this period is curation: choose which conversations, projects, and skills deserve the full mind.",
    "Ketu": "A Ketu mahadasha foregrounds release, insight, and the inward turn. Ketu is the tail of the serpent — already-finished business. This chapter tends to loosen attachments that no longer serve, sometimes abruptly, and to reward contemplative depth, research, and spiritual practice. Material ambition often quiets. Its gift is clarity about what you never needed; its practice is trusting the emptying rather than rushing to refill it.",
    "Venus": "A Venus mahadasha foregrounds love, art, comfort, and connection. At twenty years, it's the longest chapter — themes include partnership, aesthetics, wealth-through-relationships, and the refinement of taste and values. Life tends to sweeten where you let it. It rewards devotion and craftsmanship; its trap is indulgence without meaning. The classical counsel: enjoy fully, but let pleasure serve love rather than replace it.",
}

SYNTHESIS_INTRO = (
    "You chose the Mixed report, so here both systems sit side by side. A "
    "quick honest note: Western and Vedic astrology will often place your "
    "planets in different signs, because they anchor the zodiac differently "
    "— Western to the seasons (tropical), Vedic to the stars (sidereal). "
    "That's not a contradiction; it's two calibrated instruments measuring "
    "from different reference points. The most useful way to read them "
    "together: Western astrology tends to describe the psychological weather "
    "— personality as experienced from inside. Jyotish tends to describe the "
    "karmic terrain — patterns, timings, and territories as seen from above. "
    "Where the two agree about you, pay special attention: that's the same "
    "signal arriving through two independent instruments."
)
