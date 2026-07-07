"""Three professional-grade celestial emblems (tarot/boho/art-deco genre)
for the Arvelos cover center. Renders each inside the real cover for review.
"""
import math
from gen_cover_options import COVER_HTML, ring_with_center

GOLD = "#c9b458"
GOLD_SOFT = "#d8c777"
C = 230


def _rot(px, py, ang, cx=0, cy=0):
    ca, sa = math.cos(ang), math.sin(ang)
    return cx + px * ca - py * sa, cy + px * sa + py * ca


def flame_ray(cx, cy, ang, r0, r1, width) -> str:
    """Tapered S-curved flame ray as a filled path (tarot style)."""
    pts = []
    b1 = _rot(r0, -width, ang, cx, cy)
    b2 = _rot(r0, width, ang, cx, cy)
    m1 = _rot((r0 + r1) / 2, -width * 1.6, ang, cx, cy)
    m2 = _rot((r0 + r1) / 2, width * 0.2, ang, cx, cy)
    tip = _rot(r1, 0, ang, cx, cy)
    return (f'M {b1[0]:.1f} {b1[1]:.1f} '
            f'Q {m1[0]:.1f} {m1[1]:.1f} {tip[0]:.1f} {tip[1]:.1f} '
            f'Q {m2[0]:.1f} {m2[1]:.1f} {b2[0]:.1f} {b2[1]:.1f} Z')


def taper_ray(cx, cy, ang, r0, r1, width) -> str:
    """Straight tapered spike as filled triangle."""
    b1 = _rot(r0, -width, ang, cx, cy)
    b2 = _rot(r0, width, ang, cx, cy)
    tip = _rot(r1, 0, ang, cx, cy)
    return (f'M {b1[0]:.1f} {b1[1]:.1f} L {tip[0]:.1f} {tip[1]:.1f} '
            f'L {b2[0]:.1f} {b2[1]:.1f} Z')


def serene_face(cx, cy, scale=1.0, color=None) -> str:
    """Closed eyes with lashes, nose, soft lips — boho moon-face style.
    Drawn in the DARK background colour so it engraves into gold fill."""
    col = color or "#2d1b52"
    s = scale
    e = []
    for side in (-1, 1):
        ex = cx + side * 16 * s
        # closed eye: gentle downward arc
        e.append(f'<path d="M {ex-8*s:.1f} {cy-6*s:.1f} Q {ex:.1f} {cy+1*s:.1f} '
                 f'{ex+8*s:.1f} {cy-6*s:.1f}" stroke="{col}" '
                 f'stroke-width="{2.2*s:.1f}" fill="none" stroke-linecap="round"/>')
        # brow
        e.append(f'<path d="M {ex-9*s:.1f} {cy-13*s:.1f} Q {ex:.1f} {cy-18*s:.1f} '
                 f'{ex+9*s:.1f} {cy-13*s:.1f}" stroke="{col}" '
                 f'stroke-width="{1.6*s:.1f}" fill="none" stroke-linecap="round"/>')
        # three tiny lashes
        for k in (-4, 0, 4):
            lx = ex + k * s
            e.append(f'<line x1="{lx:.1f}" y1="{cy-2*s:.1f}" x2="{lx:.1f}" '
                     f'y2="{cy+3*s:.1f}" stroke="{col}" '
                     f'stroke-width="{1.2*s:.1f}" stroke-linecap="round"/>')
    # nose
    e.append(f'<path d="M {cx:.1f} {cy+2*s:.1f} Q {cx-2*s:.1f} {cy+10*s:.1f} '
             f'{cx+2*s:.1f} {cy+11*s:.1f}" stroke="{col}" '
             f'stroke-width="{1.8*s:.1f}" fill="none" stroke-linecap="round"/>')
    # lips
    e.append(f'<path d="M {cx-6*s:.1f} {cy+19*s:.1f} Q {cx:.1f} {cy+24*s:.1f} '
             f'{cx+6*s:.1f} {cy+19*s:.1f}" stroke="{col}" '
             f'stroke-width="{2*s:.1f}" fill="none" stroke-linecap="round"/>')
    return "".join(e)


def sparkle(x, y, r, col=GOLD) -> str:
    """Four-point star sparkle."""
    return (f'<path d="M {x} {y-r} Q {x+r*0.18} {y-r*0.18} {x+r} {y} '
            f'Q {x+r*0.18} {y+r*0.18} {x} {y+r} '
            f'Q {x-r*0.18} {y+r*0.18} {x-r} {y} '
            f'Q {x-r*0.18} {y-r*0.18} {x} {y-r} Z" fill="{col}"/>')


# ================================================================ 1. TAROT SUN


def emblem_tarot_sun_moon() -> str:
    """Full sun disc with serene face, alternating flame + straight rays,
    stipple ring — classic tarot 'The Sun' treatment."""
    e = []
    # rays
    for i in range(12):
        ang = math.radians(i * 30 - 90)
        e.append(f'<path d="{flame_ray(C, C, ang, 86, 138, 9)}" fill="{GOLD}"/>')
    for i in range(12):
        ang = math.radians(i * 30 - 75)
        e.append(f'<path d="{taper_ray(C, C, ang, 86, 120, 3.4)}" fill="{GOLD}" opacity="0.85"/>')
    # stipple dots between rays
    for i in range(24):
        ang = math.radians(i * 15 - 82.5)
        x, y = _rot(126, 0, ang, C, C)
        e.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.6" fill="{GOLD}" opacity="0.75"/>')
    # sun disc: double ring + engraved inner circle
    e.append(f'<circle cx="{C}" cy="{C}" r="82" fill="{GOLD}"/>')
    e.append(f'<circle cx="{C}" cy="{C}" r="82" fill="none" stroke="#2d1b52" stroke-width="1.4" opacity="0.35"/>')
    e.append(f'<circle cx="{C}" cy="{C}" r="74" fill="none" stroke="#2d1b52" stroke-width="1.1" opacity="0.45"/>')
    # face engraved in background colour
    e.append(serene_face(C, C - 4, scale=1.5))
    # cheek dots
    for sx in (-1, 1):
        e.append(f'<circle cx="{C+sx*30:.0f}" cy="{C+22:.0f}" r="2.6" fill="#2d1b52" opacity="0.5"/>')
    return "".join(e)


# ================================================================ 2. ECLIPSE


def emblem_eclipse_duality() -> str:
    """Art-deco half-sun / half-moon split disc: engraved ray lines on the
    sun side, craters + stars on the moon side."""
    e = []
    R = 84
    # sun-side rays (left half only) — alternating flame + taper
    for i in range(7):
        ang = math.radians(90 + i * 30)
        e.append(f'<path d="{flame_ray(C, C, ang, R + 4, R + 52, 8)}" fill="{GOLD}"/>')
    for i in range(6):
        ang = math.radians(105 + i * 30)
        e.append(f'<path d="{taper_ray(C, C, ang, R + 4, R + 38, 3)}" fill="{GOLD}" opacity="0.85"/>')
    # moon-side scattered stars + sparkles (right half)
    pts = [(74, -66, 3.2), (98, -20, 2.0), (108, 30, 2.6), (80, 66, 1.8),
           (122, -52, 1.6), (128, 8, 1.8), (112, 62, 2.0)]
    for dx, dy, r in pts:
        if r > 2.4:
            e.append(sparkle(C + dx, C + dy, r * 3.2))
        else:
            e.append(f'<circle cx="{C+dx}" cy="{C+dy}" r="{r}" fill="{GOLD}" opacity="0.9"/>')
    # disc outline
    e.append(f'<circle cx="{C}" cy="{C}" r="{R}" fill="none" stroke="{GOLD}" stroke-width="2.6"/>')
    # left half filled (sun)
    e.append(f'<path d="M {C} {C-R} A {R} {R} 0 0 0 {C} {C+R} Z" fill="{GOLD}"/>')
    # engraved arcs inside sun half (deco lines)
    for k in range(1, 5):
        rr = R - k * 16
        e.append(f'<path d="M {C} {C-rr} A {rr} {rr} 0 0 0 {C} {C+rr}" '
                 f'fill="none" stroke="#2d1b52" stroke-width="1.2" opacity="0.4"/>')
    # moon half: crescent line + craters
    e.append(f'<path d="M {C} {C-R} A {R} {R} 0 0 1 {C} {C+R}" fill="none" stroke="{GOLD}" stroke-width="2.6"/>')
    for dx, dy, r in [(34, -34, 9), (52, 10, 6), (30, 42, 7), (58, -16, 3.5)]:
        e.append(f'<circle cx="{C+dx}" cy="{C+dy}" r="{r}" fill="none" '
                 f'stroke="{GOLD}" stroke-width="1.4" opacity="0.85"/>')
    # split line
    e.append(f'<line x1="{C}" y1="{C-R}" x2="{C}" y2="{C+R}" stroke="{GOLD}" stroke-width="1.6"/>')
    return "".join(e)


# ============================================================ 3. BOHO CRESCENT


def emblem_boho_crescent() -> str:
    """Fine-line boho medallion: ornate crescent with face cradling a small
    radiant star, dotted orbit ring, sparkles, stipple shading."""
    e = []
    # dotted orbit ring
    for i in range(48):
        ang = math.radians(i * 7.5)
        x, y = _rot(128, 0, ang, C, C)
        e.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.3" fill="{GOLD}" opacity="0.8"/>')
    # fine tapered rays outside the dotted ring at 8 compass points
    for i in range(8):
        ang = math.radians(i * 45 - 90)
        e.append(f'<path d="{taper_ray(C, C, ang, 134, 152, 2.4)}" fill="{GOLD}"/>')
    # crescent: large, opening to the right
    e.append(f'<path d="M {C+34} {C-72} A 80 80 0 1 0 {C+34} {C+72} '
             f'A 62 62 0 1 1 {C+34} {C-72} Z" fill="{GOLD}"/>')
    # stipple shading along crescent inner edge
    for i in range(14):
        t = -70 + i * 10.8
        ang = math.radians(t)
        x = C + 34 - 8 + 56 * math.cos(math.radians(180 - t * 0.9)) * 0.28
        y = C + 62 * math.sin(ang) * 0.92
        e.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.4" fill="#2d1b52" opacity="0.45"/>')
    # face on the crescent body
    e.append(serene_face(C - 34, C - 6, scale=1.05))
    # small radiant star cradled in the crescent's opening
    sx, sy = C + 52, C
    for i in range(8):
        ang = math.radians(i * 45)
        e.append(f'<path d="{taper_ray(sx, sy, ang, 12, 26 if i % 2 == 0 else 20, 2.2)}" fill="{GOLD}"/>')
    e.append(f'<circle cx="{sx}" cy="{sy}" r="10" fill="{GOLD}"/>')
    e.append(f'<circle cx="{sx}" cy="{sy}" r="10" fill="none" stroke="#2d1b52" stroke-width="1" opacity="0.4"/>')
    # sparkles
    e.append(sparkle(C + 88, C - 62, 9))
    e.append(sparkle(C + 96, C + 58, 7))
    e.append(sparkle(C - 6, C - 108, 6))
    return "".join(e)


if __name__ == "__main__":
    from weasyprint import HTML
    opts = {"1_tarot_sun": emblem_tarot_sun_moon(),
            "2_eclipse_duality": emblem_eclipse_duality(),
            "3_boho_crescent": emblem_boho_crescent()}
    for name, center in opts.items():
        HTML(string=COVER_HTML.format(ring=ring_with_center(center))
             ).write_pdf(f"/tmp/emblem_{name}.pdf")
        print(name)
