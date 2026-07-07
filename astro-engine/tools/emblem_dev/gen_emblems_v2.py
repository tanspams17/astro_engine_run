"""
Gilded Firmament — polished celestial emblems, PIL-rendered with metallic
gradients, rim light, glow and engraving. Supersampled 3x for crispness.
Outputs transparent PNGs + cover mockups.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 3                       # supersample factor
S = 600                      # final emblem size
W = S * SS                   # working size
C = W // 2

# metallic palette (light source upper-left)
CHAMPAGNE = (242, 230, 184)
HONEY = (201, 180, 88)
BRONZE = (138, 112, 40)
NIGHT = (45, 27, 82)
INK = (26, 19, 51)


def metal_gradient(size, angle_deg=135):
    """Linear champagne->honey->bronze gradient array (RGBA, opaque)."""
    y, x = np.mgrid[0:size, 0:size].astype(float)
    a = math.radians(angle_deg)
    t = (x * math.cos(a) + y * math.sin(a)) / (size * abs(math.cos(a)) + size * abs(math.sin(a)))
    t = (t - t.min()) / (t.max() - t.min())
    img = np.zeros((size, size, 4), dtype=np.uint8)
    for i, (c0, c1, lo, hi) in enumerate([
            (CHAMPAGNE, HONEY, 0.0, 0.55), (HONEY, BRONZE, 0.55, 1.0)]):
        m = (t >= lo) & (t <= hi)
        tt = (t - lo) / (hi - lo)
        for ch in range(3):
            vals = c0[ch] + (c1[ch] - c0[ch]) * tt
            img[..., ch] = np.where(m, vals.astype(np.uint8), img[..., ch])
    img[..., 3] = 255
    return Image.fromarray(img, "RGBA")


GRAD = metal_gradient(W)


def gold_fill(mask: Image.Image) -> Image.Image:
    """Apply metallic gradient through a mask."""
    out = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    out.paste(GRAD, (0, 0), mask)
    return out


def new_mask():
    m = Image.new("L", (W, W), 0)
    return m, ImageDraw.Draw(m)


def rot(px, py, ang, cx=C, cy=C):
    ca, sa = math.cos(ang), math.sin(ang)
    return cx + px * ca - py * sa, cy + px * sa + py * ca


def taper_poly(d, ang, r0, r1, w0, w1=0.0):
    p = [rot(r0, -w0, ang), rot(r1, -w1, ang), rot(r1, w1, ang), rot(r0, w0, ang)]
    d.polygon(p, fill=255)


def flame_poly(d, ang, r0, r1, w):
    """Curved flame ray approximated with many points."""
    pts = []
    n = 14
    for i in range(n + 1):
        t = i / n
        r = r0 + (r1 - r0) * t
        off = -w * math.sin(math.pi * t) * (1 - t * 0.4) - w * (1 - t)
        pts.append(rot(r, off, ang))
    for i in range(n + 1):
        t = 1 - i / n
        r = r0 + (r1 - r0) * t
        off = w * (1 - t) * math.cos(t * 1.2)
        pts.append(rot(r, off, ang))
    d.polygon(pts, fill=255)


def star4(d, x, y, r, thin=0.16):
    pts = []
    for i in range(8):
        ang = i * math.pi / 4
        rr = r if i % 2 == 0 else r * thin
        pts.append((x + rr * math.cos(ang), y + rr * math.sin(ang)))
    d.polygon(pts, fill=255)


def glow_layer(mask, radius, alpha):
    g = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    tint = Image.new("RGBA", (W, W), HONEY + (alpha,))
    g.paste(tint, (0, 0), mask)
    return g.filter(ImageFilter.GaussianBlur(radius))


def canvas():
    return Image.new("RGBA", (W, W), (0, 0, 0, 0))


def ring_mask(d, r, width):
    d.ellipse([C - r, C - r, C + r, C + r], fill=255)
    d.ellipse([C - r + width, C - r + width, C + r - width, C + r - width], fill=0)


# ============================================================ A. GILDED ECLIPSE
def emblem_A():
    img = canvas()
    R = int(W * 0.235)

    # --- glow behind everything
    gm, gd = new_mask()
    gd.ellipse([C - R * 1.15, C - R * 1.15, C + R * 1.15, C + R * 1.15], fill=255)
    img.alpha_composite(glow_layer(gm, W * 0.045, 110))

    # --- sunburst on left half: 11 flame rays + hairlines
    fm, fd = new_mask()
    for i in range(11):
        ang = math.radians(99 + i * 16.2)
        flame_poly(fd, ang, R * 1.06, R * 1.62 if i % 2 == 0 else R * 1.45, W * 0.011)
    img.alpha_composite(gold_fill(fm))
    hm, hd = new_mask()
    for i in range(22):
        ang = math.radians(95 + i * 8.1)
        taper_poly(hd, ang, R * 1.06, R * 1.30, W * 0.0022)
    img.alpha_composite(gold_fill(hm))

    # --- right half: stars + sparkles
    sm, sd = new_mask()
    stars = [(0.62, -0.55, 0.045), (0.88, -0.16, 0.028), (0.95, 0.28, 0.038),
             (0.66, 0.58, 0.024), (1.12, -0.44, 0.018), (1.16, 0.10, 0.02)]
    for dx, dy, r in stars:
        star4(sd, C + dx * R, C + dy * R, r * W)
    for dx, dy, r in [(0.78, -0.72, 0.005), (1.05, 0.48, 0.004), (0.95, -0.62, 0.0035)]:
        x, y, rr = C + dx * R, C + dy * R, r * W
        sd.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
    img.alpha_composite(gold_fill(sm))

    # --- disc: left half solid metal, right half night with gold rim
    dm, dd = new_mask()
    dd.pieslice([C - R, C - R, C + R, C + R], 90, 270, fill=255)
    img.alpha_composite(gold_fill(dm))
    # engraved concentric arcs on the sun half (night-coloured hairlines)
    eng = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ed = ImageDraw.Draw(eng)
    for k in range(1, 6):
        rr = R - k * R // 6
        ed.arc([C - rr, C - rr, C + rr, C + rr], 92, 268,
               fill=NIGHT + (150,), width=max(2, W // 700))
    img.alpha_composite(eng)

    # right half rim (metal ring clipped to right side)
    rm, rd = new_mask()
    ring_mask(rd, R, max(4, W // 260))
    clip = Image.new("L", (W, W), 0)
    ImageDraw.Draw(clip).rectangle([C, 0, W, W], fill=255)
    rm = Image.composite(rm, Image.new("L", (W, W), 0), clip)
    img.alpha_composite(gold_fill(rm))

    # moon craters: thin gold circles, gradient-filled crescents
    cm, cd = new_mask()
    craters = [(0.38, -0.38, 0.105), (0.60, 0.13, 0.068), (0.33, 0.50, 0.082), (0.68, -0.20, 0.04)]
    for dx, dy, r in craters:
        x, y, rr = C + dx * R, C + dy * R, r * R * 2.2
        cd.ellipse([x - rr, y - rr, x + rr, y + rr], outline=255,
                   width=max(3, W // 500))
    img.alpha_composite(gold_fill(cm))

    # full outer rim + split line
    om, od = new_mask()
    ring_mask(od, R + max(4, W // 260), max(5, W // 220))
    od.rectangle([C - W // 400, C - R, C + W // 400, C + R], fill=255)
    img.alpha_composite(gold_fill(om))

    # rim light: bright arc upper-left, dark arc lower-right
    rim = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    rd2 = ImageDraw.Draw(rim)
    rd2.arc([C - R, C - R, C + R, C + R], 160, 240, fill=CHAMPAGNE + (230,),
            width=max(3, W // 400))
    rd2.arc([C - R, C - R, C + R, C + R], 20, 70, fill=BRONZE + (200,),
            width=max(3, W // 400))
    img.alpha_composite(rim)
    return img


# ============================================================ B. SOLAR DIADEM
def emblem_B():
    img = canvas()
    R = int(W * 0.16)

    gm, gd = new_mask()
    gd.ellipse([C - R * 2.1, C - R * 2.1, C + R * 2.1, C + R * 2.1], fill=255)
    img.alpha_composite(glow_layer(gm, W * 0.05, 90))

    # 16 metallic flame rays
    fm, fd = new_mask()
    for i in range(16):
        ang = math.radians(i * 22.5 - 90)
        flame_poly(fd, ang, R * 1.32, R * 2.55 if i % 2 == 0 else R * 2.1, W * 0.012)
    img.alpha_composite(gold_fill(fm))
    # 32 hairline rays
    hm, hd = new_mask()
    for i in range(32):
        ang = math.radians(i * 11.25 - 84.4)
        taper_poly(hd, ang, R * 1.32, R * 1.78, W * 0.0018)
    img.alpha_composite(gold_fill(hm))
    # dotted halo
    dm2, dd2 = new_mask()
    for i in range(64):
        ang = math.radians(i * 5.625)
        x, y = rot(R * 2.75, 0, ang)
        rr = W * 0.0035 if i % 8 == 0 else W * 0.0018
        dd2.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
    img.alpha_composite(gold_fill(dm2))

    # engraved outer ring pair
    om, od = new_mask()
    ring_mask(od, int(R * 1.28), max(4, W // 300))
    ring_mask(od, int(R * 1.16), max(2, W // 700))
    img.alpha_composite(gold_fill(om))

    # central disc
    dm, dd = new_mask()
    dd.ellipse([C - R, C - R, C + R, C + R], fill=255)
    img.alpha_composite(gold_fill(dm))
    # engraved inner circles (night hairlines) + center dot
    eng = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ed = ImageDraw.Draw(eng)
    for k, alpha in [(0.84, 160), (0.62, 130)]:
        rr = R * k
        ed.ellipse([C - rr, C - rr, C + rr, C + rr], outline=NIGHT + (alpha,),
                   width=max(2, W // 700))
    # tiny engraved starburst at center
    for i in range(8):
        ang = math.radians(i * 45)
        x1, y1 = rot(R * 0.10, 0, ang)
        x2, y2 = rot(R * 0.42 if i % 2 == 0 else R * 0.30, 0, ang)
        ed.line([x1, y1, x2, y2], fill=NIGHT + (170,), width=max(3, W // 500))
    img.alpha_composite(eng)

    # rim light
    rim = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    rd2 = ImageDraw.Draw(rim)
    rd2.arc([C - R, C - R, C + R, C + R], 160, 250, fill=CHAMPAGNE + (235,),
            width=max(3, W // 400))
    rd2.arc([C - R, C - R, C + R, C + R], 15, 75, fill=BRONZE + (210,),
            width=max(3, W // 400))
    img.alpha_composite(rim)
    return img


# ============================================================ C. LUNA AUREA
def emblem_C():
    img = canvas()
    R = int(W * 0.24)

    gm, gd = new_mask()
    gd.ellipse([C - R, C - R, C + R, C + R], fill=255)
    img.alpha_composite(glow_layer(gm, W * 0.05, 95))

    # pearl-dot orbit ring
    dm2, dd2 = new_mask()
    for i in range(72):
        ang = math.radians(i * 5)
        x, y = rot(R * 1.42, 0, ang)
        rr = W * 0.0032 if i % 6 == 0 else W * 0.0016
        dd2.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
    img.alpha_composite(gold_fill(dm2))
    # compass hairline rays outside orbit
    hm, hd = new_mask()
    for i in range(8):
        ang = math.radians(i * 45 - 90)
        taper_poly(hd, ang, R * 1.5, R * 1.68, W * 0.0024)
    img.alpha_composite(gold_fill(hm))

    # crescent (opening right): big circle minus offset circle
    cm, cd = new_mask()
    cd.ellipse([C - R, C - R, C + R, C + R], fill=255)
    off = int(R * 0.62)
    cd.ellipse([C - R + off, C - R + int(R * 0.10), C + R + off - int(R * 0.16),
                C + R - int(R * 0.10)], fill=0)
    img.alpha_composite(gold_fill(cm))
    # engraved hairline following the crescent inner edge + stipple
    eng = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ed = ImageDraw.Draw(eng)
    ed.ellipse([C - R + off + W // 90, C - R + int(R * 0.10) + W // 90,
                C + R + off - int(R * 0.16) - W // 90,
                C + R - int(R * 0.10) - W // 90],
               outline=NIGHT + (110,), width=max(2, W // 800))
    rng = np.random.default_rng(7)
    for _ in range(90):
        a = rng.uniform(math.pi * 0.55, math.pi * 1.45)
        rr = rng.uniform(R * 0.55, R * 0.92)
        x, y = C + rr * math.cos(a + math.pi), C + rr * math.sin(a + math.pi)
        dot = rng.uniform(1.2, 2.6) * W / 1000
        ed.ellipse([x - dot, y - dot, x + dot, y + dot],
                   fill=NIGHT + (int(rng.uniform(40, 90)),))
    img.alpha_composite(eng)

    # radiant star in the crescent opening
    sx, sy = C + int(R * 0.58), C
    sm, sd = new_mask()
    star4(sd, sx, sy, R * 0.34, thin=0.14)
    star4(sd, sx, sy, R * 0.20, thin=0.22)
    img.alpha_composite(gold_fill(sm))
    # micro stars scattered
    mm, md = new_mask()
    for dx, dy, r in [(0.95, -0.65, 0.05), (1.05, 0.55, 0.036), (0.2, -1.18, 0.03),
                      (0.35, 1.15, 0.026), (1.25, -0.1, 0.02)]:
        star4(md, C + dx * R, C + dy * R, r * R * 2.4)
    img.alpha_composite(gold_fill(mm))

    # crescent rim light
    rim = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    rd2 = ImageDraw.Draw(rim)
    rd2.arc([C - R, C - R, C + R, C + R], 120, 250, fill=CHAMPAGNE + (235,),
            width=max(3, W // 380))
    rd2.arc([C - R, C - R, C + R, C + R], 60, 105, fill=BRONZE + (190,),
            width=max(3, W // 420))
    img.alpha_composite(rim)
    return img


COVER_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 0; }}
body {{ margin:0; font-family: Georgia, serif; }}
.cover {{ width: 210mm; height: 297mm; position: relative;
  background: radial-gradient(ellipse at 50% 30%, #43277a 0%, #2d1b52 45%, #1a1333 100%); color:#f3eefe; }}
.f1 {{ position:absolute; top:8mm; left:8mm; right:8mm; bottom:8mm; border:2px solid #c9b458; }}
.f2 {{ position:absolute; top:11mm; left:11mm; right:11mm; bottom:11mm; border:0.7px solid #c9b458; }}
.in {{ position:absolute; top:20mm; left:0; right:0; text-align:center; }}
.brand {{ font-size:12pt; letter-spacing:8px; color:#c9b458; }}
.om {{ font-size:10pt; color:#9d90c4; margin-top:4mm; letter-spacing:2px; }}
h1 {{ font-size:34pt; font-weight:normal; color:#f8f5ff; margin:10mm 0 2mm; line-height:1.1; }}
.sub {{ font-size:13pt; letter-spacing:4px; color:#c9b458; text-transform:uppercase; }}
.emblem {{ margin:4mm auto 2mm; width:118mm; }}
.plq {{ display:inline-block; border:1.6px solid #c9b458; border-radius:20px; padding:4mm 16mm; }}
.plq .n {{ font-size:19pt; color:#fff; }} .plq .b {{ font-size:10.5pt; color:#cfc4ec; margin-top:1.5mm; }}
.b3 {{ margin-top:6mm; font-size:11.5pt; color:#c9b458; }}
.ft {{ position:absolute; bottom:15mm; left:0; right:0; text-align:center; font-size:9.5pt; color:#9d90c4; }}
</style></head><body><div class="cover"><div class="f1"></div><div class="f2"></div>
<div class="in"><div class="brand">A R V E L O S</div>
<div class="om">॥ Your Sky · Your Numbers · Your Year Ahead ॥</div>
<h1>Fortune &amp; Birth Chart<br>Report</h1>
<div class="sub">Mixed Report — Western + Vedic</div>
<img class="emblem" src="file://{emblem}">
<div class="plq"><div class="n">Pamit Raj</div><div class="b">16 October 1992, 10:30 — Patna, India</div></div>
<div class="b3">Sagittarius Rising · Libra Sun · Taurus Moon · Mulank 7 · Bhagyank 2</div></div>
<div class="ft">Individually calculated · arvelos.cloud<br>One report, one payment — no subscription.</div>
</div></body></html>"""

if __name__ == "__main__":
    from weasyprint import HTML
    for name, fn in [("A_gilded_eclipse", emblem_A),
                     ("B_solar_diadem", emblem_B),
                     ("C_luna_aurea", emblem_C)]:
        im = fn().resize((S, S), Image.LANCZOS)
        path = f"/tmp/emb_{name}.png"
        im.save(path)
        HTML(string=COVER_HTML.format(emblem=path)).write_pdf(f"/tmp/cov_{name}.pdf")
        print(name)
