"""
Sudarshan Chakra × Solar Diadem — authentic temple iconography:
jwala (flame tongues) curling in rotation direction around a solid rim,
pearl beading, blade spokes radiating from a lotus hub. Three variants.
"""
import math
from PIL import Image, ImageDraw
from gen_emblems_v2 import (W, S, C, NIGHT, CHAMPAGNE, BRONZE, canvas,
                            new_mask, gold_fill, glow_layer, rot,
                            ring_mask, COVER_HTML)


def jwala(d, ang, r0, r1, base_w, curl):
    """Single flame tongue: rises outward, bulges, tip hooks tangentially."""
    n = 18
    out_pts, in_pts = [], []
    for i in range(n + 1):
        t = i / n
        r = r0 + (r1 - r0) * t
        drift = curl * (t ** 2.1)          # accelerating curl
        w = base_w * (1 + 0.55 * math.sin(math.pi * min(t * 1.15, 1))) * (1 - t) ** 0.75
        a = ang + drift
        out_pts.append(rot(r, -w, a))
        in_pts.append(rot(r, w, a))
    # tip hook: small extra curl
    tip_a = ang + curl * 1.18
    out_pts.append(rot(r1 + (r1 - r0) * 0.06, 0, tip_a))
    d.polygon(out_pts + in_pts[::-1], fill=255)


def blade_spoke(d, ang, r0, r1, w0, w1):
    """Petal/blade shaped spoke with soft sides."""
    n = 10
    pts = []
    for i in range(n + 1):
        t = i / n
        r = r0 + (r1 - r0) * t
        w = w0 + (w1 - w0) * t + w0 * 0.5 * math.sin(math.pi * t)
        pts.append(rot(r, -w, ang))
    for i in range(n + 1):
        t = 1 - i / n
        r = r0 + (r1 - r0) * t
        w = w0 + (w1 - w0) * t + w0 * 0.5 * math.sin(math.pi * t)
        pts.append(rot(r, w, ang))
    d.polygon(pts, fill=255)


def chakra(n_spokes=12, n_flames=22, curl_deg=26) -> Image.Image:
    img = canvas()
    R = int(W * 0.185)

    # glow
    gm, gd = new_mask()
    gd.ellipse([C - R * 1.9, C - R * 1.9, C + R * 1.9, C + R * 1.9], fill=255)
    img.alpha_composite(glow_layer(gm, W * 0.05, 95))

    # ---- jwala flame ring (all curling one direction)
    fm, fd = new_mask()
    curl = math.radians(curl_deg)
    for i in range(n_flames):
        ang = 2 * math.pi * i / n_flames - math.pi / 2
        long = i % 2 == 0
        jwala(fd, ang, R * 1.18, R * (1.78 if long else 1.56),
              W * 0.0085 if long else W * 0.0065, curl if long else curl * 0.85)
    img.alpha_composite(gold_fill(fm))

    # ---- rim: two solid rings with pearl beads between
    rm, rd = new_mask()
    ring_mask(rd, int(R * 1.18), max(5, W // 240))
    ring_mask(rd, int(R * 0.98), max(5, W // 240))
    n_pearls = 40
    for i in range(n_pearls):
        ang = 2 * math.pi * i / n_pearls
        x, y = rot(R * 1.08, 0, ang)
        pr = W * 0.0042
        rd.ellipse([x - pr, y - pr, x + pr, y + pr], fill=255)
    img.alpha_composite(gold_fill(rm))

    # ---- blade spokes (gold over night interior)
    sm, sd = new_mask()
    for i in range(n_spokes):
        ang = 2 * math.pi * i / n_spokes - math.pi / 2
        blade_spoke(sd, ang, R * 0.30, R * 0.96, W * 0.0075, W * 0.0028)
    img.alpha_composite(gold_fill(sm))
    # engraved midline on each spoke
    eng = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ed = ImageDraw.Draw(eng)
    for i in range(n_spokes):
        ang = 2 * math.pi * i / n_spokes - math.pi / 2
        x1, y1 = rot(R * 0.36, 0, ang)
        x2, y2 = rot(R * 0.88, 0, ang)
        ed.line([x1, y1, x2, y2], fill=NIGHT + (120,), width=max(2, W // 900))

    # ---- hub: gold disc + lotus engraving
    hm, hd = new_mask()
    hub = int(R * 0.30)
    hd.ellipse([C - hub, C - hub, C + hub, C + hub], fill=255)
    img.alpha_composite(gold_fill(hm))
    # lotus: 8 petal arcs engraved on hub
    for i in range(8):
        ang = 2 * math.pi * i / 8
        px, py = rot(hub * 0.58, 0, ang)
        pr = hub * 0.34
        ed.ellipse([px - pr, py - pr, px + pr, py + pr],
                   outline=NIGHT + (140,), width=max(2, W // 900))
    ed.ellipse([C - hub * 0.30, C - hub * 0.30, C + hub * 0.30, C + hub * 0.30],
               outline=NIGHT + (170,), width=max(2, W // 700))
    ed.ellipse([C - hub * 0.10, C - hub * 0.10, C + hub * 0.10, C + hub * 0.10],
               fill=NIGHT + (190,))
    img.alpha_composite(eng)

    # ---- rim light on outer rim ring
    rim = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    rd2 = ImageDraw.Draw(rim)
    RR = R * 1.18
    rd2.arc([C - RR, C - RR, C + RR, C + RR], 160, 250,
            fill=CHAMPAGNE + (235,), width=max(3, W // 400))
    rd2.arc([C - RR, C - RR, C + RR, C + RR], 15, 75,
            fill=BRONZE + (200,), width=max(3, W // 420))
    img.alpha_composite(rim)
    return img


if __name__ == "__main__":
    from weasyprint import HTML
    variants = {
        "1_temple_12spoke": chakra(12, 22, 26),
        "2_dense_16spoke": chakra(16, 28, 22),
        "3_bold_8spoke": chakra(8, 18, 32),
    }
    for name, im in variants.items():
        path = f"/tmp/emb_ck2_{name}.png"
        im.resize((S, S), Image.LANCZOS).save(path)
        HTML(string=COVER_HTML.format(emblem=path)).write_pdf(f"/tmp/ck2_{name}.pdf")
        print(name)


def chakra_solid(n_spokes=16, n_flames=28, curl_deg=22) -> Image.Image:
    """Final: dense 16-spoke chakra on a SOLID gold disc, engraved detail."""
    img = canvas()
    R = int(W * 0.185)

    # glow behind full silhouette only
    gm, gd = new_mask()
    gd.ellipse([C - R * 1.55, C - R * 1.55, C + R * 1.55, C + R * 1.55], fill=255)
    img.alpha_composite(glow_layer(gm, W * 0.045, 100))

    # jwala flame ring
    fm, fd = new_mask()
    curl = math.radians(curl_deg)
    for i in range(n_flames):
        ang = 2 * math.pi * i / n_flames - math.pi / 2
        long = i % 2 == 0
        jwala(fd, ang, R * 1.18, R * (1.74 if long else 1.52),
              W * 0.0082 if long else W * 0.0062, curl if long else curl * 0.85)
    img.alpha_composite(gold_fill(fm))

    # SOLID disc up to outer rim
    dm, dd = new_mask()
    RR = int(R * 1.18)
    dd.ellipse([C - RR, C - RR, C + RR, C + RR], fill=255)
    img.alpha_composite(gold_fill(dm))

    # engraving layer (night hairlines on gold)
    eng = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ed = ImageDraw.Draw(eng)
    lw = max(3, W // 600)
    # rim: two engraved rings + pearl dots between
    for rr, a in [(R * 1.18 - lw, 200), (R * 0.98, 190)]:
        ed.ellipse([C - rr, C - rr, C + rr, C + rr],
                   outline=NIGHT + (a,), width=lw)
    for i in range(44):
        ang = 2 * math.pi * i / 44
        x, y = rot(R * 1.08, 0, ang)
        pr = W * 0.0038
        ed.ellipse([x - pr, y - pr, x + pr, y + pr],
                   outline=NIGHT + (170,), width=max(2, W // 900))
    # 16 engraved blade spokes
    for i in range(n_spokes):
        ang = 2 * math.pi * i / n_spokes - math.pi / 2
        for side in (-1, 1):
            pts = []
            for j in range(11):
                t = j / 10
                r = R * (0.30 + 0.66 * t)
                w = (W * 0.0068) * (1 - t * 0.62) + (W * 0.003) * math.sin(math.pi * t)
                pts.append(rot(r, side * w, ang))
            ed.line(pts, fill=NIGHT + (160,), width=max(2, W // 800))
        x1, y1 = rot(R * 0.36, 0, ang)
        x2, y2 = rot(R * 0.90, 0, ang)
        ed.line([x1, y1, x2, y2], fill=NIGHT + (90,), width=max(2, W // 1100))
    # hub ring + lotus
    hub = int(R * 0.30)
    ed.ellipse([C - hub, C - hub, C + hub, C + hub],
               outline=NIGHT + (190,), width=lw)
    for i in range(8):
        ang = 2 * math.pi * i / 8
        px, py = rot(hub * 0.58, 0, ang)
        pr = hub * 0.34
        ed.ellipse([px - pr, py - pr, px + pr, py + pr],
                   outline=NIGHT + (140,), width=max(2, W // 900))
    ed.ellipse([C - hub * 0.30, C - hub * 0.30, C + hub * 0.30, C + hub * 0.30],
               outline=NIGHT + (170,), width=max(2, W // 700))
    ed.ellipse([C - hub * 0.10, C - hub * 0.10, C + hub * 0.10, C + hub * 0.10],
               fill=NIGHT + (200,))
    img.alpha_composite(eng)

    # rim light
    rim = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    rd2 = ImageDraw.Draw(rim)
    rd2.arc([C - RR, C - RR, C + RR, C + RR], 160, 250,
            fill=CHAMPAGNE + (235,), width=max(3, W // 400))
    rd2.arc([C - RR, C - RR, C + RR, C + RR], 15, 75,
            fill=BRONZE + (200,), width=max(3, W // 420))
    img.alpha_composite(rim)
    return img
