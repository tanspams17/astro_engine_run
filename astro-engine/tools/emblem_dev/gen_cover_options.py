"""Render 4 cover center-emblem options for Raj to choose from."""
import math
from chart_graphics import SIGN_GLYPH, SIGNS

GOLD = "#c9b458"


def ring_with_center(center_svg: str, size=460) -> str:
    s, c, r = size, size / 2, size / 2 - 34
    e = [f'<svg viewBox="0 0 {s} {s}" xmlns="http://www.w3.org/2000/svg">']
    e.append(f'<circle cx="{c}" cy="{c}" r="{r+22}" fill="none" stroke="{GOLD}" stroke-width="1.4"/>')
    e.append(f'<circle cx="{c}" cy="{c}" r="{r-24}" fill="none" stroke="{GOLD}" stroke-width="0.8" opacity="0.7"/>')
    for i, sign in enumerate(SIGNS):
        a = math.radians(i * 30 - 90)
        x, y = c + r * math.cos(a), c + r * math.sin(a)
        e.append(f'<text x="{x:.0f}" y="{y+8:.0f}" font-size="24" fill="{GOLD}" text-anchor="middle">{SIGN_GLYPH[sign]}</text>')
        a2 = math.radians(i * 30 - 75)
        sx, sy = c + (r + 1) * math.cos(a2), c + (r + 1) * math.sin(a2)
        e.append(f'<text x="{sx:.0f}" y="{sy+4:.0f}" font-size="9" fill="{GOLD}" text-anchor="middle" opacity="0.8">✦</text>')
    e.append(center_svg)
    e.append("</svg>")
    return "".join(e)


C = 230  # center


def opt_a_sun_moon() -> str:
    """A: celestial sun + crescent emblem."""
    e = []
    # sun rays
    for i in range(16):
        a = math.radians(i * 22.5)
        x1, y1 = C + 58 * math.cos(a), C + 58 * math.sin(a)
        x2, y2 = C + (78 if i % 2 == 0 else 70) * math.cos(a), C + (78 if i % 2 == 0 else 70) * math.sin(a)
        e.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{GOLD}" stroke-width="2"/>')
    e.append(f'<circle cx="{C}" cy="{C}" r="52" fill="none" stroke="{GOLD}" stroke-width="2.2"/>')
    # crescent inside
    e.append(f'<path d="M {C+20} {C-30} A 38 38 0 1 0 {C+20} {C+30} A 30 30 0 1 1 {C+20} {C-30} Z" fill="{GOLD}" opacity="0.9"/>')
    e.append(f'<circle cx="{C-14}" cy="{C-6}" r="3" fill="{GOLD}"/>')
    e.append(f'<circle cx="{C-4}" cy="{C+14}" r="2" fill="{GOLD}"/>')
    return "".join(e)


def opt_b_glyph_trio(sun="Libra", moon="Taurus", asc="Sagittarius") -> str:
    """B: big sun glyph, smaller moon + rising."""
    e = [f'<circle cx="{C}" cy="{C}" r="78" fill="none" stroke="{GOLD}" stroke-width="1.2" opacity="0.8"/>']
    e.append(f'<text x="{C}" y="{C+8}" font-size="76" fill="{GOLD}" text-anchor="middle">{SIGN_GLYPH[sun]}</text>')
    e.append(f'<text x="{C-52}" y="{C+62}" font-size="30" fill="{GOLD}" text-anchor="middle" opacity="0.85">{SIGN_GLYPH[moon]}</text>')
    e.append(f'<text x="{C+52}" y="{C+62}" font-size="30" fill="{GOLD}" text-anchor="middle" opacity="0.85">{SIGN_GLYPH[asc]}</text>')
    e.append(f'<text x="{C}" y="{C-58}" font-size="12" fill="{GOLD}" text-anchor="middle" opacity="0.7">✦ ✦ ✦</text>')
    return "".join(e)


def opt_c_mandala() -> str:
    """C: sacred-geometry eight-pointed star mandala."""
    e = []
    for rot in (0, 45):
        pts = []
        for i in range(4):
            a = math.radians(i * 90 + rot)
            pts.append(f"{C + 74 * math.cos(a):.0f},{C + 74 * math.sin(a):.0f}")
        # diamond
        e.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="{GOLD}" stroke-width="1.8"/>')
    e.append(f'<circle cx="{C}" cy="{C}" r="46" fill="none" stroke="{GOLD}" stroke-width="1"/>')
    e.append(f'<circle cx="{C}" cy="{C}" r="30" fill="none" stroke="{GOLD}" stroke-width="0.8" opacity="0.8"/>')
    for i in range(8):
        a = math.radians(i * 45 + 22.5)
        x, y = C + 38 * math.cos(a), C + 38 * math.sin(a)
        e.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="2" fill="{GOLD}"/>')
    e.append(f'<text x="{C}" y="{C+10}" font-size="30" fill="{GOLD}" text-anchor="middle">✦</text>')
    return "".join(e)


def opt_d_kundali_motif() -> str:
    """D: decorative empty diamond-kundali pattern (astrology motif, no data)."""
    s = 130  # half-size of square
    e = [f'<rect x="{C-s}" y="{C-s}" width="{2*s}" height="{2*s}" fill="none" stroke="{GOLD}" stroke-width="2"/>']
    e.append(f'<line x1="{C-s}" y1="{C-s}" x2="{C+s}" y2="{C+s}" stroke="{GOLD}" stroke-width="1.2"/>')
    e.append(f'<line x1="{C+s}" y1="{C-s}" x2="{C-s}" y2="{C+s}" stroke="{GOLD}" stroke-width="1.2"/>')
    e.append(f'<polygon points="{C},{C-s} {C+s},{C} {C},{C+s} {C-s},{C}" fill="none" stroke="{GOLD}" stroke-width="1.2"/>')
    e.append(f'<text x="{C}" y="{C+9}" font-size="26" fill="{GOLD}" text-anchor="middle">ॐ</text>')
    return "".join(e)


COVER_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 0; }}
body {{ margin:0; font-family: Georgia, serif; }}
.cover {{ width: 210mm; height: 297mm; position: relative;
  background: radial-gradient(ellipse at 50% 30%, #43277a 0%, #2d1b52 45%, #1a1333 100%);
  color: #f3eefe; }}
.f1 {{ position:absolute; top:8mm; left:8mm; right:8mm; bottom:8mm; border:2px solid #c9b458; }}
.f2 {{ position:absolute; top:11mm; left:11mm; right:11mm; bottom:11mm; border:0.7px solid #c9b458; }}
.in {{ position:absolute; top:20mm; left:0; right:0; text-align:center; }}
.brand {{ font-size:12pt; letter-spacing:8px; color:#c9b458; }}
.om {{ font-size:10pt; color:#9d90c4; margin-top:4mm; letter-spacing:2px; }}
h1 {{ font-size:34pt; font-weight:normal; color:#f8f5ff; margin:10mm 0 2mm; line-height:1.1; }}
.sub {{ font-size:13pt; letter-spacing:4px; color:#c9b458; text-transform:uppercase; }}
.ring {{ margin:8mm auto 6mm; width:108mm; }}
.plq {{ display:inline-block; border:1.6px solid #c9b458; border-radius:20px; padding:4mm 16mm; }}
.plq .n {{ font-size:19pt; color:#fff; }} .plq .b {{ font-size:10.5pt; color:#cfc4ec; margin-top:1.5mm; }}
.b3 {{ margin-top:7mm; font-size:11.5pt; color:#c9b458; }}
.ft {{ position:absolute; bottom:15mm; left:0; right:0; text-align:center; font-size:9.5pt; color:#9d90c4; }}
</style></head><body><div class="cover"><div class="f1"></div><div class="f2"></div>
<div class="in"><div class="brand">A R V E L O S</div>
<div class="om">॥ Your Sky · Your Numbers · Your Year Ahead ॥</div>
<h1>Fortune &amp; Birth Chart<br>Report</h1>
<div class="sub">Mixed Report — Western + Vedic</div>
<div class="ring">{ring}</div>
<div class="plq"><div class="n">Pamit Raj</div><div class="b">16 October 1992, 10:30 — Patna, India</div></div>
<div class="b3">Sagittarius Rising · Libra Sun · Taurus Moon · Mulank 7 · Bhagyank 2</div></div>
<div class="ft">Individually calculated · arvelos.cloud<br>One report, one payment — no subscription.</div>
</div></body></html>"""

if __name__ == "__main__":
    from weasyprint import HTML
    opts = {"A_sun_moon_emblem": opt_a_sun_moon(),
            "B_sign_glyph_trio": opt_b_glyph_trio(),
            "C_star_mandala": opt_c_mandala(),
            "D_kundali_motif": opt_d_kundali_motif()}
    for name, center in opts.items():
        html = COVER_HTML.format(ring=ring_with_center(center))
        HTML(string=html).write_pdf(f"/tmp/cover_{name}.pdf")
        print(name)
