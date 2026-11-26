"""Tests that don't need a phone or any game image (synthetic pictures only)."""

import numpy as np
from PIL import Image, ImageDraw

from ross_tcgp import counts, grid
from ross_tcgp.collection import build_snapshot, diff
from ross_tcgp.data import Card
from ross_tcgp.fingerprint import Index, fingerprint
from ross_tcgp.scan import Entry, merge

BG = (228, 237, 245)  # the game's pale blue page background


def fake_page(rows=3, top=300, w=1080, h=2340):
    """A screenshot-like image: 3 columns of coloured 'cards' on the background."""
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    cw, gap, left = 316, 16, 49
    ch = round(cw * grid.CARD_RATIO)
    rng = np.random.default_rng(0)
    for r in range(rows):
        for c in range(3):
            x0, y0 = left + c * (cw + gap), top + r * (ch + gap)
            d.rectangle((x0, y0, x0 + cw - 1, y0 + ch - 1), fill=tuple(int(v) for v in rng.integers(0, 150, 3)))
    return img, cw, ch


def test_grid_finds_full_cards_only():
    img, cw, ch = fake_page(rows=4, top=900)  # 4th row runs off the bottom
    slots = grid.find_slots(img)
    assert len(slots) == 9
    assert all(abs(s.width - cw) <= 2 and abs(s.height - ch) <= 2 for s in slots)
    assert [s.col for s in slots[:3]] == [0, 1, 2]


def test_fingerprint_matches_itself():
    cards = [Image.new("RGB", (208, 290), c) for c in [(200, 30, 30), (30, 200, 30), (30, 30, 200)]]
    for im, color in zip(cards, [(0, 0, 0), (255, 255, 255), (0, 0, 0)]):
        ImageDraw.Draw(im).ellipse((40, 40, 160, 200), fill=color)
    index = Index(["a", "b", "c"], np.stack([fingerprint(c) for c in cards]))
    match = index.match(cards[1].resize((316, 440)))
    assert match.card_id == "b" and match.score > 0.99


def test_digit_split():
    mask = np.zeros((20, 40), bool)
    mask[3:17, 8:13] = True  # a "1"
    mask[3:17, 20:29] = True  # another glyph
    assert len(counts.glyphs(mask)) == 2


def e(cid, n=1):
    return Entry(cid, n, 1.0, 0.5)


def test_merge_uses_shared_rows():
    acc = [[e("a"), e("b"), e("c")], [e("d"), e("e"), e("f")]]
    page = [[e("d"), e("e"), e("f")], [e("g"), e("h"), e("i")]]
    assert merge(acc, page) == 1
    assert [x.card_id for x in acc[-1]] == ["g", "h", "i"]
    assert merge(acc, [[e("x"), e("y"), e("z")]]) is None  # no overlap


def test_snapshot_and_diff():
    cards = {"A1-001": Card("A1", 1, "Bulbasaur", "C"), "A1-002": Card("A1", 2, "Ivysaur", "U")}
    old = build_snapshot([e("A1-001", 1)], cards, "full")
    new = build_snapshot([e("A1-001", 2), e("A1-002", 1)], cards, "full")
    assert new["total"] == 3
    changes = {c.id: (c.before, c.after) for c in diff(old, new)}
    assert changes == {"A1-001": (1, 2), "A1-002": (0, 1)}
    quick = build_snapshot([e("A1-002", 2)], cards, "quick", base=new)
    assert quick["total"] == 4  # Bulbasaur kept from the base snapshot
