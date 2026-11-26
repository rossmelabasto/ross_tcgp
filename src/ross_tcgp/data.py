"""Card database: metadata and reference thumbnails.

Metadata comes from flibustier/pokemon-tcg-pocket-database (MIT), served from
jsDelivr. Thumbnails come from the CDN behind that project's public site.
Nothing is redistributed by this repo: everything is downloaded on demand into
a local cache (``~/.cache/ross_tcgp`` by default).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

CARDS_URL = "https://cdn.jsdelivr.net/npm/pokemon-tcg-pocket-database/dist/cards.json"
SETS_URL = "https://cdn.jsdelivr.net/npm/pokemon-tcg-pocket-database/dist/sets.json"
THUMB_URL = "https://cdn.pokemon-tcg.exchange/images/thumbnails/{set}/{number}.webp"
USER_AGENT = "ross_tcgp (+https://github.com/rossmelabasto/ross_tcgp)"


def cache_dir() -> Path:
    base = os.environ.get("ROSS_TCGP_CACHE") or os.path.join(
        os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "ross_tcgp"
    )
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class Card:
    set: str
    number: int
    name: str
    rarity: str
    packs: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return f"{self.set}-{self.number:03d}"

    @property
    def thumb_url(self) -> str:
        return THUMB_URL.format(set=self.set, number=self.number)

    def thumb_path(self) -> Path:
        return cache_dir() / "thumbs" / self.set / f"{self.number}.webp"


def _get(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def load_cards(refresh: bool = False) -> list[Card]:
    """Return every known card, downloading the metadata once (or on refresh)."""
    path = cache_dir() / "cards.json"
    if refresh or not path.exists():
        path.write_bytes(_get(CARDS_URL))
    raw = json.loads(path.read_text())
    return [
        Card(
            set=c["set"],
            number=int(c["number"]),
            name=c["name"],
            rarity=c.get("rarity", ""),
            packs=tuple(c.get("packs") or ()),
        )
        for c in raw
    ]


def download_thumbs(cards: list[Card], workers: int = 6, progress=None) -> list[Card]:
    """Download missing thumbnails. Returns the cards whose image could not be fetched."""
    missing = [c for c in cards if not c.thumb_path().exists()]
    failed: list[Card] = []

    def fetch(card: Card) -> None:
        dest = card.thumb_path()
        dest.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(3):
            try:
                data = _get(card.thumb_url)
                if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                    tmp = dest.with_suffix(".part")
                    tmp.write_bytes(data)
                    tmp.replace(dest)
                    return
                break  # not an image: don't retry
            except urllib.error.HTTPError as err:
                if err.code == 404:
                    break
                time.sleep(1 + attempt)
            except (urllib.error.URLError, TimeoutError):
                time.sleep(1 + attempt)
        failed.append(card)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, _ in enumerate(pool.map(fetch, missing), 1):
            if progress:
                progress(i, len(missing))
    return failed
