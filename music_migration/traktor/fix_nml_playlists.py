#!/usr/bin/env python3
"""Rewrite Traktor playlist PRIMARYKEYs to match remapped COLLECTION locations.

update_nml_paths.py fixed ENTRY LOCATION paths, but playlist keys still embed
the pre-migration absolute path (e.g. ~/Documents/Stems/...). This repairs them.

Dry-run is the default. Pass --execute to write collection.nml.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
import urllib.parse
from pathlib import Path
import xml.etree.ElementTree as ET

TRAKTOR_DIR = Path.home() / "Documents/Native Instruments/Traktor 4.5.1"
DEFAULT_NML = TRAKTOR_DIR / "collection.nml"


def loc_to_key(volume: str, directory: str, file_attr: str) -> str:
    # Traktor playlist KEY format: VOLUME + DIR + FILE (FILE may stay URL-encoded)
    return f"{volume}{directory}{file_attr}"


def loc_to_path(directory: str, file_attr: str) -> Path:
    decoded = urllib.parse.unquote(file_attr or "")
    parts = [p for p in (directory or "").split("/:") if p]
    path = Path("/")
    for part in parts:
        path = path / part
    return path / decoded


def build_basename_index(collection: ET.Element) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for entry in collection.findall("ENTRY"):
        location = entry.find("LOCATION")
        if location is None:
            continue
        file_attr = location.get("FILE", "") or ""
        directory = location.get("DIR", "") or ""
        volume = location.get("VOLUME", "") or "Macintosh HD"
        decoded = urllib.parse.unquote(file_attr)
        if not decoded:
            continue
        path = loc_to_path(directory, file_attr)
        rec = {
            "volume": volume,
            "dir": directory,
            "file": file_attr,
            "decoded": decoded,
            "path": path,
            "exists": path.exists(),
            "key": loc_to_key(volume, directory, file_attr),
        }
        index.setdefault(decoded.lower(), []).append(rec)
    return index


def pick_match(candidates: list[dict]) -> dict | None:
    """Prefer an on-disk COLLECTION location; else first candidate."""
    live = [c for c in candidates if c["exists"]]
    if live:
        # Prefer stems_audio if multiple live hits
        stems = Path.home() / "Music/stems_audio"
        for c in live:
            try:
                c["path"].relative_to(stems)
                return c
            except ValueError:
                continue
        return live[0]
    return candidates[0] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repair Traktor playlist PRIMARYKEYs after path remaps. Dry-run by default."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write repaired NML (backs up to collection.nml.playlists.bak first).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No writes (default). Accepted so --dry-run is a valid flag.",
    )
    parser.add_argument(
        "--nml",
        type=Path,
        default=DEFAULT_NML,
        help=f"NML path (default: {DEFAULT_NML})",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=25,
        help="Print at most N example repairs (default: 25).",
    )
    args = parser.parse_args()
    dry_run = not args.execute
    nml_path = args.nml.expanduser().resolve()

    if not nml_path.exists():
        print(f"Error: NML not found: {nml_path}", file=sys.stderr)
        return 1

    print(f"{'DRY-RUN' if dry_run else 'EXECUTE'}: loading {nml_path} ...")
    started = time.time()
    tree = ET.parse(nml_path)
    root = tree.getroot()
    collection = root.find("COLLECTION")
    playlists = root.find("PLAYLISTS")
    if collection is None or playlists is None:
        print("Error: COLLECTION or PLAYLISTS missing.", file=sys.stderr)
        return 1

    index = build_basename_index(collection)
    print(f"Indexed {sum(len(v) for v in index.values()):,} COLLECTION locations "
          f"({len(index):,} unique basenames).")

    total = 0
    already_ok = 0
    repaired = 0
    unresolved = 0
    samples_shown = 0
    per_playlist: dict[str, dict[str, int]] = {}

    for node in playlists.iter("NODE"):
        if node.get("TYPE") != "PLAYLIST":
            continue
        name = node.get("NAME") or "(unnamed)"
        stats = per_playlist.setdefault(
            name, {"total": 0, "ok": 0, "repaired": 0, "unresolved": 0}
        )
        for pk in node.iter("PRIMARYKEY"):
            # Traktor uses TYPE=TRACK for normal audio and TYPE=STEM for .stem.*
            # TYPE=SET is a recorded history set — leave those alone.
            pk_type = pk.get("TYPE") or "TRACK"
            if pk_type not in ("TRACK", "STEM"):
                continue
            key = pk.get("KEY", "") or ""
            if not key:
                continue
            total += 1
            stats["total"] += 1

            fname = urllib.parse.unquote(key.split("/:")[-1])
            # Does current KEY path exist?
            parts = [p for p in key.split("/:") if p]
            old_path = Path("/") / Path(*parts[1:]) if len(parts) > 1 else None
            if old_path is not None and old_path.exists():
                already_ok += 1
                stats["ok"] += 1
                continue

            match = pick_match(index.get(fname.lower(), []))
            if match is None:
                unresolved += 1
                stats["unresolved"] += 1
                if samples_shown < args.sample:
                    print(f"[UNRESOLVED] {name}: {fname}")
                    samples_shown += 1
                continue

            new_key = match["key"]
            if new_key == key:
                # Key already points at collection location but file missing on disk
                unresolved += 1
                stats["unresolved"] += 1
                if samples_shown < args.sample:
                    print(f"[UNRESOLVED/same-key] {name}: {fname} -> {match['path']}")
                    samples_shown += 1
                continue

            repaired += 1
            stats["repaired"] += 1
            if samples_shown < args.sample:
                print(
                    f"[{'DRY-RUN' if dry_run else 'REPAIR'}] {name}:\n"
                    f"  from: {key}\n"
                    f"  to:   {new_key}"
                )
                samples_shown += 1
            if not dry_run:
                pk.set("KEY", new_key)

    print("\n================ PLAYLIST KEY REPAIR ================")
    print(f"Mode                 : {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print(f"Playlist keys scanned: {total:,}")
    print(f"Already OK (file live): {already_ok:,}")
    print(f"Would repair / repaired: {repaired:,}")
    print(f"Unresolved           : {unresolved:,}")
    print("\nPer playlist:")
    for name, s in sorted(per_playlist.items(), key=lambda kv: (-kv[1]["repaired"], kv[0])):
        if s["repaired"] or s["unresolved"]:
            print(
                f"  {s['repaired']:4d} fix / {s['unresolved']:3d} miss / {s['ok']:4d} ok  {name}"
            )

    if dry_run:
        print("\nNo NML written. Re-run with --execute after reviewing.")
    else:
        backup = nml_path.with_suffix(nml_path.suffix + ".playlists.bak")
        if backup.exists():
            backup.unlink()
        shutil.copy2(nml_path, backup)
        tree.write(nml_path, encoding="UTF-8", xml_declaration=True)
        print(f"\nBacked up to: {backup}")
        print(f"Wrote:       {nml_path}")
        print("Quit/reopen Traktor (or reload collection) to see playlists heal.")

    print(f"Execution time: {time.time() - started:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
