"""Find the cards (and their copy-count badges) in a "My Cards" screenshot.

The collection screen is a 3-column grid of cards on a pale, low-saturation
background. Instead of hard-coding pixel positions for one phone, we look for
the *gutters*: the thin lines of pure background between cards. Cards are
whatever sits between two gutters and has the right shape, so the same code
works on any resolution, and partially hidden cards (under the sticky header
or the bottom bar) are skipped because their height is wrong.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

CARD_RATIO = 1.394  # height / width of a card (the reference thumbnails are 208x290)
GUTTER_FILL = 0.85  # a gutter line is at least this fraction of background pixels


@dataclass(frozen=True)
class Slot:
    """One fully visible card in a screenshot (pixel box: left, top, right, bottom)."""

    box: tuple[int, int, int, int]
    row: int
    col: int

    @property
    def width(self) -> int:
        return self.box[2] - self.box[0]

    @property
    def height(self) -> int:
        return self.box[3] - self.box[1]


def background_mask(img: Image.Image) -> np.ndarray:
    """True where a pixel looks like the pale blue-grey page background."""
    a = np.asarray(img.convert("RGB"), dtype=np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # Pale and slightly blue: white card bodies are neutral grey (b ~= r),
    # the page background always has a blue tint.
    bright = (r > 175) & (g > 185) & (b > 195)
    bluish = (b - r >= 10) & (b - r <= 45) & (b >= g)
    return bright & bluish


def _runs(flags: np.ndarray, min_len: int = 1) -> list[tuple[int, int]]:
    """Return [start, end) ranges where ``flags`` is True for at least ``min_len`` items."""
    padded = np.concatenate(([False], flags.astype(bool), [False]))
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    pairs = edges.reshape(-1, 2)
    return [(int(a), int(b)) for a, b in pairs if b - a >= min_len]


def _between(gutters: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """The spans between consecutive gutters."""
    return [(g0[1], g1[0]) for g0, g1 in zip(gutters, gutters[1:])]


def find_columns(bg: np.ndarray) -> list[tuple[int, int]]:
    """x-ranges of the 3 card columns, found from the vertical gutters."""
    h, w = bg.shape
    band = bg[int(h * 0.30) : int(h * 0.90)]
    gutters = _runs(band.mean(axis=0) > GUTTER_FILL, 3)
    spans = [s for s in _between(gutters) if 0.22 * w < s[1] - s[0] < 0.40 * w]
    return spans if len(spans) == 3 else []


def find_slots(img: Image.Image) -> list[Slot]:
    """Return every fully visible card, ordered row by row, left to right."""
    bg = background_mask(img)
    columns = find_columns(bg)
    if not columns:
        return []
    # A card with a bluish edge can eat into a gutter, so rebuild the columns
    # from the most reliable measurements: the first column's left edge, the
    # median width and the left-to-left spacing of the first two columns.
    width = int(np.median([c[1] - c[0] for c in columns]))
    pitch = columns[1][0] - columns[0][0]
    columns = [(columns[0][0] + i * pitch, columns[0][0] + i * pitch + width) for i in range(3)]
    left, right = columns[0][0], columns[-1][1]
    expected = width * CARD_RATIO

    gutters = _runs(bg[:, left:right].mean(axis=1) > GUTTER_FILL, 4)
    rows = [s for s in _between(gutters) if abs((s[1] - s[0]) - expected) <= expected * 0.03]

    return [
        Slot((x0, y0, x1, y1), r, c)
        for r, (y0, y1) in enumerate(rows)
        for c, (x0, x1) in enumerate(columns)
    ]


def badge_box(slot: Slot) -> tuple[int, int, int, int]:
    """Region of the dark copy-count badge in the card's bottom-left corner."""
    x0, _, _, y1 = slot.box
    return (x0, y1 - int(slot.height * 0.095), x0 + int(slot.width * 0.40), y1)
