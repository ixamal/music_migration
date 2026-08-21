#!/usr/bin/env python3
"""Hoist ~/Music/Music/Media.localized/Music/{Artist}/{Album}/ up one level.

Apple Music's extra nested Music/ folder left ~18k files at:
  Media.localized/Music/Artist/Album/Track.ext
while ~4.6k already live at:
  Media.localized/Artist/Album/Track.ext

This script only strips that extra Music/ prefix. It does NOT retag or
rename tracks (basenames stay stable for Traktor/Rekordbox remaps).

Dry-run is the default. Pass --execute to move.

After a live run:
  1. python3 -m music_migration.traktor.update_nml_paths
     then python3 -m music_migration.traktor.fix_nml_playlists --execute
  2. python3 -m music_migration.rekordbox.heal_rekordbox_paths --execute
  3. Open Music.app and let it relink / Consolidate if it complains.

Quit Music, Traktor, and Rekordbox before --execute.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

from music_migration.paths import HOIST_MANIFEST, ensure_config_dir

MEDIA_ROOT = Path.home() / "Music/Music/Media.localized"
NESTED = MEDIA_ROOT / "Music"
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
}
STEM_SUFFIXES = (".stem.mp4", ".stem.m4a", ".stem.mp3")


def is_audio(path: Path) -> bool:
    name = path.name.lower()
    if name.startswith(".") or name.startswith("._"):
        return False
    if name.endswith(STEM_SUFFIXES):
        return True
    return path.suffix.lower() in AUDIO_EXT


def file_fingerprint(path: Path) -> tuple[int, str]:
    """(size, md5 of first+last 64KiB) — cheap same-content check."""
    size = path.stat().st_size
    h = hashlib.md5()
    with path.open("rb") as fh:
        head = fh.read(65536)
        h.update(head)
        if size > 65536:
            fh.seek(max(0, size - 65536))
            h.update(fh.read(65536))
    return size, h.hexdigest()


def unique_dest(dest: Path, used: set[str]) -> Path:
    """If dest is taken, suffix before extension(s). Keep original when free."""
    key = str(dest).lower()
    if key not in used and not dest.exists():
        used.add(key)
        return dest

    name = dest.name
    lower = name.lower()
    compound = next((s for s in STEM_SUFFIXES if lower.endswith(s)), None)
    if compound:
        base = name[: -len(compound)]
        ext = name[-len(compound) :]
    else:
        base = dest.stem
        ext = dest.suffix

    n = 2
    while True:
        candidate = dest.with_name(f"{base} ({n}){ext}")
        key = str(candidate).lower()
        if key not in used and not candidate.exists():
            used.add(key)
            return candidate
        n += 1


def plan_moves(nested: Path, media_root: Path) -> list[dict]:
    used: set[str] = set()
    moves: list[dict] = []
    scanned = 0
    for src in nested.rglob("*"):
        if not src.is_file() or src.name.startswith(".") or src.name.startswith("._"):
            continue
        scanned += 1
        if scanned % 2000 == 0:
            print(f"  …scanned {scanned:,} nested files")

        rel = src.relative_to(nested)
        dest = media_root / rel
        action = "move"
        note = ""
        basename_changed = False

        if dest.exists() or str(dest).lower() in used:
            if dest.exists() and dest.is_file() and is_audio(src) and is_audio(dest):
                try:
                    if file_fingerprint(src) == file_fingerprint(dest):
                        action = "skip_duplicate"
                        note = "same size+hash already at destination"
                    else:
                        dest = unique_dest(dest, used)
                        action = "rename_collision"
                        basename_changed = src.name != dest.name
                        note = "different file, same relative path"
                except OSError as exc:
                    dest = unique_dest(dest, used)
                    action = "rename_collision"
                    basename_changed = src.name != dest.name
                    note = f"stat failed ({exc}); renamed to be safe"
            else:
                dest = unique_dest(dest, used)
                action = "rename_collision"
                basename_changed = src.name != dest.name
                note = "destination path occupied"
        else:
            used.add(str(dest).lower())

        moves.append(
            {
                "from": str(src),
                "to": str(dest),
                "relative": str(rel),
                "action": action,
                "note": note,
                "basename_changed": basename_changed,
                "is_audio": is_audio(src),
            }
        )
    return moves


def prune_empty(root: Path) -> int:
    removed = 0
    for dirpath in sorted(
        (p for p in root.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        try:
            if dirpath != root and not any(dirpath.iterdir()):
                dirpath.rmdir()
                removed += 1
        except OSError:
            pass
    # Drop the nested Music/ folder itself if empty.
    try:
        if root.is_dir() and not any(root.iterdir()):
            root.rmdir()
            removed += 1
    except OSError:
        pass
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hoist Media.localized/Music/* up one level. Dry-run by default."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform moves. Without this flag, only plan.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No writes (default). Accepted so --dry-run is a valid flag.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=MEDIA_ROOT,
        help=f"Media.localized root (default: {MEDIA_ROOT})",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=25,
        help="Print at most N planned moves (default: 25).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=HOIST_MANIFEST,
        help="Write move plan JSON here (default: config/hoist_apple_music_manifest.json).",
    )
    args = parser.parse_args()

    media_root = args.root.expanduser().resolve()
    nested = media_root / "Music"
    dry = not args.execute

    if not media_root.is_dir():
        print(f"Error: media root not found: {media_root}", file=sys.stderr)
        return 1
    if nested.is_symlink():
        print(f"Nothing to hoist — {nested} is a compat symlink -> {nested.resolve()}")
        return 0
    if not nested.is_dir():
        print(f"Nothing to hoist — nested folder missing: {nested}")
        return 0

    print(f"{'DRY-RUN' if dry else 'EXECUTE'}: hoist {nested}")
    print(f"  into: {media_root}")
    if not dry:
        print("  Quit Music / Traktor / Rekordbox first if you have not.")
    started = time.time()

    moves = plan_moves(nested, media_root)
    by_action: dict[str, int] = {}
    audio_moves = 0
    artist_merges: set[str] = set()
    for item in moves:
        by_action[item["action"]] = by_action.get(item["action"], 0) + 1
        if item["is_audio"] and item["action"] != "skip_duplicate":
            audio_moves += 1
        rel = Path(item["relative"])
        if rel.parts:
            top_dest = media_root / rel.parts[0]
            nested_src = nested / rel.parts[0]
            if top_dest.exists() and nested_src.exists():
                artist_merges.add(rel.parts[0])

    shown = 0
    moved = errors = skipped = 0
    for item in moves:
        src = Path(item["from"])
        dest = Path(item["to"])
        if shown < args.sample:
            tag = "[DRY-RUN]" if dry else f"[{item['action'].upper()}]"
            extra = f" ({item['note']})" if item["note"] else ""
            try:
                src_rel = src.relative_to(media_root)
                dest_rel = dest.relative_to(media_root)
            except ValueError:
                src_rel, dest_rel = src, dest
            print(f"{tag} {src_rel} -> {dest_rel}{extra}")
            shown += 1

        if dry:
            continue

        if item["action"] == "skip_duplicate":
            try:
                src.unlink()
                skipped += 1
            except OSError as exc:
                print(f"ERROR unlink dup {src}: {exc}")
                errors += 1
            continue

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                print(f"SKIP exists: {dest}")
                errors += 1
                continue
            shutil.move(str(src), str(dest))
            moved += 1
            if moved % 500 == 0:
                print(f"  …moved {moved:,}/{len(moves):,}")
        except OSError as exc:
            print(f"ERROR {src} -> {dest}: {exc}")
            errors += 1

    removed_dirs = 0
    if not dry:
        removed_dirs = prune_empty(nested)

    manifest = {
        "media_root": str(media_root),
        "nested": str(nested),
        "dry_run": dry,
        "planned": len(moves),
        "by_action": by_action,
        "audio_to_move": audio_moves,
        "artist_folders_that_would_merge": sorted(artist_merges),
        "artist_merge_count": len(artist_merges),
        "moved": moved,
        "duplicates_removed": skipped,
        "errors": errors,
        "empty_dirs_removed": removed_dirs,
        "moves": moves,
    }
    ensure_config_dir()
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\n================ HOIST APPLE MUSIC ================")
    print(f"Mode                         : {'DRY-RUN' if dry else 'EXECUTE'}")
    print(f"Nested files planned         : {len(moves):,}")
    print(f"  move                       : {by_action.get('move', 0):,}")
    print(f"  skip_duplicate (same file) : {by_action.get('skip_duplicate', 0):,}")
    print(f"  rename_collision           : {by_action.get('rename_collision', 0):,}")
    print(f"Audio files that change path : {audio_moves:,}")
    print(f"Artist folders that merge    : {len(artist_merges):,}")
    if not dry:
        print(f"Moved                        : {moved:,}")
        print(f"Duplicate nested files unlinked: {skipped:,}")
        print(f"Errors                       : {errors:,}")
        print(f"Empty dirs removed           : {removed_dirs:,}")
    print(f"Manifest                     : {args.manifest.resolve()}")
    print(f"Time                         : {time.time() - started:.1f}s")
    if dry:
        print("\nNo files moved. Review the manifest, then:")
        print("  python3 hoist_apple_music.py --execute")
        print("After execute, remap Traktor + heal Rekordbox paths.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
