#!/usr/bin/env python3
"""
Talvio Generate — DOTFIELD collection generator.

10,000 unique Black Dot Robots, drawn procedurally with PIL on a dot lattice.
Seeded and fully reproducible: python3 generate.py --start 1 --end 10000

Classes (fixed-seed shuffle over token IDs):
  Prime 3,000 · Pixel Dot 2,800 · Stealth Dot 2,700 · Aurum Dot 1,500
Token #1 is the one-of-one Genesis Dot (Aurum, halo + crown antenna).
"""
import argparse
import hashlib
import json
import math
import os
import random

from PIL import Image, ImageDraw

MASTER_SEED = 20261118
TOTAL = 10000
SIZE = 512
BG = (5, 5, 5)
IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "collection", "images")
META_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "collection", "metadata")

CLASS_COUNTS = {"Aurum Dot": 1500, "Prime": 3000, "Pixel Dot": 2800, "Stealth Dot": 2700}

CLASS_PARAMS = {
    "Prime":      dict(pitch=15.0, base_r=5.6, color=(233, 228, 216), accent=(255, 246, 220), skip=0.020, glow=False),
    "Pixel Dot":  dict(pitch=11.5, base_r=4.1, color=(226, 222, 236), accent=(205, 198, 255), skip=0.015, glow=False),
    "Stealth Dot": dict(pitch=15.0, base_r=5.2, color=(96, 97, 104),  accent=(150, 152, 162), skip=0.380, glow=False),
    "Aurum Dot":  dict(pitch=13.0, base_r=5.9, color=(238, 192, 94),  accent=(255, 219, 130), skip=0.006, glow=True),
}

HEADS = ["Dome", "Box", "Tall", "Wide", "Hex"]
VISORS = ["Visor Bar", "Dual Eyes", "Cyclops", "Cross", "Scanlines", "Chevron"]
ANTENNAS = ["None", "Stalk", "Dual Stalk", "Dish", "Fin"]
MOUTHS = ["Grille", "Smile", "Flat", "Vents", "None"]
CORES = ["Ring Core", "Diamond Core", "Bar Core", "Triangle Core", "Dot Core", "No Core"]
ARMS = ["Down", "Raised", "Out", "One Up"]
PROFILES = ["Uniform", "Core Glow", "Edge Pulse"]
BG_DENSITIES = ["Sparse Grid", "Standard Grid", "Dense Grid"]
LEGS = ["Legs", "Pedestal", "Hover"]


def class_assignment():
    """Deterministic token-id -> class map (fixed-seed shuffle, #1 forced Aurum)."""
    pool = []
    for cls, n in CLASS_COUNTS.items():
        pool.extend([cls] * n)
    random.Random(MASTER_SEED).shuffle(pool)
    assign = {i + 1: pool[i] for i in range(TOTAL)}
    if assign[1] != "Aurum Dot":
        for tid in range(2, TOTAL + 1):
            if assign[tid] == "Aurum Dot":
                assign[tid], assign[1] = assign[1], "Aurum Dot"
                break
    return assign


# ---------------------------------------------------------------- geometry
# Robot box in pixels; parts are tested in normalized (u, v) space or pixels.

def head_contains(u, v, shape):
    if shape == "Dome":
        if v >= 0.16:
            return 0.24 <= u <= 0.76 and v <= 0.38
        return ((u - 0.5) / 0.26) ** 2 + ((v - 0.16) / 0.13) ** 2 <= 1.0
    if shape == "Box":
        return 0.21 <= u <= 0.79 and 0.06 <= v <= 0.38
    if shape == "Tall":
        if v >= 0.14:
            return 0.28 <= u <= 0.72 and v <= 0.40
        return ((u - 0.5) / 0.22) ** 2 + ((v - 0.14) / 0.13) ** 2 <= 1.0
    if shape == "Wide":
        if v >= 0.17:
            return 0.15 <= u <= 0.85 and v <= 0.38
        return ((u - 0.5) / 0.35) ** 2 + ((v - 0.17) / 0.06) ** 2 <= 1.0
    if shape == "Hex":
        pts = [(0.30, 0.03), (0.70, 0.03), (0.80, 0.14), (0.80, 0.38), (0.20, 0.38), (0.20, 0.14)]
        inside = False
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            if (y1 > v) != (y2 > v):
                xin = (x2 - x1) * (v - y1) / (y2 - y1) + x1
                if u < xin:
                    inside = not inside
        return inside
    return False


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def visor_kind(u, v, px, py, style, box):
    x0, y0, bw, bh = box
    cx, cy = x0 + 0.5 * bw, y0 + 0.185 * bh
    if style == "Visor Bar":
        return 0.155 <= v <= 0.215 and 0.31 <= u <= 0.69
    if style == "Dual Eyes":
        return (math.hypot(px - (x0 + 0.385 * bw), py - cy) < 16 or
                math.hypot(px - (x0 + 0.615 * bw), py - cy) < 16)
    if style == "Cyclops":
        return math.hypot(px - cx, py - cy) < 17
    if style == "Cross":
        return (0.165 <= v <= 0.205 and 0.36 <= u <= 0.64) or (0.475 <= u <= 0.525 and 0.10 <= v <= 0.27)
    if style == "Scanlines":
        return 0.33 <= u <= 0.67 and any(a <= v <= b for a, b in [(0.130, 0.155), (0.175, 0.200), (0.220, 0.245)])
    if style == "Chevron":
        return 0.33 <= u <= 0.67 and abs(v - (0.13 + abs(u - 0.5) * 0.5)) < 0.020
    return False


def mouth_kind(u, v, style):
    if style == "Grille":
        return 0.295 <= v <= 0.345 and any(a <= u <= b for a, b in [(0.420, 0.455), (0.4825, 0.5175), (0.545, 0.580)])
    if style == "Smile":
        return 0.38 <= u <= 0.62 and abs(v - (0.30 + ((u - 0.5) ** 2) * 0.35)) < 0.016
    if style == "Flat":
        return 0.308 <= v <= 0.332 and 0.40 <= u <= 0.60
    if style == "Vents":
        return (0.290 <= v <= 0.305 or 0.325 <= v <= 0.340) and 0.40 <= u <= 0.60 and (int(u * 90) % 2 == 0)
    return False


def core_kind(px, py, style, box):
    x0, y0, bw, bh = box
    cx, cy = x0 + 0.5 * bw, y0 + 0.60 * bh
    du, dv = px - cx, py - cy
    d = math.hypot(du, dv)
    if style == "Ring Core":
        return 14 < d < 21 or d < 5
    if style == "Diamond Core":
        m = abs(du) + abs(dv)
        return 16 < m < 24 or m < 7
    if style == "Bar Core":
        return abs(du) < 24 and any(abs(dv - o) < 4.5 for o in (-14, 0, 14))
    if style == "Triangle Core":
        if -16 <= dv <= 16:
            halfw = (16 - dv) * 0.55
            return abs(abs(du) - halfw) < 4.0 or d < 4.5
        return False
    if style == "Dot Core":
        return d < 9
    return False


def antenna_dots(style, cx, head_top, color, accent, rng):
    """Explicit (x, y, r, color) dots above the head."""
    dots = []
    if style == "Stalk":
        for i, dy in enumerate((8, 20, 32)):
            dots.append((cx, head_top - dy, 3.4, color))
        dots.append((cx, head_top - 46, 6.0, accent))
    elif style == "Dual Stalk":
        for sx in (-30, 30):
            for t in (0.33, 0.66, 1.0):
                dots.append((cx + sx * t, head_top - 6 - 30 * t, 3.2, color))
            dots.append((cx + sx, head_top - 44, 5.2, accent))
    elif style == "Dish":
        for dy in (8, 18):
            dots.append((cx, head_top - dy, 3.2, color))
        for deg in range(195, 346, 15):
            a = math.radians(deg)
            dots.append((cx + 21 * math.cos(a), head_top - 20 + 15 * math.sin(a), 3.4, color))
        dots.append((cx, head_top - 20, 4.4, accent))
    elif style == "Fin":
        for row, dy in enumerate((8, 17, 26, 35)):
            w = 2 - row // 2
            for k in range(-w, w + 1):
                dots.append((cx + k * 7, head_top - dy, 3.3, color))
    elif style == "Crown":
        for sx in (-26, 0, 26):
            h = 46 if sx == 0 else 34
            for dy in range(8, h, 9):
                dots.append((cx + sx, head_top - dy, 3.4, color))
            dots.append((cx + sx, head_top - h - 4, 5.4, accent))
    return dots


# ---------------------------------------------------------------- drawing

def render(tid, cls, traits, attempt):
    p = CLASS_PARAMS[cls]
    rng = random.Random((MASTER_SEED ^ (tid * 2654435761) ^ (attempt * 104729)) & 0xFFFFFFFF)
    genesis = tid == 1

    if genesis:
        box = (108.0, 98.0, 296.0, 356.0)
    else:
        box = (116.0, 104.0, 280.0, 344.0)
    x0, y0, bw, bh = box
    pitch = 12.0 if genesis else p["pitch"]
    base_r = p["base_r"]

    # per-token tint jitter
    tj = rng.uniform(-7, 7)
    color = tuple(max(0, min(255, int(c + tj))) for c in p["color"])
    accent = p["accent"]

    img = Image.new("RGB", (SIZE, SIZE), BG)
    dr = ImageDraw.Draw(img)

    # --- background dot grid
    bg_style = traits["Density"]
    if bg_style == "Sparse Grid":
        bp, br, bskip = 46.0, 1.3, 0.35
    elif bg_style == "Dense Grid":
        bp, br, bskip = 25.0, 1.6, 0.05
    else:
        bp, br, bskip = 34.0, 1.5, 0.15
    bdim = 0.7 if cls == "Stealth Dot" else 1.0
    bg_col = tuple(int(c * bdim) for c in (27, 27, 30))
    y = bp / 2
    while y < SIZE:
        x = bp / 2
        while x < SIZE:
            if rng.random() > bskip:
                dr.ellipse([x - br, y - br, x + br, y + br], fill=bg_col)
            x += bp
        y += bp

    # --- robot lattice
    glow_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)) if p["glow"] else None
    gd = ImageDraw.Draw(glow_layer) if glow_layer else None

    cxr, cyr = x0 + bw / 2, y0 + bh * 0.52  # robot centroid for radius profiles
    head_top = y0 + 0.04 * bh
    head_cy = y0 + 0.20 * bh

    # arm segments in pixel space
    sh_y = y0 + 0.46 * bh
    sh_l = (x0 + 0.185 * bw, sh_y)
    sh_r = (x0 + 0.815 * bw, sh_y)
    pose = traits["_arms"]
    flip = rng.random() < 0.5
    def arm_seg(sh, side):  # side: -1 left, +1 right
        if pose == "Down":
            return (sh[0], sh[1], sh[0] + side * 6, sh[1] + 95)
        if pose == "Raised":
            return (sh[0], sh[1], sh[0] + side * 52, sh[1] - 62)
        if pose == "Out":
            return (sh[0], sh[1], sh[0] + side * 78, sh[1] + 6)
        # One Up
        up = (side == 1) if not flip else (side == -1)
        if up:
            return (sh[0], sh[1], sh[0] + side * 52, sh[1] - 62)
        return (sh[0], sh[1], sh[0] + side * 6, sh[1] + 95)
    seg_l, seg_r = arm_seg(sh_l, -1), arm_seg(sh_r, 1)
    legs_style = traits["_legs"]

    dots = []  # (x, y, r, color)
    py = y0 - pitch
    while py < y0 + bh + pitch:
        px = x0 - 44
        while px < x0 + bw + 44:
            u = (px - x0) / bw
            v = (py - y0) / bh
            inside = False
            if 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0:
                if head_contains(u, v, traits["Head"]):
                    inside = True
                elif 0.375 <= v <= 0.425 and 0.43 <= u <= 0.57:  # neck
                    inside = True
                elif 0.42 <= v <= 0.78:  # torso (slight taper)
                    hw = 0.30 + (v - 0.42) * (0.06 / 0.36)
                    inside = 0.5 - hw <= u <= 0.5 + hw
                elif legs_style == "Legs" and v > 0.78:
                    if v <= 0.96 and ((0.33 <= u <= 0.45) or (0.55 <= u <= 0.67)):
                        inside = True
                    elif 0.94 <= v <= 0.985 and ((0.30 <= u <= 0.47) or (0.53 <= u <= 0.70)):
                        inside = True
                elif legs_style == "Pedestal" and v > 0.78:
                    if 0.78 <= v <= 0.88 and 0.44 <= u <= 0.56:
                        inside = True
                    elif 0.88 <= v <= 0.97 and 0.30 <= u <= 0.70:
                        inside = True
            if not inside:  # arms live partly outside the box
                if seg_dist(px, py, *seg_l) < 13 or seg_dist(px, py, *seg_r) < 13:
                    inside = True
            if inside:
                if rng.random() < p["skip"]:
                    px += pitch
                    continue
                # classify the cell
                kind = "body"
                if 0.0 <= u <= 1.0 and 0.0 <= v <= 0.42 and visor_kind(u, v, px, py, traits["Visor"], box):
                    kind = "visor"
                elif 0.0 <= u <= 1.0 and 0.26 <= v <= 0.37 and mouth_kind(u, v, traits["_mouth"]):
                    kind = "mouth"
                elif core_kind(px, py, traits["Core"], box):
                    kind = "core"
                # radius profile
                d = min(1.0, math.hypot(px - cxr, py - cyr) / 230.0)
                prof = traits["_profile"]
                if prof == "Core Glow":
                    f = 0.75 + 0.55 * (1 - d)
                elif prof == "Edge Pulse":
                    f = 0.80 + 0.50 * d
                else:
                    f = 1.0
                r = base_r * f * rng.uniform(0.82, 1.12)
                jx = px + rng.uniform(-1.1, 1.1)
                jy = py + rng.uniform(-1.1, 1.1)
                if kind in ("visor", "core"):
                    dots.append((jx, jy, r * 1.05, accent))
                elif kind == "mouth":
                    dim = tuple(int(c * 0.5) for c in color)
                    dots.append((jx, jy, r * 0.55, dim))
                else:
                    dots.append((jx, jy, r, color))
            px += pitch
        py += pitch

    # hover trail
    if legs_style == "Hover":
        base_y = y0 + 0.80 * bh
        for i, dy in enumerate((12, 24, 37, 51)):
            spread = 52 - i * 9
            n = 5 - i
            for k in range(n):
                hx = cxr + (k - (n - 1) / 2) * (spread / max(1, n - 1) if n > 1 else 0)
                dim = tuple(int(c * (0.55 - i * 0.11)) for c in color)
                dots.append((hx, base_y + dy, base_r * (0.62 - i * 0.1), dim))

    # antenna + halo
    dots.extend(antenna_dots(traits["Antenna"], cxr, head_top, color, accent, rng))
    if genesis:
        for deg in range(0, 360, 6):
            a = math.radians(deg)
            hx, hy = cxr + 118 * math.cos(a), head_cy + 104 * math.sin(a)
            dots.append((hx, hy, 3.2 * rng.uniform(0.85, 1.15), accent))

    for (dx, dy, r, col) in dots:
        if gd is not None:
            gd.ellipse([dx - r * 1.9, dy - r * 1.9, dx + r * 1.9, dy + r * 1.9],
                       fill=(col[0], col[1], col[2], 36))
        dr.ellipse([dx - r, dy - r, dx + r, dy + r], fill=col)
    if glow_layer is not None:
        img = Image.alpha_composite(img.convert("RGBA"), glow_layer).convert("RGB")

    return img


def pick_traits(tid, cls, attempt):
    rng = random.Random((MASTER_SEED ^ (tid * 2654435761) ^ (attempt * 104729)) & 0xFFFFFFFF)
    t = dict(
        Head=rng.choice(HEADS),
        Visor=rng.choice(VISORS),
        Antenna=rng.choice(ANTENNAS),
        Core=rng.choice(CORES),
        Density=rng.choice(BG_DENSITIES),
        _mouth=rng.choice(MOUTHS),
        _arms=rng.choice(ARMS),
        _profile=rng.choice(PROFILES),
        _legs=rng.choice(LEGS),
    )
    if tid == 1:  # Genesis Dot — one-of-one composition
        t.update(Head="Dome", Visor="Cyclops", Antenna="Crown", Core="Ring Core",
                 Density="Dense Grid", _mouth="Flat", _arms="Raised", _profile="Core Glow", _legs="Legs")
    return t


def metadata(tid, cls, t):
    attrs = [
        {"trait_type": "Class", "value": cls},
        {"trait_type": "Head", "value": t["Head"]},
        {"trait_type": "Visor", "value": t["Visor"]},
        {"trait_type": "Antenna", "value": t["Antenna"]},
        {"trait_type": "Core", "value": t["Core"]},
        {"trait_type": "Density", "value": t["Density"]},
    ]
    if tid == 1:
        attrs.append({"trait_type": "Specimen", "value": "Genesis Dot"})
    return {
        "name": f"Talvio Dot Robot #{tid}",
        "description": "A Black Dot Robot from Talvio Generate — 10,000 machines resolved from a single dot field on BNB Chain.",
        "image": f"https://talviogenerate.com/nft/images/{tid}.webp",
        "attributes": attrs,
    }


def generate_range(start, end, assign, hashlog_path):
    seen = {}
    if os.path.exists(hashlog_path):
        with open(hashlog_path) as f:
            for line in f:
                h, i = line.strip().split()
                seen[h] = int(i)
    out = open(hashlog_path, "a")
    done = 0
    for tid in range(start, end + 1):
        cls = assign[tid]
        attempt = 0
        while True:
            traits = pick_traits(tid, cls, attempt)
            img = render(tid, cls, traits, attempt)
            path = os.path.join(IMG_DIR, f"{tid}.webp")
            img.save(path, "WEBP", quality=90, method=4)
            with open(path, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            if h in seen and seen[h] != tid:
                attempt += 1  # collision with another token — perturb and redo
                continue
            seen[h] = tid
            out.write(f"{h} {tid}\n")
            out.flush()
            break
        with open(os.path.join(META_DIR, f"{tid}.json"), "w") as f:
            json.dump(metadata(tid, cls, traits), f, indent=2)
        done += 1
        if done % 500 == 0:
            print(f"  ...{tid} done", flush=True)
    out.close()
    print(f"range {start}-{end} complete")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=TOTAL)
    ap.add_argument("--hashlog", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "hashes.txt"))
    a = ap.parse_args()
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(META_DIR, exist_ok=True)
    assign = class_assignment()
    generate_range(a.start, a.end, assign, a.hashlog)


if __name__ == "__main__":
    main()
