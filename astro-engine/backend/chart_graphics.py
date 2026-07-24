"""
SVG chart graphics for the Arvelos report (WeasyPrint renders inline SVG).
North-Indian diamond chart, Western wheel, Lo Shu grid.
"""
from __future__ import annotations
import math

INK, DEEP, VIOLET, GOLD, PAPER = "#1a1333", "#2d1b52", "#43277a", "#c9b458", "#f6f3fc"

SIGN_GLYPH = {"Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋",
              "Leo": "♌", "Virgo": "♍", "Libra": "♎", "Scorpio": "♏",
              "Sagittarius": "♐", "Capricorn": "♑", "Aquarius": "♒",
              "Pisces": "♓"}
PLANET_ABBR = {"Sun": "Su", "Moon": "Mo", "Mercury": "Me", "Venus": "Ve",
               "Mars": "Ma", "Jupiter": "Ju", "Saturn": "Sa", "Rahu": "Ra",
               "Ketu": "Ke", "Uranus": "Ur", "Neptune": "Ne", "Pluto": "Pl",
               "Ascendant": "As"}
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def north_indian_chart(asc_sign_idx: int, placements: list, size=420) -> str:
    """placements: [(planet_name, sign_idx)]. Houses fixed; signs rotate."""
    s = size
    # house centres for the classic diamond layout (fractions of size)
    HC = [(.5, .25), (.25, .12), (.10, .25), (.25, .5), (.10, .75),
          (.25, .88), (.5, .75), (.75, .88), (.90, .75), (.75, .5),
          (.90, .25), (.75, .12)]
    by_house: dict[int, list[str]] = {}
    for name, sign_idx in placements:
        h = (sign_idx - asc_sign_idx) % 12
        by_house.setdefault(h, []).append(PLANET_ABBR.get(name, name[:2]))

    e = [f'<svg viewBox="0 0 {s} {s}" xmlns="http://www.w3.org/2000/svg">']
    e.append(f'<rect x="4" y="4" width="{s-8}" height="{s-8}" fill="{PAPER}" '
             f'stroke="{GOLD}" stroke-width="3"/>')
    e.append(f'<rect x="12" y="12" width="{s-24}" height="{s-24}" fill="none" '
             f'stroke="{VIOLET}" stroke-width="1.5"/>')
    # diagonals + inner diamond
    e.append(f'<line x1="12" y1="12" x2="{s-12}" y2="{s-12}" stroke="{VIOLET}" stroke-width="1.5"/>')
    e.append(f'<line x1="{s-12}" y1="12" x2="12" y2="{s-12}" stroke="{VIOLET}" stroke-width="1.5"/>')
    mid = s / 2
    e.append(f'<polygon points="{mid},12 {s-12},{mid} {mid},{s-12} 12,{mid}" '
             f'fill="none" stroke="{VIOLET}" stroke-width="1.5"/>')
    for h in range(12):
        cx, cy = HC[h][0] * s, HC[h][1] * s
        sign_no = (asc_sign_idx + h) % 12 + 1
        e.append(f'<text x="{cx}" y="{cy-14}" font-size="13" fill="{GOLD}" '
                 f'text-anchor="middle" font-weight="bold">{sign_no}</text>')
        planets = by_house.get(h, [])
        for i, p in enumerate(planets):
            row, col = divmod(i, 3)
            px = cx + (col - (min(len(planets),3)-1)/2 if len(planets) > 1 else 0) * 26
            px = cx + (col - 1) * 26 if len(planets) > 2 else cx + (col - (len(planets)-1)/2) * 26
            e.append(f'<text x="{px}" y="{cy+6+row*16}" font-size="14" '
                     f'fill="{INK}" text-anchor="middle">{p}</text>')
    e.append("</svg>")
    return "".join(e)


def western_wheel(placements: list, asc_lon: float | None, size=440) -> str:
    """placements: [(planet_name, longitude_deg)] tropical."""
    s = size
    c = s / 2
    r_outer, r_zod, r_pl = c - 6, c - 44, c - 92
    e = [f'<svg viewBox="0 0 {s} {s}" xmlns="http://www.w3.org/2000/svg">']
    e.append(f'<circle cx="{c}" cy="{c}" r="{r_outer}" fill="{DEEP}" stroke="{GOLD}" stroke-width="3"/>')
    e.append(f'<circle cx="{c}" cy="{c}" r="{r_zod}" fill="{PAPER}" stroke="{GOLD}" stroke-width="1.5"/>')
    e.append(f'<circle cx="{c}" cy="{c}" r="60" fill="{DEEP}" stroke="{GOLD}" stroke-width="1.5"/>')
    e.append(f'<text x="{c}" y="{c+6}" font-size="16" fill="{GOLD}" text-anchor="middle">✦</text>')

    rot = 180 - (asc_lon if asc_lon is not None else 0)  # Asc at left (9 o'clock)

    def xy(lon, r):
        a = math.radians((lon + rot) % 360)
        return c + r * math.cos(math.radians(180) - a), c - r * math.sin(math.radians(180) - a)

    def xy2(lon, r):  # standard: 0° Aries at Asc-rotated position, counterclockwise
        a = math.radians(180 + (lon + rot))
        return c + r * math.cos(a), c + r * math.sin(a)

    # sign boundaries + glyphs
    for i in range(12):
        lon = i * 30
        x1, y1 = xy2(lon, r_zod)
        x2, y2 = xy2(lon, r_outer)
        e.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{GOLD}" stroke-width="1"/>')
        gx, gy = xy2(lon + 15, (r_outer + r_zod) / 2)
        e.append(f'<text x="{gx:.1f}" y="{gy+6:.1f}" font-size="19" fill="{GOLD}" '
                 f'text-anchor="middle">{SIGN_GLYPH[SIGNS[i]]}</text>')
    # planets
    slots: list[float] = []
    for name, lon in placements:
        adj = lon
        while any(abs((adj - u + 180) % 360 - 180) < 9 for u in slots):
            adj += 9
        slots.append(adj)
        px, py = xy2(adj, r_pl)
        tx, ty = xy2(adj, r_pl - 34)
        dx, dy = xy2(lon, r_zod)
        e.append(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="3" fill="{VIOLET}"/>')
        e.append(f'<line x1="{dx:.1f}" y1="{dy:.1f}" x2="{px:.1f}" y2="{py:.1f}" stroke="{VIOLET}" stroke-width="0.7" opacity="0.5"/>')
        e.append(f'<text x="{px:.1f}" y="{py+5:.1f}" font-size="13" fill="{INK}" '
                 f'text-anchor="middle" font-weight="bold">{PLANET_ABBR.get(name,name[:2])}</text>')
    if asc_lon is not None:
        ax, ay = xy2(asc_lon, r_zod)
        e.append(f'<text x="{ax:.1f}" y="{ay:.1f}" font-size="12" fill="#b03030" '
                 f'text-anchor="middle" font-weight="bold">ASC</text>')
    e.append("</svg>")
    return "".join(e)


def lo_shu_svg(counts: dict[int, int], size=300) -> str:
    try:
        from .numerology import LO_SHU_POSITIONS, LO_SHU_ELEMENT
    except ImportError:
        from numerology import LO_SHU_POSITIONS, LO_SHU_ELEMENT
    s, cell = size, size / 3
    e = [f'<svg viewBox="0 0 {s} {s+8}" xmlns="http://www.w3.org/2000/svg">']
    for n, (row, col) in LO_SHU_POSITIONS.items():
        x, y = col * cell, row * cell
        cnt = counts.get(n, 0)
        fill = PAPER if cnt else "#eae5f5"
        e.append(f'<rect x="{x+2}" y="{y+2}" width="{cell-4}" height="{cell-4}" '
                 f'fill="{fill}" stroke="{GOLD}" stroke-width="2" rx="6"/>')
        txt = " ".join([str(n)] * cnt) if cnt else "—"
        e.append(f'<text x="{x+cell/2}" y="{y+cell/2+2}" font-size="{20 if cnt else 16}" '
                 f'fill="{INK if cnt else "#9b90c4"}" text-anchor="middle" '
                 f'font-weight="bold">{txt}</text>')
        e.append(f'<text x="{x+cell/2}" y="{y+cell-12}" font-size="10.5" '
                 f'fill="{VIOLET}" text-anchor="middle">{LO_SHU_ELEMENT[n]}</text>')
    e.append("</svg>")
    return "".join(e)


def cover_zodiac_ring(size=460) -> str:
    """Decorative ring of zodiac glyphs with a radiant sun + crescent moon
    emblem in the center."""
    s, c, r = size, size / 2, size / 2 - 34
    e = [f'<svg viewBox="0 0 {s} {s}" xmlns="http://www.w3.org/2000/svg">']
    e.append(f'<circle cx="{c}" cy="{c}" r="{r+22}" fill="none" stroke="{GOLD}" stroke-width="1.4" opacity="0.9"/>')
    e.append(f'<circle cx="{c}" cy="{c}" r="{r-24}" fill="none" stroke="{GOLD}" stroke-width="0.8" opacity="0.7"/>')
    for i, sign in enumerate(SIGNS):
        a = math.radians(i * 30 - 90)
        x, y = c + r * math.cos(a), c + r * math.sin(a)
        e.append(f'<text x="{x:.1f}" y="{y+8:.1f}" font-size="24" fill="{GOLD}" '
                 f'text-anchor="middle">{SIGN_GLYPH[sign]}</text>')
        # small star between glyphs
        a2 = math.radians(i * 30 - 75)
        sx, sy = c + (r + 1) * math.cos(a2), c + (r + 1) * math.sin(a2)
        e.append(f'<text x="{sx:.1f}" y="{sy+4:.1f}" font-size="9" fill="{GOLD}" '
                 f'text-anchor="middle" opacity="0.8">✦</text>')
    # --- center emblem: Eclipse Duality (half sun / half moon, art deco) ---
    e.append(_eclipse_duality_emblem(c))
    e.append("</svg>")
    return "".join(e)


def _rot(px, py, ang, cx=0.0, cy=0.0):
    ca, sa = math.cos(ang), math.sin(ang)
    return cx + px * ca - py * sa, cy + px * sa + py * ca


def _flame_ray(cx, cy, ang, r0, r1, width) -> str:
    b1 = _rot(r0, -width, ang, cx, cy)
    b2 = _rot(r0, width, ang, cx, cy)
    m1 = _rot((r0 + r1) / 2, -width * 1.6, ang, cx, cy)
    m2 = _rot((r0 + r1) / 2, width * 0.2, ang, cx, cy)
    tip = _rot(r1, 0, ang, cx, cy)
    return (f'M {b1[0]:.1f} {b1[1]:.1f} '
            f'Q {m1[0]:.1f} {m1[1]:.1f} {tip[0]:.1f} {tip[1]:.1f} '
            f'Q {m2[0]:.1f} {m2[1]:.1f} {b2[0]:.1f} {b2[1]:.1f} Z')


def _taper_ray(cx, cy, ang, r0, r1, width) -> str:
    b1 = _rot(r0, -width, ang, cx, cy)
    b2 = _rot(r0, width, ang, cx, cy)
    tip = _rot(r1, 0, ang, cx, cy)
    return (f'M {b1[0]:.1f} {b1[1]:.1f} L {tip[0]:.1f} {tip[1]:.1f} '
            f'L {b2[0]:.1f} {b2[1]:.1f} Z')


def _sparkle(x, y, r) -> str:
    return (f'<path d="M {x} {y-r} Q {x+r*0.18} {y-r*0.18} {x+r} {y} '
            f'Q {x+r*0.18} {y+r*0.18} {x} {y+r} '
            f'Q {x-r*0.18} {y+r*0.18} {x-r} {y} '
            f'Q {x-r*0.18} {y-r*0.18} {x} {y-r} Z" fill="{GOLD}"/>')


def _eclipse_duality_emblem(C: float) -> str:
    """Art-deco half-sun / half-moon split disc (chosen cover emblem)."""
    e = []
    R = 84
    for i in range(7):
        ang = math.radians(90 + i * 30)
        e.append(f'<path d="{_flame_ray(C, C, ang, R + 4, R + 52, 8)}" fill="{GOLD}"/>')
    for i in range(6):
        ang = math.radians(105 + i * 30)
        e.append(f'<path d="{_taper_ray(C, C, ang, R + 4, R + 38, 3)}" fill="{GOLD}" opacity="0.85"/>')
    pts = [(74, -66, 3.2), (98, -20, 2.0), (108, 30, 2.6), (80, 66, 1.8),
           (122, -52, 1.6), (128, 8, 1.8), (112, 62, 2.0)]
    for dx, dy, r in pts:
        if r > 2.4:
            e.append(_sparkle(C + dx, C + dy, r * 3.2))
        else:
            e.append(f'<circle cx="{C+dx}" cy="{C+dy}" r="{r}" fill="{GOLD}" opacity="0.9"/>')
    e.append(f'<circle cx="{C}" cy="{C}" r="{R}" fill="none" stroke="{GOLD}" stroke-width="2.6"/>')
    e.append(f'<path d="M {C} {C-R} A {R} {R} 0 0 0 {C} {C+R} Z" fill="{GOLD}"/>')
    for k in range(1, 5):
        rr = R - k * 16
        e.append(f'<path d="M {C} {C-rr} A {rr} {rr} 0 0 0 {C} {C+rr}" '
                 f'fill="none" stroke="{DEEP}" stroke-width="1.2" opacity="0.4"/>')
    e.append(f'<path d="M {C} {C-R} A {R} {R} 0 0 1 {C} {C+R}" fill="none" stroke="{GOLD}" stroke-width="2.6"/>')
    for dx, dy, r in [(34, -34, 9), (52, 10, 6), (30, 42, 7), (58, -16, 3.5)]:
        e.append(f'<circle cx="{C+dx}" cy="{C+dy}" r="{r}" fill="none" '
                 f'stroke="{GOLD}" stroke-width="1.4" opacity="0.85"/>')
    e.append(f'<line x1="{C}" y1="{C-R}" x2="{C}" y2="{C+R}" stroke="{GOLD}" stroke-width="1.6"/>')
    return "".join(e)
