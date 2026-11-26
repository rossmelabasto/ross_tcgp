"""Command line interface: ``ross-tcgp <command>``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, collection, data
from .fingerprint import Index


def _bar(done: int, total: int) -> None:
    width = 30
    fill = int(width * done / max(total, 1))
    print(f"\r  [{'#' * fill}{'.' * (width - fill)}] {done}/{total}", end="", flush=True)
    if done == total:
        print()


def cmd_update(args) -> int:
    print("Downloading card list…")
    cards = data.load_cards(refresh=True)
    print(f"  {len(cards)} cards known")
    print("Downloading reference images (only the missing ones)…")
    failed = data.download_thumbs(cards, progress=_bar)
    if failed:
        print(f"  {len(failed)} images not available yet (new or unreleased cards)")
    print("Building the image index…")
    index = Index.build(cards)
    print(f"  done: {len(index.ids)} cards can be recognised")
    return 0


def _load_index() -> Index:
    index = Index.load()
    if index is None:
        print("No image index yet: running `ross-tcgp update` first.\n")
        cmd_update(None)
        index = Index.load()
    return index


def _print_changes(changes) -> None:
    if not changes:
        print("No changes since the previous scan.")
        return
    new = [c for c in changes if c.before == 0]
    more = [c for c in changes if c.before and c.after > c.before]
    less = [c for c in changes if c.after < c.before]
    for title, group in (("New cards", new), ("More copies", more), ("Fewer copies", less)):
        if group:
            print(f"{title}:")
            for c in group:
                print(f"  {c.id:<12} {c.name:<28} {c.rarity:<4} {c.before} -> {c.after}")


def cmd_scan(args) -> int:
    from .adb import AdbError, Device, GAME_PACKAGE
    from .scan import read_saved_pages, scan

    if args.from_pages:
        index = _load_index()
        cards = {c.id: c for c in data.load_cards()}
        pages = sorted(Path(args.from_pages).glob("*.png"))
        result = read_saved_pages(pages, index)
        print(f"Read {len(pages)} saved pages: {result.stopped_because}")
        snap = collection.build_snapshot(result.entries(), cards, "pages")
        if args.out:
            path = collection.save(snap, Path(args.out))
            print(f"Saved {snap['unique']} different cards ({snap['total']} copies) to {path}")
        else:
            print(f"{snap['unique']} different cards ({snap['total']} copies); use --out to save")
        return 0

    try:
        device = Device(args.serial)
        pkg = device.foreground_package()
    except AdbError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    if pkg != GAME_PACKAGE:
        print("Open Pokémon TCG Pocket on the phone, on the 'My Cards' screen, then run again.")
        return 1

    index = _load_index()
    cards = {c.id: c for c in data.load_cards()}
    previous = collection.load()
    quick = args.quick and previous is not None
    if args.quick and previous is None:
        print("No previous scan: doing a full scan instead of a quick one.")

    save_dir = None
    if args.save_pages:
        save_dir = Path(args.save_pages)
        save_dir.mkdir(parents=True, exist_ok=True)

    def progress(result):
        n = sum(len(r) for r in result.rows)
        print(f"\r  page {result.pages}: {n} cards read", end="", flush=True)

    print("Scanning… (don't touch the phone)")
    result = scan(
        device,
        index,
        known=collection.counts_of(previous) if quick else None,
        quick=quick,
        from_top=not args.no_top,
        save_dir=save_dir,
        progress=progress,
    )
    print(f"\n  stopped: {result.stopped_because}")
    if not result.entries():
        print("No cards were read, so nothing was saved.")
        return 1

    mode = "quick" if quick else "full"
    snap = collection.build_snapshot(
        result.entries(), cards, mode, base=previous if quick else None
    )
    path = collection.save(snap, Path(args.out) if args.out else None)
    print(f"Saved {snap['unique']} different cards ({snap['total']} copies) to {path}")
    if snap["uncertain"]:
        print(f"  {len(snap['uncertain'])} cards were hard to read; see 'uncertain' in the file.")
    _print_changes(collection.diff(previous, snap))
    return 0


def cmd_diff(args) -> int:
    old = collection.load(Path(args.old))
    new = collection.load(Path(args.new)) if args.new else collection.load()
    if new is None:
        print("No scan found.", file=sys.stderr)
        return 1
    _print_changes(collection.diff(old, new))
    return 0


def cmd_show(args) -> int:
    snap = collection.load(Path(args.file) if args.file else None)
    if snap is None:
        print("No scan yet: run `ross-tcgp scan`.", file=sys.stderr)
        return 1
    if args.json:
        json.dump(snap, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    print(f"{snap['unique']} different cards, {snap['total']} copies (scanned {snap['scanned_at']})")
    for c in snap["cards"]:
        if args.name and args.name.lower() not in c["name"].lower():
            continue
        print(f"  {c['id']:<12} {c['name']:<28} {c['rarity']:<4} x{c['count']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ross-tcgp",
        description="Read your Pokémon TCG Pocket collection from an Android phone over adb.",
    )
    parser.add_argument("--version", action="version", version=f"ross_tcgp {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("update", help="download the card list and reference images")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("scan", help="read the collection from the phone")
    p.add_argument("--quick", action="store_true",
                   help="only read new cards (sort the game list by 'Recent cards' first)")
    p.add_argument("--no-top", action="store_true", help="start where the list is, don't scroll up")
    p.add_argument("--serial", help="adb serial, if several devices are connected")
    p.add_argument("--out", help="directory for the JSON files (default: ~/.local/share/ross_tcgp)")
    p.add_argument("--save-pages", metavar="DIR", help="also save every screenshot (for debugging)")
    p.add_argument("--from-pages", metavar="DIR",
                   help="don't use the phone: rebuild a scan from screenshots saved with --save-pages")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("show", help="print the latest (or a given) scan")
    p.add_argument("file", nargs="?")
    p.add_argument("--name", help="only cards whose name contains this text")
    p.add_argument("--json", action="store_true", help="print the raw JSON")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("diff", help="compare two scans (default: OLD against the latest)")
    p.add_argument("old")
    p.add_argument("new", nargs="?")
    p.set_defaults(func=cmd_diff)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
