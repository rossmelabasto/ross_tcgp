"""Read the copy count printed on the dark badge in each card's bottom-left corner.

The badge is a slate-blue shape with a white number in the game's font. The
font never changes, so instead of a general OCR engine (Tesseract and its
language data) we cut the number into single digits and compare each one with
small reference pictures of 0-9 taken from real screenshots ("templates").
That keeps the project free of system dependencies and is very accurate for a
fixed font.

Templates live in ``digits.npz`` next to this file; ``ross_tcgp digits``
rebuilds them from labelled samples (see the README).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .grid import Slot, badge_box

GLYPH = (10, 14)  # width, height every digit is normalised to
TEMPLATES = Path(__file__).with_name("digits.npz")


def digit_mask(screenshot: Image.Image, slot: Slot) -> np.ndarray | None:
    """Boolean image of the white digit pixels inside the badge, or None if no badge."""
    a = np.asarray(screenshot.crop(badge_box(slot)).convert("RGB"), dtype=np.int16)
    r, b = a[..., 0], a[..., 2]
    slate = (r > 45) & (r < 120) & (b - r > 12) & (b - r < 60) & (b < 160)
    cols = np.flatnonzero(slate.mean(axis=0) > 0.25)
    rows = np.flatnonzero(slate.mean(axis=1) > 0.25)
    if not cols.size or not rows.size:
        return None
    inside = a[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]
    # White-ish and neutral; anti-aliased edges blend towards the slate colour.
    return (inside.min(axis=2) > 170) & ((inside.max(axis=2) - inside.min(axis=2)) < 45)


def glyphs(mask: np.ndarray) -> list[np.ndarray]:
    """Split the digit mask into single digits (left to right), each normalised."""
    ys = np.flatnonzero(mask.any(axis=1))
    if not ys.size:
        return []
    mask = mask[ys[0] : ys[-1] + 1]
    present = mask.any(axis=0)
    out = []
    x, w = 0, mask.shape[1]
    height = mask.shape[0]
    while x < w:
        if not present[x]:
            x += 1
            continue
        start = x
        while x < w and present[x]:
            x += 1
        part = mask[:, start:x]
        # Digits sit in the middle of the badge: anything touching its left or
        # right edge is the page background showing through a rounded corner.
        if part.sum() < 6 or start <= 2 or x >= w - 2:
            continue
        if np.flatnonzero(part.any(axis=1)).size < height * 0.5:
            continue  # too short to be a digit
        rows = np.flatnonzero(part.any(axis=1))
        part = part[rows[0] : rows[-1] + 1]
        img = Image.fromarray((part * 255).astype(np.uint8)).resize(GLYPH, Image.Resampling.BOX)
        out.append(np.asarray(img, dtype=np.float32) / 255.0)
    return out


def load_templates() -> dict[str, np.ndarray]:
    if not TEMPLATES.exists():
        return {}
    data = np.load(TEMPLATES)
    return {k: data[k] for k in data.files}


def classify(glyph: np.ndarray, templates: dict[str, np.ndarray]) -> tuple[str, float]:
    """Best matching digit and its distance (mean absolute pixel difference)."""
    best, dist = "?", 1.0
    for key, tpl in templates.items():  # keys look like "3" or "3_b"
        d = float(np.abs(glyph - tpl).mean())
        if d < dist:
            best, dist = key[0], d
    return best, dist


def read_count(screenshot: Image.Image, slot: Slot, templates=None, max_dist: float = 0.18):
    """Return the copy count, or None when it can't be read reliably."""
    templates = templates if templates is not None else load_templates()
    mask = digit_mask(screenshot, slot)
    if mask is None or not templates:
        return None
    text = ""
    for g in glyphs(mask):
        digit, dist = classify(g, templates)
        if dist > max_dist:
            return None
        text += digit
    return int(text) if text.isdigit() else None
