#!/usr/bin/env python3
"""Verify the Talvio Generate collection: file completeness, SHA-256 uniqueness,
class counts from metadata, total size."""
import hashlib
import json
import os
from collections import Counter

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "collection")
TOTAL = 10000

hashes = {}
dupes = []
missing = []
total_bytes = 0
classes = Counter()
specimen = []

for tid in range(1, TOTAL + 1):
    ip = os.path.join(BASE, "images", f"{tid}.webp")
    mp = os.path.join(BASE, "metadata", f"{tid}.json")
    if not (os.path.exists(ip) and os.path.exists(mp)):
        missing.append(tid)
        continue
    with open(ip, "rb") as f:
        data = f.read()
    total_bytes += len(data)
    h = hashlib.sha256(data).hexdigest()
    if h in hashes:
        dupes.append((tid, hashes[h]))
    hashes[h] = tid
    with open(mp) as f:
        meta = json.load(f)
    attrs = {a["trait_type"]: a["value"] for a in meta["attributes"]}
    classes[attrs["Class"]] += 1
    if attrs.get("Specimen") == "Genesis Dot":
        specimen.append(tid)

print(f"images+metadata present: {TOTAL - len(missing)}/{TOTAL}")
print(f"missing: {missing[:10] if missing else 'none'}")
print(f"unique SHA-256 hashes: {len(hashes)}/{TOTAL}")
print(f"duplicate pairs: {dupes if dupes else 'none'}")
print(f"class counts: {dict(classes)}")
print(f"Genesis Dot specimen tokens: {specimen}")
print(f"total image size: {total_bytes / 1e6:.1f} MB ({total_bytes} bytes)")
