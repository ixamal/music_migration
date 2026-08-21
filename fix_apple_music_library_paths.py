#!/usr/bin/env python3
"""Make Apple Music's old Media.localized/Music/ paths resolve after hoist.

Library.musicdb is encrypted (hfma) — we cannot rewrite locations in-place.
Music.app also recreates Media.localized/Music/ when it 'organizes' or Locates.

Fix:
  1. Quit Music.app first.
  2. Move any real files out of Media.localized/Music/{Artist}/... up one level.
  3. Replace Media.localized/Music with a symlink to '.' so
     .../Media.localized/Music/Artist/Album/Track
     resolves to
     .../Media.localized/Artist/Album/Track

Dry-run is the default. Pass --execute to apply.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

MEDIA = Path.home() / "Music/Music/Media.localized"
NESTED = MEDIA / "Music"
LIB = Path.home() / "Music/Music/Music Library.musiclibrary"
BACKUP_ROOT = Path.home() / "Music/PioneerDJ/apple_music_library_backups"


def music_running() -> bool:
    import subprocess

    r = subprocess.run(
        ["pgrep", "-f", "/Applications/Music.app"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0 and bool(r.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    dry = not args.execute

    print(f"{'DRY-RUN' if dry else 'EXECUTE'}: Apple Music path compat")
    print(f"  media:  {MEDIA}")
    print(f"  nested: {NESTED}")
    started = time.time()

    if not MEDIA.is_dir():
        print(f"Error: {MEDIA} missing", file=sys.stderr)
        return 1
    if music_running():
        print("Error: Music.app is running. Quit it (Cmd+Q) and retry.", file=sys.stderr)
        return 1

    if NESTED.is_symlink():
        print(f"Already a symlink: {NESTED} -> {NESTED.resolve()}")
        target = NESTED.resolve()
        if target == MEDIA.resolve():
            print("Compat symlink already in place. Nothing to do.")
            return 0
        print("Symlink points elsewhere — not changing it automatically.")
        return 1

    moves: list[tuple[Path, Path]] = []
    if NESTED.is_dir():
        for src in NESTED.rglob("*"):
            if not src.is_file() or src.name.startswith(".") or src.name.startswith("._"):
                continue
            dest = MEDIA / src.relative_to(NESTED)
            moves.append((src, dest))

    print(f"Files to hoist out of nested Music/: {len(moves)}")
    for src, dest in moves[:15]:
        exists = "EXISTS" if dest.exists() else "free"
        print(f"  {src.relative_to(MEDIA)} -> {dest.relative_to(MEDIA)} [{exists}]")
    if len(moves) > 15:
        print(f"  … {len(moves) - 15} more")

    if dry:
        print("\nWould then: remove nested Music/ directory, ln -s . Music")
        print("No changes written. Re-run with --execute.")
        return 0

    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = BACKUP_ROOT / stamp
    bak.mkdir(parents=True, exist_ok=True)
    for name in ("Library.musicdb", "Application.musicdb", "Library Preferences.musicdb"):
        src = LIB / name
        if src.exists():
            shutil.copy2(src, bak / name)
    print(f"Backed up musicdb files to {bak}")

    errors = 0
    for src, dest in moves:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                # Keep both if different; skip identical
                if dest.stat().st_ino == src.stat().st_ino:
                    continue
                dest = dest.with_name(dest.stem + " (located)" + dest.suffix)
            shutil.move(str(src), str(dest))
            print(f"MOVED {src.relative_to(MEDIA)} -> {dest.relative_to(MEDIA)}")
        except OSError as exc:
            print(f"ERROR {src}: {exc}")
            errors += 1

    # Wipe leftover .DS_Store / empty dirs, then replace with symlink
    if NESTED.is_dir() and not NESTED.is_symlink():
        for p in sorted(NESTED.rglob("*"), key=lambda x: len(x.parts), reverse=True):
            try:
                if p.is_file() and (p.name.startswith(".") or p.name.startswith("._")):
                    p.unlink()
                elif p.is_dir() and not any(p.iterdir()):
                    p.rmdir()
            except OSError:
                leftover = list(p.rglob("*")) if p.is_dir() else [p]
                if leftover:
                    print(f"WARN leftover {p}: {leftover[:5]}")
        try:
            if NESTED.exists() and not any(NESTED.iterdir()):
                NESTED.rmdir()
        except OSError as exc:
            print(f"ERROR removing nested dir: {exc}")
            errors += 1

    if NESTED.exists():
        print(f"Error: could not clear {NESTED} to make symlink", file=sys.stderr)
        return 1

    NESTED.symlink_to(".", target_is_directory=True)
    print(f"Symlink: {NESTED} -> .")

    probe = MEDIA / "Music/Pivots/These Beets/Less Than Burning Hawt.m4a"
    print(f"Probe old path exists: {probe.exists()}  ({probe})")
    print(f"Time: {time.time() - started:.1f}s  errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
