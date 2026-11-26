"""Export a collection snapshot to files other trackers can import.

Formats:

``csv`` / ``packprophet``
    One row per owned card: ``set,number,card_id,name,rarity,quantity``. It's
    the format PackProphet (https://packprophet.spibane.com, Collection → Import)
    reads, and a plain CSV for spreadsheets. PackProphet numbers cards like the
    flibustier database we use, so no id translation is needed.

``tcg-tracker``
    For https://tcgpocketcollectiontracker.com (Import, logged in). That site
    keys cards by its own numeric ``InternalId``, so its card list is
    downloaded fresh on every export (never a stale copy: a wrong id would put
    counts on the wrong cards) and every card is written, owned or not, because
    its import *replaces* the collection there. Reprints share an InternalId
    and get the same count.
"""

from __future__ import annotations

import csv
import io
import json

from .data import _get

TRACKER_CARDS_URL = (
    "https://raw.githubusercontent.com/marcelpanse/tcg-pocket-collection-tracker/"
    "main/frontend/assets/cards.json"
)
FORMATS = ("csv", "packprophet", "tcg-tracker")


def _owned(snapshot: dict) -> list[dict]:
    return [c for c in snapshot["cards"] if c.get("count", 0) > 0]


def to_packprophet(snapshot: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["set", "number", "card_id", "name", "rarity", "quantity"])
    for c in _owned(snapshot):
        w.writerow([c["set"], c["number"], f"{c['set']}-{c['number']}", c["name"], c["rarity"], c["count"]])
    return buf.getvalue()


def tracker_id(card_id: str) -> str:
    """Our id (``A1-096``, ``PROMO-A-001``) in the tracker's scheme (``A1-96``, ``P-A-1``)."""
    set_id, _, number = card_id.rpartition("-")
    if set_id.endswith("-"):  # negative numbers, e.g. "SP1--1"
        set_id, number = set_id[:-1], "-" + number
    return f"{set_id.replace('PROMO-', 'P-')}-{int(number)}"


def to_tcg_tracker(snapshot: dict, tracker_cards: list[dict] | None = None) -> tuple[str, list[str]]:
    """Return (csv text, ids of owned cards that the tracker doesn't know)."""
    cards: list[dict] = (
        tracker_cards if tracker_cards is not None else json.loads(_get(TRACKER_CARDS_URL, timeout=60))
    )
    internal = {c["card_id"]: c["internal_id"] for c in cards}

    counts: dict[int, int] = {}
    unknown = []
    for c in _owned(snapshot):
        ids = [c["id"], *c.get("reprints", [])]
        mapped = [internal[t] for t in map(tracker_id, ids) if t in internal]
        if not mapped:
            unknown.append(c["id"])
        for iid in mapped:
            counts[iid] = max(counts.get(iid, 0), c["count"])

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["Id", "CardName", "InternalId", "NumberOwned", "Expansion", "Pack", "Rarity", "Collected"])
    for c in cards:
        n = counts.get(c["internal_id"], 0)
        w.writerow([
            c["card_id"], c.get("name", ""), c["internal_id"], n,
            c.get("expansion", ""), c.get("pack", ""), c.get("rarity", ""),
            "TRUE" if n > 0 else "FALSE",
        ])
    return buf.getvalue(), unknown
