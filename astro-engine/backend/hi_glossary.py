"""Hindi glossary: the single source for every Hindi term used in the Hindi
reports. Keys are the English names used by the calculation engine."""

SIGNS = {
    "Aries": "मेष", "Taurus": "वृषभ", "Gemini": "मिथुन", "Cancer": "कर्क",
    "Leo": "सिंह", "Virgo": "कन्या", "Libra": "तुला", "Scorpio": "वृश्चिक",
    "Sagittarius": "धनु", "Capricorn": "मकर", "Aquarius": "कुंभ", "Pisces": "मीन",
}

NAKSHATRAS = {
    "Ashwini": "अश्विनी", "Bharani": "भरणी", "Krittika": "कृत्तिका", "Rohini": "रोहिणी",
    "Mrigashira": "मृगशिरा", "Ardra": "आर्द्रा", "Punarvasu": "पुनर्वसु", "Pushya": "पुष्य",
    "Ashlesha": "आश्लेषा", "Magha": "मघा", "Purva Phalguni": "पूर्वा फाल्गुनी",
    "Uttara Phalguni": "उत्तरा फाल्गुनी", "Hasta": "हस्त", "Chitra": "चित्रा",
    "Swati": "स्वाती", "Vishakha": "विशाखा", "Anuradha": "अनुराधा", "Jyeshtha": "ज्येष्ठा",
    "Mula": "मूल", "Purva Ashadha": "पूर्वाषाढ़ा", "Uttara Ashadha": "उत्तराषाढ़ा",
    "Shravana": "श्रवण", "Dhanishta": "धनिष्ठा", "Shatabhisha": "शतभिषा",
    "Purva Bhadrapada": "पूर्वाभाद्रपद", "Uttara Bhadrapada": "उत्तराभाद्रपद", "Revati": "रेवती",
}

PLANETS = {
    "Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु",
    "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु",
}

GANA = {"Deva": "देव", "Manushya": "मनुष्य", "Rakshasa": "राक्षस"}

YONI = {
    "Horse": "अश्व", "Elephant": "गज", "Sheep": "मेष (भेड़)", "Serpent": "सर्प", "Dog": "श्वान",
    "Cat": "मार्जार", "Rat": "मूषक", "Cow": "गौ", "Buffalo": "महिष", "Tiger": "व्याघ्र",
    "Deer": "मृग", "Monkey": "वानर", "Mongoose": "नकुल", "Lion": "सिंह",
}

VASHYA = {"Chatushpada": "चतुष्पद", "Manava": "मानव", "Jalachara": "जलचर",
          "Vanachara": "वनचर", "Keeta": "कीट"}

VARNA = {"Brahmin": "ब्राह्मण", "Kshatriya": "क्षत्रिय", "Vaishya": "वैश्य", "Shudra": "शूद्र"}

NADI = {"Adi (Vata)": "आदि (वात)", "Madhya (Pitta)": "मध्य (पित्त)", "Antya (Kapha)": "अन्त्य (कफ)"}

# The nine taras, counted from the birth star (1 = janma ... 9 = ati-mitra).
TARA = ["जन्म", "संपत", "विपत", "क्षेम", "प्रत्यरि", "साधक", "वध", "मित्र", "अति मित्र"]
TARA_INAUSPICIOUS = {3, 5, 7}

MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त",
          "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]

KOOTA = {  # engine name -> (Hindi name, max points)
    "Varna": ("वर्ण", 1), "Vashya": ("वश्य", 2), "Tara": ("तारा", 3), "Yoni": ("योनि", 4),
    "Graha Maitri": ("ग्रह मैत्री", 5), "Gana": ("गण", 6), "Bhakoot": ("भकूट", 7), "Nadi": ("नाड़ी", 8),
}

# Verdict bands on the 36-point total (the published Drik Panchang bands; the
# last label is softened from "अशुभ" to keep the tone non-alarming).
BANDS = [(31, "अति उत्तम"), (21, "उत्तम"), (17, "साधारण"), (0, "अल्प मेल")]


def band_label(total: float) -> str:
    for floor, label in BANDS:
        if total >= floor:
            return label
    return BANDS[-1][1]


def hi_date(d) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def fmt(n) -> str:
    """Score as plain digits; whole numbers without a decimal."""
    return str(int(n)) if float(n).is_integer() else f"{n:g}"
