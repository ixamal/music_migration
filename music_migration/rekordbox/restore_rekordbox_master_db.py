#!/usr/bin/env python3
"""Swap in an old-Mac Rekordbox master.db (pad banks / collection DB), then re-point XML.

Prereqs:
  1. Quit Rekordbox completely.
  2. Copy OLD files into:
       /Volumes/Terrarum/MIGRATION_MASTER/rekordbox_db_old/
     at least: master.db  (optional: master.backup.db, ExtData.edb, datafile.edb)

Dry-run by default. --execute performs the swap.
After swap: open Rekordbox, confirm sampler pads, then Preferences →
Advanced → Database → rekordbox xml → Imported Library =
  ~/Music/PioneerDJ/rekordbox.xml
and refresh / re-import From Traktor playlists as needed.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

OLD_DIR = Path("/Volumes/Terrarum/MIGRATION_MASTER/rekordbox_db_old")
LIVE_DIR = Path.home() / "Library/Pioneer/rekordbox"
BACKUP_DIR = Path.home() / "Music/PioneerDJ/rekordbox_library_backup_before_old_db"
XML = Path.home() / "Music/PioneerDJ/rekordbox.xml"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No writes (default). Accepted so --dry-run is a valid flag.",
    )
    parser.add_argument("--old-dir", type=Path, default=OLD_DIR)
    args = parser.parse_args()
    dry = not args.execute

    old_db = args.old_dir / "master.db"
    print(f"{'DRY-RUN' if dry else 'EXECUTE'}: restore old master.db")
    print(f"  old dir : {args.old_dir}")
    print(f"  live dir: {LIVE_DIR}")
    print(f"  XML     : {XML} ({'OK' if XML.exists() else 'MISSING'})")

    if not old_db.exists():
        print(
            f"\nERROR: {old_db} not found.\n"
            "On the OLD Mac, copy these into that folder (USB/Terrarum):\n"
            "  ~/Library/Pioneer/rekordbox/master.db\n"
            "  ~/Library/Pioneer/rekordbox/master.backup.db  (optional)\n"
            "NOTE: ~/Music/rekordbox is only SAMPLE AUDIO — not the pad database.",
            file=sys.stderr,
        )
        return 1

    print(f"\nFound old master.db ({old_db.stat().st_size / 1e6:.1f} MB)")
    candidates = [
        "master.db",
        "master.backup.db",
        "master.backup2.db",
        "ExtData.edb",
        "datafile.edb",
    ]
    to_copy = [n for n in candidates if (args.old_dir / n).exists()]
    print("Will restore:", ", ".join(to_copy))

    if dry:
        print("\nNo changes. Quit Rekordbox, then re-run with --execute.")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dest_bak = BACKUP_DIR / f"live_{stamp}"
    dest_bak.mkdir(parents=True)
    for p in LIVE_DIR.glob("*"):
        if p.name.startswith("master.db"):
            continue  # copy explicitly below
        if p.is_file():
            shutil.copy2(p, dest_bak / p.name)
    for name in ("master.db", "master.backup.db", "master.backup2.db", "master.backup3.db"):
        src = LIVE_DIR / name
        if src.exists():
            shutil.copy2(src, dest_bak / name)
    # remove wal/shm so old db isn't paired with new wal
    for extra in ("master.db-wal", "master.db-shm"):
        p = LIVE_DIR / extra
        if p.exists():
            shutil.copy2(p, dest_bak / extra)
            p.unlink()

    for name in to_copy:
        shutil.copy2(args.old_dir / name, LIVE_DIR / name)
        print(f"Installed {name}")

    print(f"\nBacked up previous live library files to: {dest_bak}")
    print("Open Rekordbox → check sampler banks.")
    print(f"Then set Imported Library XML to: {XML}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
