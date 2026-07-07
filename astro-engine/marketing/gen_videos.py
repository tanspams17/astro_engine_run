"""
Arvelos ad video generator — faceless text-overlay format, 9:16, <60s.
Pipeline: PIL cosmic background -> ffmpeg zoompan + timed drawtext -> VO audio.
Zero paid tools. Re-run any time a script/voice changes.
"""
import math
import os
import random
import subprocess
import json

W, H = 1080, 1920
FPS = 30
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "videos")
TMP = "/tmp/arvelos_vid"


def make_background(path: str, seed: int, hue_shift: float = 0.0):
    """Deep-indigo cosmic gradient with starfield + soft nebula blobs."""
    from PIL import Image, ImageDraw, ImageFilter
    random.seed(seed)
    img = Image.new("RGB", (W, H))
    top = (26 + int(8 * hue_shift), 19, 51)
    bot = (67 + int(12 * hue_shift), 39, 122)
    for y in range(H):
        t = y / H
        img.paste(tuple(int(a + (b - a) * t) for a, b in zip(top, bot)),
                  (0, y, W, y + 1))
    # nebula blobs
    neb = Image.new("RGB", (W, H), (0, 0, 0))
    nd = ImageDraw.Draw(neb)
    for _ in range(6):
        x, y = random.randint(0, W), random.randint(0, H)
        r = random.randint(200, 480)
        c = random.choice([(90, 60, 150), (60, 40, 110), (120, 90, 60)])
        nd.ellipse([x - r, y - r, x + r, y + r], fill=c)
    neb = neb.filter(ImageFilter.GaussianBlur(180))
    img = Image.blend(img, neb, 0.35)
    # stars
    d = ImageDraw.Draw(img)
    for _ in range(420):
        x, y = random.randint(0, W), random.randint(0, H)
        r = random.choice([1, 1, 1, 2, 2, 3])
        b = random.randint(140, 255)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(b, b, min(255, b + 20)))
    # a few gold accent stars
    for _ in range(24):
        x, y = random.randint(0, W), random.randint(0, H)
        r = random.choice([2, 3])
        d.ellipse([x - r, y - r, x + r, y + r], fill=(201, 180, 88))
    img.save(path, quality=92)


def wrap(text: str, per_line: int = 22) -> str:
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        if len(cur) + len(w_) + 1 > per_line and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = (cur + " " + w_).strip()
    lines.append(cur)
    return "\n".join(lines)


def duration_of(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                        "-show_format", path], capture_output=True, text=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def build_video(name: str, vo_path: str, segments: list[tuple[str, float]],
                seed: int, hue: float, cta: str = "arvelos.cloud — link in bio"):
    """segments: (text, weight) — weights are proportional shares of VO time."""
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    bg = os.path.join(TMP, f"bg_{name}.jpg")
    make_background(bg, seed, hue)

    vo_len = duration_of(vo_path)
    total_w = sum(wt for _, wt in segments)
    tail = 1.6                      # CTA hold after VO ends
    dur = vo_len + tail

    # timed drawtext filters
    filters = [
        f"scale={W * 2}:{H * 2},zoompan=z='1.0+0.10*on/{int(dur * FPS)}':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(dur * FPS)}:"
        f"s={W}x{H}:fps={FPS}",
    ]
    t = 0.0
    for i, (text, wt) in enumerate(segments):
        seg_len = vo_len * wt / total_w
        tf = os.path.join(TMP, f"{name}_seg{i}.txt")
        with open(tf, "w") as f:
            f.write(wrap(text))
        big = i == 0            # hook slightly bigger
        size = 76 if big else 62
        filters.append(
            f"drawtext=textfile='{tf}':fontfile='{FONT_BOLD}':"
            f"fontsize={size}:fontcolor=white:line_spacing=18:"
            f"x=(w-text_w)/2:y=(h-text_h)/2-120:"
            f"borderw=3:bordercolor=0x1a1333@0.85:"
            f"enable='between(t,{t:.2f},{t + seg_len:.2f})'")
        t += seg_len
    # brand watermark + CTA
    filters.append(
        f"drawtext=text='A R V E L O S':fontfile='{FONT}':fontsize=40:"
        f"fontcolor=0xc9b458:x=(w-text_w)/2:y=170:borderw=2:"
        f"bordercolor=0x1a1333@0.7")
    filters.append(
        f"drawtext=text='{cta}':fontfile='{FONT_BOLD}':fontsize=52:"
        f"fontcolor=0xc9b458:x=(w-text_w)/2:y=h-360:borderw=3:"
        f"bordercolor=0x1a1333@0.85:enable='gte(t,{max(0, vo_len - 2.5):.2f})'")

    out_path = os.path.join(OUT, f"{name}.mp4")
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", bg, "-i", vo_path,
           "-vf", ",".join(filters), "-t", f"{dur:.2f}",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
           "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-shortest",
           out_path]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"{name}: {dur:.1f}s -> {out_path}")


VOS = {}  # filled by main


def main():
    vo_dir = os.path.join(HERE, "vo")
    vos = sorted(os.listdir(vo_dir))
    vo_s1 = os.path.join(vo_dir, next(f for f in vos if f.startswith("tts_Most")))
    vo_s2 = os.path.join(vo_dir, next(f for f in vos if f.startswith("tts_Forge")))
    vo_s3 = os.path.join(vo_dir, next(f for f in vos if f.startswith("tts_I'm") or f.startswith("tts_I_m")))

    # diaspora_vedic_s1_textoverlay — authenticity hook
    build_video("diaspora_vedic_s1_textoverlay", vo_s1, [
        ("Most astrology apps are using the WRONG zodiac.", 15),
        ("Western astrology: tropical zodiac, based on seasons.", 12),
        ("Vedic astrology: sidereal zodiac — where the stars ACTUALLY are.", 15),
        ("Read for over 5,000 years.", 8),
        ("Arvelos: real Vedic Jyotish, calculated properly.", 13),
        ("Not a generic horoscope template.", 8),
        ("No subscription. Your real chart, once.", 12),
    ], seed=11, hue=0.0)

    # domestic_vedic_s2_textoverlay — curiosity hook
    build_video("domestic_vedic_s2_textoverlay", vo_s2, [
        ("Forget your sun sign. Your NAKSHATRA matters more.", 16),
        ("27 lunar mansions — far more precise than 12 sun signs.", 16),
        ("Most people have never even heard their own.", 11),
        ("Arvelos calculates yours properly. Authentic Vedic methods.", 15),
        ("And explains exactly what it means.", 9),
        ("Find out yours.", 6),
    ], seed=22, hue=0.5)

    # wellness_western_s3_textoverlay — anti-subscription hook
    build_video("wellness_western_s3_textoverlay", vo_s3, [
        ("I'm NOT going to charge you every month for this.", 15),
        ("Most astrology apps: cheap quiz, then quiet monthly billing...", 14),
        ("...until you notice and cancel.", 7),
        ("That's not what this is.", 7),
        ("Arvelos: ONE payment. Full chart. Delivered once.", 13),
        ("No subscription. No notifications you'll forget about.", 12),
        ("Get yours.", 5),
    ], seed=33, hue=1.0)


if __name__ == "__main__":
    main()
