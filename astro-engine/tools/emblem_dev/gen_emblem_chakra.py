"""Solar Diadem × Sudarshan Chakra fusion — two intensities + original."""
import math
from PIL import Image, ImageDraw
from gen_emblems_v2 import (W, S, C, NIGHT, CHAMPAGNE, BRONZE, canvas,
                            new_mask, gold_fill, glow_layer, rot, taper_poly,
                            flame_poly, ring_mask, emblem_B, COVER_HTML)


def swept_ray(d, ang, r0, r1, w, sweep):
    """Flame ray whose centerline curves tangentially — implies rotation."""
    n = 14
    pts = []
    for i in range(n + 1):
        t = i / n
        r = r0 + (r1 - r0) * t
        a = ang + sweep * t
        pts.append(rot(r, -w * (1 - t), a))
    for i in range(n + 1):
        t = 1 - i / n
        r = r0 + (r1 - r0) * t
        a = ang + sweep * t
        pts.append(rot(r, w * (1 - t), a))
    d.polygon(pts, fill=255)


def serrated_ring(d, r, teeth, tooth_h, tooth_w, sweep=0.35):
    """Chakra rim: ring with angled saw-teeth (rotation direction)."""
    for i in range(teeth):
        ang = 2 * math.pi * i / teeth
        base1 = rot(r, -tooth_w, ang)
        base2 = rot(r, tooth_w, ang)
        tip = rot(r + tooth_h, 0, ang + sweep * tooth_h / r)
        d.polygon([base1, tip, base2], fill=255)


def spokes_engraving(ed, r_hub, r_out, n=8, width=3, alpha=170):
    for i in range(n):
        ang = math.radians(i * 360 / n - 90)
        x1, y1 = rot(r_hub, 0, ang)
        x2, y2 = rot(r_out, 0, ang)
        ed.line([x1, y1, x2, y2], fill=NIGHT + (alpha,), width=width)


def emblem_chakra(full: bool) -> Image.Image:
    img = canvas()
    R = int(W * 0.16)

    gm, gd = new_mask()
    gd.ellipse([C - R * 2.1, C - R * 2.1, C + R * 2.1, C + R * 2.1], fill=255)
    img.alpha_composite(glow_layer(gm, W * 0.05, 90))

    # outer rays: swept (full) or straight flames (subtle)
    fm, fd = new_mask()
    sweep = math.radians(16) if full else math.radians(7)
    for i in range(16):
        ang = math.radians(i * 22.5 - 90)
        swept_ray(fd, ang, R * 1.42, R * 2.55 if i % 2 == 0 else R * 2.12,
                  W * 0.011, sweep)
    img.alpha_composite(gold_fill(fm))
    # hairline rays, lightly swept
    hm, hd = new_mask()
    for i in range(32):
        ang = math.radians(i * 11.25 - 84.4)
        swept_ray(hd, ang, R * 1.42, R * 1.82, W * 0.0016, sweep * 0.7)
    img.alpha_composite(gold_fill(hm))
    # dotted halo
    dm2, dd2 = new_mask()
    for i in range(64):
        ang = math.radians(i * 5.625)
        x, y = rot(R * 2.75, 0, ang)
        rr = W * 0.0035 if i % 8 == 0 else W * 0.0018
        dd2.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
    img.alpha_composite(gold_fill(dm2))

    # === CHAKRA RIM: serrated ring between disc and rays ===
    srm, srd = new_mask()
    teeth = 36 if full else 28
    serrated_ring(srd, int(R * 1.24), teeth, int(R * 0.14), W * 0.004,
                  sweep=0.5 if full else 0.3)
    ring_mask(srd, int(R * 1.26), max(4, W // 300))
    ring_mask(srd, int(R * 1.13), max(2, W // 700))
    img.alpha_composite(gold_fill(srm))

    # central disc
    dm, dd = new_mask()
    dd.ellipse([C - R, C - R, C + R, C + R], fill=255)
    img.alpha_composite(gold_fill(dm))

    # === CHAKRA SPOKES engraved in the disc ===
    eng = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ed = ImageDraw.Draw(eng)
    hub = R * 0.30
    ed.ellipse([C - hub, C - hub, C + hub, C + hub],
               outline=NIGHT + (170,), width=max(3, W // 500))
    ed.ellipse([C - R * 0.86, C - R * 0.86, C + R * 0.86, C + R * 0.86],
               outline=NIGHT + (150,), width=max(2, W // 700))
    spokes_engraving(ed, hub, R * 0.86, n=8, width=max(3, W // 500))
    if full:  # secondary fine spokes between the main ones
        for i in range(8):
            ang = math.radians(i * 45 - 67.5)
            x1, y1 = rot(hub, 0, ang)
            x2, y2 = rot(R * 0.86, 0, ang)
            ed.line([x1, y1, x2, y2], fill=NIGHT + (90,),
                    width=max(2, W // 900))
    # hub center: small solid dot + engraved point ring
    ed.ellipse([C - R * 0.07, C - R * 0.07, C + R * 0.07, C + R * 0.07],
               fill=NIGHT + (180,))
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


if __name__ == "__main__":
    from weasyprint import HTML
    variants = {"1_diadem_original": emblem_B(),
                "2_chakra_subtle": emblem_chakra(False),
                "3_chakra_full": emblem_chakra(True)}
    for name, im in variants.items():
        path = f"/tmp/emb_{name}.png"
        im.resize((S, S), Image.LANCZOS).save(path)
        HTML(string=COVER_HTML.format(emblem=path)).write_pdf(f"/tmp/ck_{name}.pdf")
        print(name)
