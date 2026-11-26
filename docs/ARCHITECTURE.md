# Architecture

How `ross_tcgp` turns a phone screen into a JSON file, and why each piece is
built the way it is. Numbers come from the first real run (Samsung A56,
1080×2340, 937 cards / 393 different, 2026-11-25).

```
phone ──adb──▶ adb.py ──screenshot──▶ grid.py ──card boxes──▶ fingerprint.py ──card id──┐
                  ▲                         └──badge boxes──▶ counts.py ──copies──────────┤
                  │                                                                       ▼
                  └──────────── drag ◀────────────── scan.py (pages, merge, stop) ◀── rows
                                                         │
                                                         ▼
                                     collection.py ──▶ ~/.local/share/ross_tcgp/*.json + diff
```

## 1. Reference data (`data.py`)

- **Card list:** `cards.json` of
  [flibustier/pokemon-tcg-pocket-database](https://github.com/flibustier/pokemon-tcg-pocket-database)
  (MIT) through jsDelivr: 4,577 prints with set, number, name, rarity and packs.
- **Reference images:** the 208×290 thumbnails behind
  [cards.pokemon-tcg.exchange](https://cards.pokemon-tcg.exchange/), ~15 KB each,
  ~70 MB in total, downloaded with 6 threads into `~/.cache/ross_tcgp/thumbs`.
- **Rejected:** [TCGdex](https://tcgdex.dev/tcg-pocket) is a great API, but on
  2026-11-25 it had no images for the newest set (B2a, 131 cards) and 27 promos.
- Nothing from the game is committed to this repo; everything is fetched on the
  user's machine.

## 2. Driving the phone (`adb.py`)

- **Screenshots:** `adb exec-out screencap` *without* `-p`. With `-p` the phone
  compresses a PNG first: 2.2 s per shot. The raw dump (a 12- or 16-byte header,
  then RGBA pixels, ~10 MB) arrives in 1.1 s over USB.
- **Scrolling:** `input swipe` ends with the finger still moving, so the list
  keeps going by inertia ("fling") an unpredictable distance; the first manual
  attempt skipped rows. `input motionevent DOWN / MOVE… / sleep / UP` holds the
  finger still before lifting, so the list stops where the finger is.

## 3. Finding the cards (`grid.py`)

No fixed coordinates. The page background is a pale blue; the thin lines of pure
background between cards (gutters) give the grid on any resolution:

1. **Background mask:** bright pixels with a blue tint (`b - r` between 10 and
   45). The tint matters: trainer cards have white bodies, neutral grey
   (`b ≈ r`), which a plain "bright and flat" test confused with the page.
2. **Columns:** vertical lines that are ≥85 % background are gutters; the three
   spans between them are the columns. They are then rebuilt from the first
   column, the median width and the spacing, because a card with a bluish edge
   can eat into a gutter.
3. **Rows:** horizontal gutters across the three columns; a span between two
   gutters is a card only if its height is the card ratio (1.394) ±3 %. Cards cut
   by the sticky header or the bottom bar are skipped for free.

## 4. Identifying a card (`fingerprint.py`)

- **Fingerprint:** the card without its bottom 10 % (the copy badge covers it),
  shrunk to 16×22 RGB with box filtering, centred and scaled to unit length:
  1,056 numbers.
- **Matching:** all 4,577 reference fingerprints form one matrix; one matrix
  product gives the cosine similarity with every card, in well under a
  millisecond.
- **Why not pHash/dHash:** they are greyscale. Many prints share the same artwork
  in different frames or rarities, and colour is what tells them apart.
- **Results:** almost every card scores ≥0.99. The lowest real scores (0.67–0.89)
  were all correct: the game's floating button covering a corner, or the gold
  frames the game draws on some cards. So a card is "uncertain" only if its score
  is below 0.97 **and** the runner-up is within 0.05.
- **Reprints:** identical artwork in several sets scores the same; those ids are
  kept as `reprints`, and the smallest one is used as the stable id.

## 5. Reading the copy count (`counts.py`)

- The badge is slate blue (~75, 90, 115) with a white number. The crop keeps only
  bright neutral pixels inside the slate area, then splits them into digits by
  empty columns. Blobs touching the badge's edges are the page showing through a
  rounded corner, not digits.
- Each digit is normalised to 10×14 and compared with **templates** of the game's
  font (`digits.npz`, 17 shapes for 0–9), built from real screenshots with
  `tools/build_digit_templates.py` (cluster the shapes, label each cluster once).
- **Why not Tesseract:** it's an extra system dependency, and on the dev machine
  it had no English data at all. For one fixed font, templates are simpler and
  more accurate.

## 6. Walking the list (`scan.py`)

- **Settling:** the game **hides the badges while the list moves**. Each page is
  retaken until the card positions are the same as in the previous shot and at
  most one badge is missing.
- **Overlap and merge:** each drag moves all visible rows but one. The new page is
  glued to the previous ones by finding the longest run of shared rows, compared
  by card id and count, not by pixels: the header collapses while scrolling, so
  the real scroll distance varies. One different card per row is tolerated (holo
  animations). If nothing overlaps, it drags back half a page and retries.
- **Stopping:** two drags that add nothing = end of the list. In `--quick` mode
  (game sorted by **Recent cards**, where new cards and new copies rise to the
  top) it stops at the first page whose cards and counts all match the previous
  scan; that took 15 s in practice instead of ~5 min.
- `--save-pages` keeps every screenshot and `--from-pages` rebuilds a scan from
  them without the phone, which made it possible to tune the code without
  re-scanning.

## 7. Snapshots (`collection.py`)

JSON with `schema`, `scanned_at`, `mode`, `unique`, `total`, `cards` (id, name,
set, number, rarity, count, reprints) and `uncertain`. A quick scan starts from
the previous snapshot and only overwrites what it saw. `diff` lists new cards,
more copies and fewer copies.

**Validation of the first run:** 393 different cards and 937 copies, exactly the
total the game shows, and a dozen hand-counted cards (Golbat 10, Eevee 15,
Professor's Research 4, Magnemite 12…) all matched.

## 8. Packages (`packaging/`)

One architecture-independent package (`arch: all`) for deb, rpm and pacman, built
with nfpm: the Python package in `/usr/lib/ross-tcgp`, a small `/usr/bin/ross-tcgp`
launcher (`python3 -I`, so the user's environment can't interfere) and
dependencies on the distro's Python, Pillow, NumPy and adb. A few KB instead of
bundling a ~100 MB portable Python. `release.yml` installs and runs each package
on Arch, CachyOS, Ubuntu 22.04/24.04, Debian 13 and Fedora before publishing, then
tells [repo.rossmel.com](https://repo.rossmel.com/tcgp/) to republish.
