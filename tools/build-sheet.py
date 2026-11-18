#!/usr/bin/env python3
"""Contact sheet: Genesis Dot (#1) featured + a 4x4 grid, 4 samples per class."""
import json
import os
import random

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "collection")
OUT = os.path.expanduser("~/workspace/your_files/talvio-generate-sample-sheet.png")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# pick 4 ids per class deterministically from metadata
by_class = {}
for tid in range(1, 10001):
    with open(os.path.join(BASE, "metadata", f"{tid}.json")) as f:
        attrs = {a["trait_type"]: a["value"] for a in json.load(f)["attributes"]}
    by_class.setdefault(attrs["Class"], []).append(tid)

rng = random.Random(42)
samples = []
for cls in ["Prime", "Pixel Dot", "Stealth Dot", "Aurum Dot"]:
    ids = [i for i in by_class[cls] if i != 1]
    samples.extend((tid, cls) for tid in rng.sample(ids, 4))
rng.shuffle(samples)

W, H = 1720, 1180
sheet = Image.new("RGB", (W, H), (7, 7, 7))
dr = ImageDraw.Draw(sheet)
title = ImageFont.truetype(FONT, 44)
sub = ImageFont.truetype(FONT_R, 24)
cap = ImageFont.truetype(FONT, 21)
cap_r = ImageFont.truetype(FONT_R, 19)

dr.text((36, 28), "TALVIO GENERATE — DOTFIELD", fill=(240, 236, 226), font=title)
dr.text((36, 84), "10,000 Black Dot Robots · sample sheet", fill=(150, 148, 140), font=sub)

# Genesis feature
gen = Image.open(os.path.join(BASE, "images", "1.webp")).resize((560, 560))
sheet.paste(gen, (36, 150))
dr.rectangle([36, 150, 596, 710], outline=(238, 192, 94), width=3)
dr.text((36, 726), "TOKEN #1 — GENESIS DOT", fill=(255, 219, 130), font=cap)
dr.text((36, 756), "Aurum Dot · one of one · halo + crown", fill=(170, 168, 160), font=cap_r)

# 4x4 grid
cell, gap = 238, 18
gx, gy = 650, 150
for i, (tid, cls) in enumerate(samples):
    r, c = divmod(i, 4)
    x, y = gx + c * (cell + gap), gy + r * (cell + gap + 26)
    im = Image.open(os.path.join(BASE, "images", f"{tid}.webp")).resize((cell, cell))
    sheet.paste(im, (x, y))
    gold = cls == "Aurum Dot"
    dr.rectangle([x, y, x + cell, y + cell], outline=(90, 84, 60) if gold else (52, 52, 55), width=2)
    dr.text((x + 2, y + cell + 5), f"#{tid} · {cls.upper()}", fill=(255, 219, 130) if gold else (205, 202, 195), font=cap_r)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
sheet.save(OUT)
print("saved", OUT)
