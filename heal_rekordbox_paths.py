#!/usr/bin/env python3
"""Heal missing rekordbox.xml Location paths by basename lookup on SSD.

Use after merge when old RB crates still point at ~/Documents/Stems... etc.
Dry-run by default. --execute rewrites ~/Music/PioneerDJ/rekordbox.xml.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
import urllib.parse
from pathlib import Path
import xml.etree.ElementTree as ET

DEFAULT_XML = Path.home() / "Music/PioneerDJ/rekordbox.xml"
SEARCH_ROOTS = [
    Path.home() / "Music/stems_audio",
    Path.home() / "Music/Music",
]


def loc_to_path(location: str) -> Path | None:
    if not location:
        return None
    raw = location
    if raw.startswith("file://localhost"):
        raw = raw[len("file://localhost") :]
    elif raw.startswith("file://"):
        raw = raw[len("file://") :]
    return Path(urllib.parse.unquote(raw))


def path_to_rb_location(path: Path) -> str:
    posix = path.resolve().as_posix()
    if not posix.startswith("/"):
        posix = "/" + posix
    return "file://localhost" + urllib.parse.quote(posix, safe="/")


def build_index(roots: list[Path]) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.name.startswith(".") or p.name.startswith("._"):
                continue
            low = p.name.lower()
            # Prefer stems_audio over Music on collision (first root wins if we order stems first)
            if low not in index:
                index[low] = p
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description="Heal missing Rekordbox XML paths. Dry-run default.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--xml", type=Path, default=DEFAULT_XML)
    parser.add_argument("--sample", type=int, default=20)
    args = parser.parse_args()
    dry = not args.execute

    if not args.xml.exists():
        print(f"Error: {args.xml} not found", file=sys.stderr)
        return 1

    print(f"{'DRY-RUN' if dry else 'EXECUTE'}: heal {args.xml}")
    started = time.time()
    print("Indexing local audio basenames...")
    index = build_index(SEARCH_ROOTS)
    print(f"Indexed {len(index):,} unique basenames")

    tree = ET.parse(args.xml)
    root = tree.getroot()
    collection = root.find("COLLECTION")
    if collection is None:
        print("No COLLECTION", file=sys.stderr)
        return 1

    healed = already_ok = still_missing = 0
    samples = 0

    for track in collection.findall("TRACK"):
        loc = track.get("Location") or ""
        path = loc_to_path(loc)
        if path is None:
            still_missing += 1
            continue
        if path.exists():
            already_ok += 1
            continue
        hit = index.get(path.name.lower())
        if hit is None:
            still_missing += 1
            if samples < args.sample:
                print(f"[STILL MISSING] {track.get('Name')} -> {path}")
                samples += 1
            continue
        new_loc = path_to_rb_location(hit)
        healed += 1
        if samples < args.sample:
            print(f"[HEAL] {track.get('Name')}")
            print(f"  from: {path}")
            print(f"  to:   {hit}")
            samples += 1
        if not dry:
            track.set("Location", new_loc)

    print("\n================ HEAL REKORDBOX PATHS ================")
    print(f"Already OK     : {already_ok:,}")
    print(f"Healed         : {healed:,}")
    print(f"Still missing  : {still_missing:,}")
    print(f"Execution time : {time.time() - started:.2f}s")

    if dry:
        print("\nNo write. Re-run with --execute after review.")
        print("Then in Rekordbox: refresh the rekordbox xml browser (reload icon).")
        return 0

    bak = args.xml.with_suffix(".xml.preheal.bak")
    if bak.exists():
        bak.unlink()
    shutil.copy2(args.xml, bak)
    for elem in root.iter():
        for k, v in list(elem.attrib.items()):
            if v is None:
                elem.set(k, "")
    ET.indent(tree, space="  ")
    tree.write(str(args.xml), encoding="UTF-8", xml_declaration=True)
    print(f"\nBacked up to: {bak}")
    print(f"Wrote:       {args.xml}")
    print("In Rekordbox: click the reload/refresh icon on rekordbox xml in the browser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
