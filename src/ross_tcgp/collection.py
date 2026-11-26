"""Collection snapshots (JSON files) and the differences between them.

Every scan is saved as ``collection-YYYYMMDD-HHMMSS.json`` in the data
directory (``~/.local/share/ross_tcgp`` by default) plus a copy called
``latest.json``. A snapshot is plain JSON so it can be read by any other tool
(or by a person, or by an AI assistant that suggests decks).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import __version__
from .data import Card

SCHEMA = 1


def data_dir() -> Path:
    base = os.environ.get("ROSS_TCGP_DATA") or os.path.join(
        os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")), "ross_tcgp"
    )
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_snapshot(entries, cards: dict[str, Card], mode: str, base: dict | None = None) -> dict:
    """Turn scanned entries into a snapshot dict.

    ``base`` is the previous snapshot: in quick mode only the top of the list
    is read, so every card not seen this time keeps its previous count.
    """
    found: dict[str, dict] = {}
    if base:
        for c in base["cards"]:
            found[c["id"]] = dict(c)
    uncertain = []
    for e in entries:
        cid = e.canonical_id
        card = cards.get(cid)
        if not card:
            continue
        item = found.setdefault(
            cid,
            {
                "id": cid,
                "name": card.name,
                "set": card.set,
                "number": card.number,
                "rarity": card.rarity,
                "count": 0,
            },
        )
        if e.count is not None:
            item["count"] = e.count
        alts = sorted(set((e.card_id, *e.alternatives)) - {cid})
        if alts:
            item["reprints"] = alts
        if not e.confident or e.count is None:
            uncertain.append(
                {"id": cid, "name": card.name, "count": e.count, "score": round(e.score, 3)}
            )
    items = sorted(found.values(), key=lambda c: (c["set"], c["number"]))
    return {
        "schema": SCHEMA,
        "tool": f"ross_tcgp {__version__}",
        "scanned_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": mode,
        "unique": len(items),
        "total": sum(c["count"] for c in items),
        "cards": items,
        "uncertain": uncertain,
    }


def save(snapshot: dict, directory: Path | None = None) -> Path:
    directory = directory or data_dir()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = directory / f"collection-{stamp}.json"
    text = json.dumps(snapshot, ensure_ascii=False, indent=1)
    path.write_text(text)
    (directory / "latest.json").write_text(text)
    return path


def load(path: Path | None = None) -> dict | None:
    path = path or data_dir() / "latest.json"
    return json.loads(path.read_text()) if path.exists() else None


def counts_of(snapshot: dict | None) -> dict[str, int]:
    return {c["id"]: c["count"] for c in snapshot["cards"]} if snapshot else {}


@dataclass
class Change:
    id: str
    name: str
    rarity: str
    before: int
    after: int


def diff(old: dict | None, new: dict) -> list[Change]:
    before = counts_of(old)
    info = {c["id"]: c for c in new["cards"]}
    if old:
        for c in old["cards"]:
            info.setdefault(c["id"], c)
    after = counts_of(new)
    changes = [
        Change(cid, info[cid]["name"], info[cid].get("rarity", ""), before.get(cid, 0), after.get(cid, 0))
        for cid in sorted(set(before) | set(after))
        if before.get(cid, 0) != after.get(cid, 0)
    ]
    return changes
