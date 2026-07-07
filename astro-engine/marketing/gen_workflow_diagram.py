"""Render the Arvelos end-to-end operations workflow diagram (PNG)."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 900
INK = (26, 19, 51)
DEEP = (45, 27, 82)
VIOLET = (67, 39, 122)
GOLD = (201, 180, 88)
PAPER = (246, 243, 252)
MUTED = (155, 144, 196)
GREEN = (110, 170, 120)

F = "/usr/share/fonts/truetype/dejavu/DejaVuSerif%s.ttf"
f_title = ImageFont.truetype(F % "-Bold", 44)
f_head = ImageFont.truetype(F % "-Bold", 26)
f_body = ImageFont.truetype(F % "", 20)
f_small = ImageFont.truetype(F % "", 17)
f_tag = ImageFont.truetype(F % "-Bold", 19)

img = Image.new("RGB", (W, H), INK)
d = ImageDraw.Draw(img)

# header
d.text((60, 38), "ARVELOS — OPERATIONS, END TO END", font=f_title, fill=GOLD)
d.text((60, 96), "One-time-payment astrology reports · arvelos.cloud · no subscription",
       font=f_body, fill=MUTED)


def box(x, y, w, h, head, lines, accent=VIOLET, tag=None):
    d.rounded_rectangle([x, y, x + w, y + h], 14, fill=DEEP, outline=accent, width=3)
    d.text((x + 18, y + 14), head, font=f_head, fill=PAPER)
    for i, ln in enumerate(lines):
        d.text((x + 18, y + 52 + i * 26), ln, font=f_small, fill=MUTED)
    if tag:
        tw = d.textlength(tag, font=f_tag)
        d.rounded_rectangle([x + w - tw - 30, y - 14, x + w - 6, y + 16], 12, fill=GOLD)
        d.text((x + w - tw - 18, y - 10), tag, font=f_tag, fill=INK)


def arrow(x1, y1, x2, y2, color=GOLD, wd=4):
    d.line([x1, y1, x2, y2], fill=color, width=wd)
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    for s in (0.5,):
        pass
    a1 = (x2 - 16 * math.cos(ang - 0.45), y2 - 16 * math.sin(ang - 0.45))
    a2 = (x2 - 16 * math.cos(ang + 0.45), y2 - 16 * math.sin(ang + 0.45))
    d.polygon([a1, a2, (x2, y2)], fill=color)


ROW1_Y, ROW2_Y, BW, BH = 190, 520, 330, 200

# Row 1 — marketing loop
box(60, ROW1_Y, BW, BH, "1 · Create content",
    ["Scripts (4 hooks x 3 markets)", "ElevenLabs voiceover",
     "Rendered 9:16 text-overlay video", "QC: no predictive claims"],
    tag="BUILT")
box(455, ROW1_Y, BW, BH, "2 · Publish / Ads",
    ["Instagram Reels (organic first)", "Meta Ads Manager (paid phase)",
     "Naming: market_tier_s#_format", "UTM tags on every link"],
    tag="GATED: Meta acct")
box(850, ROW1_Y, BW, BH, "3 · Landing + Quiz",
    ["arvelos.cloud", "UTM captured at quiz-start", "Birth date / time / place",
     "Focus areas + tier, live pricing"], tag="BUILT")
box(1245, ROW1_Y, BW, BH, "4 · Checkout",
    ["Fixed price at order creation", "PaymentAdapter interface",
     "Mock adapter now,", "Mollie drop-in later"], tag="GATED: gateway")

# Row 2 — fulfilment (right to left flow)
box(1245, ROW2_Y, BW, BH, "5 · Astro engine",
    ["Swiss Ephemeris calculation", "Western tropical / Placidus",
     "Vedic sidereal / Lahiri", "Nakshatra + Vimshottari dasha"], tag="BUILT")
box(850, ROW2_Y, BW, BH, "6 · Report PDF",
    ["Content library (real writing)", "WeasyPrint styled render",
     "Western / Vedic / Mixed tiers", "< 60 seconds end to end"], tag="BUILT")
box(455, ROW2_Y, BW, BH, "7 · Delivery",
    ["Private download link", "Email via SMTP provider",
     "Order: pending-paid-delivered", "Refund path defined"], tag="BUILT")
box(60, ROW2_Y, BW, BH, "8 · Analytics loop",
    ["Events: quiz_start, complete,", "purchase — stored w/ UTM",
     "CAC per creative, kill/scale", "reinvest into winners"], tag="BUILT")

# arrows row1 left->right
arrow(60 + BW, ROW1_Y + BH // 2, 455, ROW1_Y + BH // 2)
arrow(455 + BW, ROW1_Y + BH // 2, 850, ROW1_Y + BH // 2)
arrow(850 + BW, ROW1_Y + BH // 2, 1245, ROW1_Y + BH // 2)
# down
arrow(1245 + BW // 2, ROW1_Y + BH, 1245 + BW // 2, ROW2_Y)
# row2 right->left
arrow(1245, ROW2_Y + BH // 2, 850 + BW, ROW2_Y + BH // 2)
arrow(850, ROW2_Y + BH // 2, 455 + BW, ROW2_Y + BH // 2)
arrow(455, ROW2_Y + BH // 2, 60 + BW, ROW2_Y + BH // 2)
# loop back up (analytics -> create content)
arrow(60 + BW // 2, ROW2_Y, 60 + BW // 2, ROW1_Y + BH, color=GREEN)
d.text((78, (ROW1_Y + BH + ROW2_Y) // 2 - 14), "learnings feed next creatives",
       font=f_small, fill=GREEN)

# footer
d.text((60, 800), "Customer touch: steps 2-4 and 7 only.  Everything in steps 5-6 is automatic — no human in the loop per order.",
       font=f_body, fill=PAPER)
d.text((60, 834), "Gated items need Raj's accounts: Meta Business Manager · payment gateway (Mollie) · SMTP provider · DNS A-record.",
       font=f_small, fill=MUTED)

img.save("workflow_diagram.png")
print("saved workflow_diagram.png")
