#!/usr/bin/env python3
"""Reorganize ~/Music/stems_audio into {Artist}/{Album}/{Track}.ext using metadata.

Dry-run is the default. Pass --execute to perform moves.
Writes a JSON move manifest for audit / post-reorg NML remap.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

from music_migration.paths import ORGANIZE_STEMS_MANIFEST, ensure_config_dir

try:
    from tinytag import TinyTag
except ImportError:  # pragma: no cover
    TinyTag = None

try:
    from mutagen import File as MutagenFile
except ImportError:  # pragma: no cover
    MutagenFile = None

STEMS_ROOT = Path.home() / "Music/stems_audio"
AUDIO_EXTENSIONS = {
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
INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def is_audio(path: Path) -> bool:
    name = path.name.lower()
    if name.endswith(STEM_SUFFIXES):
        return True
    return path.suffix.lower() in AUDIO_EXTENSIONS


def sanitize(part: str, fallback: str) -> str:
    text = (part or "").strip()
    text = INVALID_FS_CHARS.sub("_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or fallback


def read_tags(path: Path) -> tuple[str, str, str]:
    """Return (artist, album, title) with best-effort tag readers."""
    artist = album = title = ""

    if TinyTag is not None:
        try:
            tag = TinyTag.get(str(path), duration=False, image=False)
            artist = (tag.albumartist or tag.artist or "") or ""
            album = tag.album or ""
            title = tag.title or ""
        except Exception:
            pass

    if MutagenFile is not None and (not artist or not album or not title):
        try:
            audio = MutagenFile(path, easy=True)
            if audio is not None and audio.tags is not None:
                tags = audio.tags
                artist = artist or _first(tags, ("albumartist", "artist"))
                album = album or _first(tags, ("album",))
                title = title or _first(tags, ("title",))
        except Exception:
            pass

    if not title:
        # Keep basename (without compound stem suffix) as human title; filename stays original on disk.
        lower = path.name.lower()
        for suffix in STEM_SUFFIXES:
            if lower.endswith(suffix):
                title = path.name[: -len(suffix)]
                break
        else:
            title = path.stem

    artist = sanitize(artist, "Unknown Artist")
    album = sanitize(album, "Unknown Album")
    title = sanitize(title, path.stem)
    return artist, album, title


def _first(tags, keys: tuple[str, ...]) -> str:
    for key in keys:
        values = tags.get(key)
        if values:
            return str(values[0])
    return ""


def plan_destination(
    src: Path, root: Path, artist: str, album: str, used_targets: set[str]
) -> Path:
    # Preserve original basename so update_nml_paths.py filename lookup still works.
    dest = root / artist / album / src.name
    key = str(dest).lower()
    try:
        same = dest.exists() and dest.resolve() == src.resolve()
    except OSError:
        same = False
    if same or (key not in used_targets and not dest.exists()):
        used_targets.add(key)
        return dest

    # Collision: same basename already claimed — suffix before extension(s)
    stem_name = src.name
    lower = stem_name.lower()
    compound = next((s for s in STEM_SUFFIXES if lower.endswith(s)), None)
    if compound:
        base = stem_name[: -len(compound)]
        ext = stem_name[-len(compound) :]
    else:
        base = src.stem
        ext = src.suffix

    n = 2
    while True:
        candidate = root / artist / album / f"{base} ({n}){ext}"
        key = str(candidate).lower()
        if key not in used_targets and not candidate.exists():
            used_targets.add(key)
            return candidate
        n += 1


def iter_audio(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        if is_audio(path):
            yield path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Organize stems_audio into Artist/Album/Track. Dry-run by default."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform moves on disk. Without this flag, only plan (dry-run).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No writes (default). Accepted so --dry-run is a valid flag.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=STEMS_ROOT,
        help=f"Audio root (default: {STEMS_ROOT})",
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
        default=ORGANIZE_STEMS_MANIFEST,
        help="Write move plan JSON here (default: config/organize_stems_manifest.json).",
    )
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    dry_run = not args.execute

    if TinyTag is None and MutagenFile is None:
        print("Error: need tinytag and/or mutagen installed.", file=sys.stderr)
        return 1
    if not root.is_dir():
        print(f"Error: root not found: {root}", file=sys.stderr)
        return 1

    print(f"{'DRY-RUN' if dry_run else 'EXECUTE'}: scanning {root} ...")
    started = time.time()

    moves = []
    already_ok = 0
    missing_meta = 0
    used_targets: set[str] = set()
    scanned = 0

    for src in iter_audio(root):
        scanned += 1
        if scanned % 500 == 0:
            print(f"  …scanned {scanned:,} audio files")

        artist, album, title = read_tags(src)
        if artist == "Unknown Artist" or album == "Unknown Album":
            missing_meta += 1

        dest = plan_destination(src, root, artist, album, used_targets)

        if src.resolve() == dest.resolve():
            already_ok += 1
            continue

        moves.append(
            {
                "from": str(src),
                "to": str(dest),
                "artist": artist,
                "album": album,
                "title": title,
                "basename_changed": src.name != dest.name,
            }
        )

    moved = 0
    errors = 0
    samples_shown = 0

    for item in moves:
        src = Path(item["from"])
        dest = Path(item["to"])
        if samples_shown < args.sample:
            prefix = "[DRY-RUN] Would move" if dry_run else "[MOVE]"
            note = " (basename collision rename)" if item["basename_changed"] else ""
            print(f"{prefix}: {src.relative_to(root)} -> {dest.relative_to(root)}{note}")
            samples_shown += 1

        if dry_run:
            continue

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                print(f"SKIP exists: {dest}")
                errors += 1
                continue
            shutil.move(str(src), str(dest))
            moved += 1
            if moved % 200 == 0:
                print(f"  …moved {moved:,}/{len(moves):,}")
        except OSError as exc:
            print(f"ERROR {src} -> {dest}: {exc}")
            errors += 1

    # Optionally prune empty dirs after execute
    removed_dirs = 0
    if not dry_run:
        for dirpath in sorted(
            (p for p in root.rglob("*") if p.is_dir()),
            key=lambda p: len(p.parts),
            reverse=True,
        ):
            try:
                if dirpath != root and not any(dirpath.iterdir()):
                    dirpath.rmdir()
                    removed_dirs += 1
            except OSError:
                pass

    manifest = {
        "root": str(root),
        "dry_run": dry_run,
        "scanned_audio": scanned,
        "planned_moves": len(moves),
        "already_organized": already_ok,
        "missing_artist_or_album_tags": missing_meta,
        "moved": moved,
        "errors": errors,
        "empty_dirs_removed": removed_dirs,
        "moves": moves,
    }
    ensure_config_dir()
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\n================ ORGANIZE STEMS ================")
    print(f"Mode                      : {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print(f"Audio files scanned       : {scanned:,}")
    print(f"Already in target layout  : {already_ok:,}")
    print(f"Planned moves             : {len(moves):,}")
    print(f"Missing artist/album tags : {missing_meta:,}")
    if not dry_run:
        print(f"Moved                     : {moved:,}")
        print(f"Errors                    : {errors:,}")
        print(f"Empty dirs removed        : {removed_dirs:,}")
    print(f"Manifest                  : {args.manifest.resolve()}")
    print(f"Execution time            : {time.time() - started:.2f}s")
    if dry_run:
        print("\nNo files moved. Re-run with --execute after reviewing the manifest.")
        print("After a live run, re-run: python3 update_nml_paths.py --dry-run")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
