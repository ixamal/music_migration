#!/usr/bin/env python3
"""Relocate missing Rekordbox Collection (master.db) paths by basename/hoist.

The XML library is separate. This patches the encrypted live Collection via
pyrekordbox. Quit Rekordbox first.

Dry-run is the default. Pass --execute to write master.db.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from pyrekordbox import Rekordbox6Database

STEMS = Path.home() / "Music/stems_audio"
MUSIC = Path.home() / "Music/Music"
LIVE_DB = Path.home() / "Library/Pioneer/rekordbox/master.db"
BACKUP_ROOT = Path.home() / "Music/PioneerDJ/rekordbox_library_backup_before_old_db"
HOIST_FROM = "/Media.localized/Music/"
HOIST_TO = "/Media.localized/"
AUDIO_EXT = {
    ".mp3",
    ".wav",
    ".aiff",
    ".aif",
    ".flac",
    ".m4a",
    ".aac",
    ".alac",
    ".ogg",
    ".wma",
    ".mp4",
    ".m4p",
}
STEM = (".stem.mp4", ".stem.m4a", ".stem.mp3")
SKIP_PREFIXES = ("spotify:", "soundcloud:", "apple-music:", "itunes:")


def is_audio(path: Path) -> bool:
    n = path.name.lower()
    if n.startswith(".") or n.startswith("._"):
        return False
    return n.endswith(STEM) or path.suffix.lower() in AUDIO_EXT


def build_index() -> dict[str, Path]:
    index: dict[str, Path] = {}
    for root in (STEMS, MUSIC):
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and is_audio(p) and p.name.lower() not in index:
                index[p.name.lower()] = p
    return index


def skip_url(fp: str) -> bool:
    low = (fp or "").lower()
    return any(s in low for s in SKIP_PREFIXES)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--sample", type=int, default=12)
    args = parser.parse_args()
    dry = not args.execute

    print(f"{'DRY-RUN' if dry else 'EXECUTE'}: Rekordbox Collection relocate")
    print(f"  db: {LIVE_DB}")
    started = time.time()

    print("Indexing local audio...")
    index = build_index()
    print(f"Indexed {len(index):,} basenames")

    db = Rekordbox6Database()
    contents = list(db.get_content())
    print(f"Collection tracks: {len(contents):,}")

    live = missing = hoist_n = base_n = skipped = still = 0
    planned: list[tuple] = []
    shown = 0
    still_samples: list[tuple] = []

    for c in contents:
        fp = c.FolderPath or ""
        path = Path(fp) if fp else None
        if path is not None and path.exists():
            live += 1
            continue
        missing += 1
        if skip_url(fp):
            skipped += 1
            continue
        new = None
        how = None
        if path is not None and HOIST_FROM in str(path):
            cand = Path(str(path).replace(HOIST_FROM, HOIST_TO, 1))
            if cand.is_file():
                new, how = cand, "hoist"
                hoist_n += 1
        if new is None:
            name = path.name.lower() if path is not None else ""
            hit = index.get(name)
            if hit is None and getattr(c, "FileNameL", None):
                hit = index.get(str(c.FileNameL).lower())
            if hit is not None:
                new, how = hit, "basename"
                base_n += 1
        if new is None:
            still += 1
            if len(still_samples) < args.sample:
                still_samples.append((c.Title, fp))
            continue
        planned.append((c, new, how, fp))
        if shown < args.sample:
            print(f"[{'DRY-RUN' if dry else how.upper()}] {c.Title}")
            print(f"  from: {fp}")
            print(f"  to:   {new}")
            shown += 1

    print("\n================ COLLECTION RELOCATE ================")
    print(f"Live on disk              : {live:,}")
    print(f"Missing                   : {missing:,}")
    print(f"  hoist Media.localized   : {hoist_n:,}")
    print(f"  basename match          : {base_n:,}")
    print(f"  skip streaming URLs     : {skipped:,}")
    print(f"  still missing           : {still:,}")
    print(f"Would write / writing     : {len(planned):,}")
    if still_samples:
        print("Still-missing samples:")
        for title, fp in still_samples:
            print(f"  {title} -> {fp[:100]}")

    if dry:
        db.close()
        print("\nNo DB writes. Quit Rekordbox, then --execute.")
        print(f"Time {time.time()-started:.1f}s")
        return 0

    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_dir = BACKUP_ROOT / f"collection_relocate_{stamp}"
    bak_dir.mkdir(parents=True)
    for name in ("master.db", "master.db-wal", "master.db-shm", "master.backup.db"):
        src = LIVE_DB.parent / name
        if src.exists():
            shutil.copy2(src, bak_dir / name)
    print(f"Backed up to {bak_dir}")
    print("Updating FolderPath in master.db (skip missing ANLZ files)...")

    written = errors = 0
    for i, (content, new, how, _fp) in enumerate(planned, 1):
        try:
            new_path = str(new).replace("\\", "/")
            old_path = content.FolderPath
            content.FolderPath = new_path
            if content.OrgFolderPath == old_path:
                content.OrgFolderPath = new_path
            new_name = Path(new_path).name
            if content.FileNameL != new_name:
                content.FileNameL = new_name
            written += 1
            if written % 200 == 0:
                print(f"  …updated {written:,}/{len(planned):,}")
        except Exception as exc:
            errors += 1
            print(f"ERROR {content.Title}: {exc}")
    db.commit()
    db.close()
    print(f"Updated {written:,}  errors={errors}")
    print(f"Time {time.time()-started:.1f}s")
    print("Reopen Rekordbox. Collection should play without per-track Relocate.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
