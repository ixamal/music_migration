#!/usr/bin/env python3
"""Clean migration staging mirrors after stems_audio organize.

Default is dry-run. With --execute:
  1) Copy staging-only audio (not already in stems_audio by basename) into
     ~/Music/stems_audio/_rescued_from_staging/
  2) Remove staging trees: Desktop/, Documents/, Downloads/, Library/
     under ~/Music/MIGRATED_ORPHANS (keeps scripts/docs/git)
  3) Remove leftover ~/Music/stems_audio/Library Google Drive shortcut junk
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

STAGING = Path.home() / "Music/MIGRATED_ORPHANS"
STEMS = Path.home() / "Music/stems_audio"
RESCUE = STEMS / "_rescued_from_staging"
STAGING_TREES = ("Desktop", "Documents", "Downloads", "Library")
AUDIO_EXT = {".mp3", ".wav", ".aiff", ".aif", ".flac", ".m4a", ".aac", ".mp4", ".alac", ".ogg", ".wma"}


def is_audio(path: Path) -> bool:
    name = path.name.lower()
    if name.startswith(".") or name.startswith("._"):
        return False
    if ".stem." in name:
        return True
    return path.suffix.lower() in AUDIO_EXT


def iter_staging_audio():
    for top in STAGING_TREES:
        root = STAGING / top
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and is_audio(p):
                yield p


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean staging mirrors. Dry-run by default.")
    parser.add_argument("--execute", action="store_true", help="Perform rescue copies and deletions.")
    args = parser.parse_args()
    dry = not args.execute
    started = time.time()

    print(f"{'DRY-RUN' if dry else 'EXECUTE'}: staging cleanup")
    print(f"  staging: {STAGING}")
    print(f"  stems:   {STEMS}")

    stems_names = {p.name.lower() for p in STEMS.rglob("*") if p.is_file()}
    staging_audio = list(iter_staging_audio())
    only_staging = [p for p in staging_audio if p.name.lower() not in stems_names]
    dupes = len(staging_audio) - len(only_staging)

    print(f"\nStaging audio files     : {len(staging_audio):,}")
    print(f"Already in stems_audio  : {dupes:,}")
    print(f"Staging-only (rescue)   : {len(only_staging):,}")
    for p in only_staging[:20]:
        print(f"  RESCUE: {p.relative_to(STAGING)}")

    # stems_audio/Library leftover
    lib = STEMS / "Library"
    lib_files = [p for p in lib.rglob("*") if p.is_file()] if lib.exists() else []
    print(f"\nstems_audio/Library junk files: {len(lib_files)}")
    for p in lib_files[:10]:
        print(f"  REMOVE: {p}")

    print("\nStaging trees to remove:")
    for top in STAGING_TREES:
        path = STAGING / top
        if path.exists():
            # size estimate via du would be slow; just flag presence
            print(f"  REMOVE TREE: {path}")
        else:
            print(f"  (missing) {path}")

    if dry:
        print("\nNo changes made. Re-run with --execute to rescue uniques and delete staging trees.")
        print(f"Execution time: {time.time() - started:.2f}s")
        return 0

    # Rescue uniques
    RESCUE.mkdir(parents=True, exist_ok=True)
    rescued = 0
    for src in only_staging:
        dest = RESCUE / src.name
        if dest.exists():
            stem, suf = dest.stem, dest.suffix
            n = 2
            while True:
                cand = RESCUE / f"{stem} ({n}){suf}"
                if not cand.exists():
                    dest = cand
                    break
                n += 1
        shutil.copy2(src, dest)
        rescued += 1
        print(f"COPIED -> {dest}")

    def _rmtree(path: Path) -> bool:
        errors: list[str] = []

        def onerror(func, p, exc_info):
            errors.append(f"{p}: {exc_info[1]}")

        shutil.rmtree(path, onerror=onerror)
        for err in errors[:10]:
            print(f"  WARN: {err}")
        if path.exists():
            print(f"  PARTIAL: {path} still present ({len(errors)} errors)")
            return False
        print(f"REMOVED: {path}")
        return True

    # Remove stems_audio/Library junk (Google Drive shortcuts may be locked)
    removed_lib = 0
    if lib.exists():
        print(f"REMOVING {lib} ...")
        if _rmtree(lib):
            removed_lib = 1

    # Remove staging trees
    removed_trees = 0
    for top in STAGING_TREES:
        path = STAGING / top
        if path.exists():
            print(f"REMOVING {path} ...")
            if _rmtree(path):
                removed_trees += 1

    print("\n================ STAGING CLEANUP ================")
    print(f"Rescued into stems_audio : {rescued}")
    print(f"Library junk trees gone  : {removed_lib}")
    print(f"Staging trees removed    : {removed_trees}")
    print(f"Execution time           : {time.time() - started:.2f}s")
    print("\nNext: Quit Traktor, then run:")
    print("  python3 update_nml_paths.py")
    print("  python3 fix_nml_playlists.py --execute")
    return 0


if __name__ == "__main__":
    sys.exit(main())
