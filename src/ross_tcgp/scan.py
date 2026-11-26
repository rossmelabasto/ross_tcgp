"""Walk through the "My Cards" grid on the phone and read every card.

Flow for each page:
1. take a screenshot and wait until it is "settled": the game hides the
   copy-count badges while the list moves, so we retake it until the badges
   are visible and nothing moved between two shots;
2. find the fully visible cards (grid.py), identify each one (fingerprint.py)
   and read its copy count (counts.py);
3. drag the list up by all-but-one visible rows, so consecutive pages share at
   least one row;
4. glue the new page to what we have by finding that shared row (comparing
   the identified cards, not pixels, because the header collapses and the
   exact scroll distance varies).
We stop when a drag no longer brings new rows (end of the list), or, in
"quick" mode, when a whole page matches what the previous scan already knew.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from . import counts, grid
from .adb import Device
from .fingerprint import Index


@dataclass
class Entry:
    card_id: str
    count: int | None
    score: float
    margin: float
    alternatives: tuple[str, ...] = ()

    @property
    def canonical_id(self) -> str:
        """Stable id for reprints: the smallest of the identical-looking ids."""
        return min((self.card_id, *self.alternatives))

    @property
    def confident(self) -> bool:
        # A near-perfect score is enough. A lower score is still fine when the
        # runner-up is far behind: the floating button or the game's gold
        # frames lower the score of a card without making it ambiguous.
        return self.score >= 0.97 or (self.score >= 0.60 and self.margin >= 0.05)


Row = list[Entry]


@dataclass
class ScanResult:
    rows: list[Row] = field(default_factory=list)
    pages: int = 0
    stopped_because: str = ""

    def entries(self) -> list[Entry]:
        return [e for row in self.rows for e in row]


def _is_empty(img: Image.Image, slot: grid.Slot) -> bool:
    return grid.background_mask(img.crop(slot.box)).mean() > 0.5


def read_page(img: Image.Image, index: Index, templates) -> tuple[list[Row], int]:
    """Identify every fully visible card. Returns (rows, number of badges read)."""
    rows: dict[int, Row] = {}
    badges = 0
    for slot in grid.find_slots(img):
        if _is_empty(img, slot):
            continue
        match = index.match(img.crop(slot.box))
        count = counts.read_count(img, slot, templates)
        # "Badge visible" = it has digit-shaped pixels, even if we can't read them.
        mask = counts.digit_mask(img, slot)
        badges += mask is not None and bool(counts.glyphs(mask))
        rows.setdefault(slot.row, []).append(
            Entry(match.card_id, count, match.score, match.margin, match.alternatives)
        )
    return [rows[k] for k in sorted(rows)], badges


def settled_page(device: Device, index: Index, templates, tries: int = 6):
    """Screenshot until the badges are visible and the grid stopped moving.

    One badge may stay unreadable (e.g. hidden behind the floating button), so
    "settled" means: same card positions as the previous shot and at most one
    badge missing.
    """
    previous = None
    img = device.screenshot()
    for _ in range(tries):
        rows, badges = read_page(img, index, templates)
        n = sum(len(r) for r in rows)
        boxes = [s.box for s in grid.find_slots(img)]
        if n and badges >= n - 1 and boxes == previous:
            return img, rows
        previous = boxes
        time.sleep(0.2)
        img = device.screenshot()
    rows, _ = read_page(img, index, templates)
    return img, rows


def _same_row(a: Row, b: Row) -> bool:
    """Rows match if they have the same length and at most one card differs.

    One mismatch is tolerated because animated holo effects can, rarely, make
    the same card identify differently in two screenshots.
    """
    if len(a) != len(b):
        return False
    diff = sum(x.canonical_id != y.canonical_id or x.count != y.count for x, y in zip(a, b))
    return diff <= (1 if len(a) == 3 else 0)


def merge(acc: list[Row], page: list[Row]) -> int | None:
    """Append ``page`` to ``acc`` using their shared rows. Returns new rows added.

    None means no overlap was found (the drag skipped rows).
    """
    if not acc:
        acc.extend(page)
        return len(page)
    for k in range(min(len(acc), len(page)), 0, -1):
        if all(_same_row(acc[-k + i], page[i]) for i in range(k)):
            new = page[k:]
            acc.extend(new)
            return len(new)
    return None


def read_saved_pages(paths: list[Path], index: Index) -> ScanResult:
    """Rebuild a scan from screenshots saved with ``--save-pages`` (no phone needed)."""
    templates = counts.load_templates()
    result = ScanResult()
    for path in paths:
        with Image.open(path) as im:
            page, _ = read_page(im.convert("RGB"), index, templates)
        result.pages += 1
        if page and merge(result.rows, page) is None:
            result.stopped_because = f"{path.name} doesn't overlap the previous page"
    result.stopped_because = result.stopped_because or "all pages read"
    return result


def scroll_to_top(device: Device, img: Image.Image, flings: int = 6) -> None:
    w, h = img.size
    for _ in range(flings):
        device.shell(f"input swipe {w // 2} {int(h * 0.35)} {w // 2} {int(h * 0.85)} 120")
        time.sleep(0.25)
    time.sleep(1.0)


def scan(
    device: Device,
    index: Index,
    known: dict[str, int] | None = None,
    quick: bool = False,
    from_top: bool = True,
    max_pages: int = 400,
    save_dir: Path | None = None,
    progress=None,
) -> ScanResult:
    templates = counts.load_templates()
    result = ScanResult()
    img = device.screenshot()
    # Never touch the phone unless the card grid is on screen: the game could be
    # on any other screen (a battle, the shop…) and drags there do who knows what.
    if not grid.find_slots(img):
        result.stopped_because = "no card grid on screen: open 'My Cards' in the game"
        return result
    if from_top:
        scroll_to_top(device, img)
    w, h = img.size
    no_progress = 0

    while result.pages < max_pages:
        img, page = settled_page(device, index, templates)
        result.pages += 1
        if save_dir:
            img.save(save_dir / f"page-{result.pages:03d}.png")
        if not page:
            result.stopped_because = "no cards on screen (wrong screen?)"
            break

        added = merge(result.rows, page)
        if added is None:
            # The drag went too far: go back half a page and try again.
            device.drag(w // 2, int(h * 0.40), int(h * 0.65))
            continue
        if progress:
            progress(result)

        if quick and known is not None and result.pages > 1:
            page_entries = [e for row in page for e in row]
            if all(known.get(e.canonical_id) == e.count for e in page_entries):
                result.stopped_because = "quick mode: reached cards already known"
                break

        no_progress = no_progress + 1 if added == 0 else 0
        if no_progress >= 2:
            result.stopped_because = "end of the list"
            break

        # Drag by all visible rows but one, measured on this page.
        slots = grid.find_slots(img)
        tops = sorted({s.box[1] for s in slots})
        if len(tops) >= 2:
            pitch = int(np.median(np.diff(tops)))
            distance = pitch * (len(tops) - 1)
        else:
            distance = int(h * 0.25)
        start = int(h * 0.85)
        device.drag(w // 2, start, max(start - distance, int(h * 0.12)))
    else:
        result.stopped_because = f"stopped after {max_pages} pages"
    return result
