# ross_tcgp

**English** · [Español](README.es.md)

Read your **Pokémon TCG Pocket** collection straight from your Android phone
and save it as a JSON file, from the terminal, for free, without typing a
single card by hand.

```
$ ross-tcgp scan
Scanning… (don't touch the phone)
  page 69: 393 cards read
  stopped: end of the list
Saved 393 different cards (937 copies) to ~/.local/share/ross_tcgp/collection-20261125-232730.json
New cards:
  A2b-071      Red                          U    0 -> 1
More copies:
  A1-225       Sabrina                      U    2 -> 3
```

> Fan project. Not affiliated with, endorsed or sponsored by Nintendo, The
> Pokémon Company, Creatures, GAME FREAK or DeNA. Pokémon and its names are
> trademarks of their respective owners. This repository contains **no game
> assets**: card images are downloaded to your own machine on first use.

## Why

The game has no export and no API. Existing trackers make you add cards by
hand or upload screenshots one by one in a browser. `ross_tcgp` drives the
phone itself over `adb`: it scrolls the **My Cards** screen, takes
screenshots, recognises every card and reads how many copies you own.

Once you have a scan, `ross-tcgp scan --quick` only reads what changed since
last time (sort the list by **Recent cards** in the game first), so checking
your new packs takes seconds.

## How it works

| Step | What happens | Module |
| --- | --- | --- |
| Drive the phone | `adb exec-out screencap` for screenshots (raw pixels, ~1 s), `input motionevent` drags that stop dead instead of flinging | `adb.py` |
| Find the cards | The page background is a pale blue; the thin gutters of pure background between cards give the grid on any resolution. Cards cut by the header or the bottom bar are skipped because their height is wrong | `grid.py` |
| Identify each card | Every card is shrunk to a 16×22 colour "fingerprint" and compared (cosine similarity, one matrix product) with the fingerprints of all ~4,600 official card images | `fingerprint.py` |
| Read the copy count | The white number on the dark badge is cut into digits and each one is compared with templates of the game's font, no OCR engine needed | `counts.py` |
| Walk the whole list | Each drag moves all visible rows but one; pages are glued together on that shared row (by card, not by pixels). The game hides the badges while scrolling, so every page is retaken until it is still and the badges are back | `scan.py` |
| Save and compare | JSON snapshots with a diff against the previous one | `collection.py` |

The reasoning behind every piece is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

Reprints (identical artwork in several sets, such as some trainers) can't be
told apart from an image; they are stored under one id with the others listed
in `reprints`.

## Requirements

- Python 3.10+
- [`adb`](https://developer.android.com/tools/releases/platform-tools)
  and an Android phone with **USB debugging** enabled
- Pokémon TCG Pocket installed and open on **My Cards**

Tested on a 1080×2340 phone (Samsung A56). The grid detection measures the
screen instead of using fixed coordinates, so other sizes should work; please
open an issue if yours doesn't.

## Install

From [repo.rossmel.com](https://repo.rossmel.com/tcgp/) (signed packages; add the
[repository](https://repo.rossmel.com/repository/) once):

```bash
sudo pacman -Syu ross-tcgp                          # Arch, CachyOS
sudo apt update && sudo apt install ross-tcgp       # Ubuntu, Debian
sudo dnf install ross-tcgp                          # Fedora
ross-tcgp update   # downloads card data + images (~70 MB, once)
```

They use your system's Python, Pillow, NumPy and adb. From source:

```bash
git clone https://github.com/rossmelabasto/ross_tcgp
cd ross_tcgp
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/ross-tcgp update   # downloads card data + images (~70 MB, once)
```

## Usage

```bash
ross-tcgp scan             # full scan, from the top of the list
ross-tcgp scan --quick     # only new cards (sort by "Recent cards" in the game)
ross-tcgp show             # list the latest scan
ross-tcgp show --name pika # filter by name
ross-tcgp show --json      # raw JSON, e.g. to feed another tool
ross-tcgp diff OLD.json    # compare an old scan with the latest
ross-tcgp export           # CSV for PackProphet or a spreadsheet
ross-tcgp export -f tcg-tracker   # CSV for tcgpocketcollectiontracker.com
ross-tcgp update           # refresh card data after a new set comes out
```

Don't touch the phone while it scans. On a Samsung A56 a full scan of 937
cards (393 different) took about 5 minutes and matched the game's own total
exactly; a quick scan takes about 15 seconds.

### Output

```json
{
 "schema": 1,
 "scanned_at": "2026-11-25T23:30:00-04:00",
 "mode": "full",
 "unique": 393,
 "total": 937,
 "cards": [
  {"id": "A1-096", "name": "Pikachu ex", "set": "A1", "number": 96, "rarity": "RR", "count": 2}
 ],
 "uncertain": []
}
```

`uncertain` lists cards whose image or count was hard to read, so you can
double-check them.

### Use it in other trackers

`ross-tcgp export` writes a CSV you can import elsewhere:

- **[PackProphet](https://packprophet.spibane.com)** (which pack to open next,
  set progress): `ross-tcgp export`, then *Collection → Import*. Runs in your
  browser, no account, with a preview before saving.
- **[TCG Pocket Collection Tracker](https://tcgpocketcollectiontracker.com)**
  (trades, friends): `ross-tcgp export -f tcg-tracker`, then log in → *Import*.
  That site uses its own card ids, so its card list is downloaded fresh on every
  export, and the file lists every card (owned or not) because **its import
  replaces your collection there**.

## Development

```bash
.venv/bin/pip install -e . pytest
.venv/bin/pytest                         # synthetic tests, no phone needed
ross-tcgp scan --save-pages pages/       # keep the screenshots of a scan
ross-tcgp scan --from-pages pages/       # re-read them offline after a code change
```

The copy-count digits are recognised with small templates
(`src/ross_tcgp/digits.npz`) built from real screenshots with
`tools/build_digit_templates.py`; see that file if the game changes its font.

## Data sources

- Card list and metadata:
  [flibustier/pokemon-tcg-pocket-database](https://github.com/flibustier/pokemon-tcg-pocket-database) (MIT)
- Reference thumbnails: the CDN of that project's site,
  [cards.pokemon-tcg.exchange](https://cards.pokemon-tcg.exchange/)
- Also worth knowing: [TCGdex](https://tcgdex.dev/tcg-pocket), a free API with
  Pocket cards in 9 languages

Everything is cached in `~/.cache/ross_tcgp`. Scans live in
`~/.local/share/ross_tcgp`.

## Related projects

- [PackProphet](https://github.com/Spibane/PackProphet): web tracker with
  screenshot import and pack advice
- [tcg-pocket-collection-tracker](https://github.com/marcelpanse/tcg-pocket-collection-tracker)
  and its [screenshot scanner](https://github.com/1vcian/Pokemon-TCGP-Card-Scanner)

`ross_tcgp` is complementary: it automates the capture on the phone and
works offline from the terminal.

## Is it allowed?

`ross_tcgp` only scrolls the collection screen and takes screenshots, like
you would by hand. It doesn't play, open packs, read game memory or talk to
the game's servers. Still, automating input is your responsibility: read the
game's terms of service.

## License

[MIT](LICENSE) © 2026 Rossmel Abasto
