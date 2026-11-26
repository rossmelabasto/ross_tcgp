"""Identify a card image by comparing it with every reference thumbnail.

Each image becomes a small "fingerprint": the card shrunk to a tiny colour
picture (16x22 pixels, RGB), with the bottom strip removed because in the game
the copy-count badge covers it. The vector is centred and scaled to unit
length, so the cosine similarity between two fingerprints is just a dot
product. Matching one screenshot crop against ~4,600 references is a single
matrix multiplication, which takes well under a millisecond.

Why not a perceptual hash (pHash/dHash)? Those work on greyscale and many TCG
Pocket prints share the same artwork in different frames or rarities, where
colour is what tells them apart. The tiny-RGB approach keeps that colour.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .data import Card, cache_dir

SIZE = (16, 22)  # width, height of the fingerprint picture
KEEP = 0.90  # keep the top 90% of the card (the badge covers the bottom)
INDEX_VERSION = 1


def fingerprint(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB")
    w, h = img.size
    img = img.crop((0, 0, w, int(h * KEEP))).resize(SIZE, Image.Resampling.BOX)
    v = np.asarray(img, dtype=np.float32).reshape(-1)
    v -= v.mean()
    n = np.linalg.norm(v)
    return v / n if n else v


@dataclass
class Match:
    card_id: str
    score: float  # cosine similarity, 1.0 = identical
    margin: float  # gap to the best match with a different, non-identical card
    alternatives: tuple[str, ...] = ()  # reprints: other ids with the same image


class Index:
    def __init__(self, ids: list[str], matrix: np.ndarray):
        self.ids = ids
        self.matrix = matrix

    @classmethod
    def path(cls) -> Path:
        return cache_dir() / f"index-v{INDEX_VERSION}.npz"

    @classmethod
    def build(cls, cards: list[Card]) -> "Index":
        ids, rows = [], []
        for card in cards:
            p = card.thumb_path()
            if p.exists():
                with Image.open(p) as im:
                    rows.append(fingerprint(im))
                ids.append(card.id)
        index = cls(ids, np.stack(rows).astype(np.float32))
        np.savez_compressed(cls.path(), ids=np.array(ids), matrix=index.matrix)
        return index

    @classmethod
    def load(cls) -> "Index | None":
        p = cls.path()
        if not p.exists():
            return None
        data = np.load(p)
        return cls([str(i) for i in data["ids"]], data["matrix"])

    def match(self, img: Image.Image, reprint_eps: float = 0.003) -> Match:
        scores = self.matrix @ fingerprint(img)
        order = np.argsort(scores)[::-1][:12]
        best = order[0]
        top = scores[best]
        # Reprints (same artwork in several sets) score the same: keep them as
        # alternatives instead of pretending we can tell them apart.
        same = [i for i in order[1:] if top - scores[i] <= reprint_eps]
        others = [i for i in order[1:] if top - scores[i] > reprint_eps]
        runner = others[0] if others else order[-1]
        return Match(
            self.ids[best],
            float(top),
            float(top - scores[runner]),
            tuple(self.ids[i] for i in same),
        )
