#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from pathlib import Path
import urllib.parse
import time
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Update Traktor collection.nml file paths, relinking to local audio library. Supports --dry-run."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print remappings; do not modify collection.nml on disk.",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=20,
        help="In --dry-run, print at most N example remaps/misses (default: 20).",
    )
    args = parser.parse_args()

    start_time = time.time()

    MASTER_NML = Path("/Volumes/Terrarum/MIGRATION_MASTER/collection.nml")
    TRAKTOR_DIR = Path.home() / "Documents/Native Instruments/Traktor 4.5.1"
    OUTPUT_NML = TRAKTOR_DIR / "collection.nml"
    BACKUP_NML = TRAKTOR_DIR / "collection.nml.bak"
    MEDIA_ROOT = Path.home() / "Music/Music"
    STEMS_ROOT = Path.home() / "Music/stems_audio"

    print("Indexing all local audio files on disk into memory...")

    file_map = {}
    indexed = 0

    # Index stems_audio first (preferred on basename collision)
    for p in STEMS_ROOT.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            file_map[p.name.lower()] = p
            indexed += 1
            if indexed % 5000 == 0:
                print(f"  …indexed {indexed:,} files")

    # Index ~/Music/Music (Media, Media.localized, nested Apple Music trees)
    for p in MEDIA_ROOT.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            name_lower = p.name.lower()
            if name_lower not in file_map:
                file_map[name_lower] = p
            indexed += 1
            if indexed % 5000 == 0:
                print(f"  …indexed {indexed:,} files")

    print(f"Indexed {len(file_map):,} total unique local audio files.")
    print(f"Loading master collection from: {MASTER_NML}...")

    tree = ET.parse(MASTER_NML)
    root = tree.getroot()

    relinked_media = 0
    relinked_stems = 0
    not_found = 0
    dry_samples_shown = 0

    collection = root.find("COLLECTION")
    if collection is None:
        print("Error: COLLECTION node not found in NML!")
        sys.exit(1)

    print("Decoding Traktor URL paths and remapping in memory...")

    for entry in collection.findall("ENTRY"):
        location = entry.find("LOCATION")
        if location is None:
            continue

        raw_file = location.get("FILE", "")
        if not raw_file:
            continue

        # Decode NML URL encoding (e.g. '01%20Track.mp3' -> '01 Track.mp3')
        decoded_file = urllib.parse.unquote(raw_file)

        # Lowercase lookup to handle case mismatch between old/new OS
        found_path = file_map.get(decoded_file.lower())

        if found_path:
            if STEMS_ROOT in found_path.parents:
                relinked_stems += 1
                idx_type = "stems_audio"
            else:
                relinked_media += 1
                idx_type = "music_media"

            # Format DIR attribute for Traktor NML: /:Users/:david/:Music/...
            dir_parts = [p for p in found_path.parent.parts if p != "/"]
            traktor_dir = "/:" + "/:".join(dir_parts) + "/:"

            if args.dry_run:
                if dry_samples_shown < args.sample:
                    print(
                        f"[DRY-RUN] Would relink: '{decoded_file}' -> '{found_path}' "
                        f"(DIR='{traktor_dir}', FILE='{found_path.name}', Type='{idx_type}')"
                    )
                    dry_samples_shown += 1
            else:
                location.set("VOLUME", "Macintosh HD")
                location.set("DIR", traktor_dir)
                location.set("FILE", found_path.name)
        else:
            not_found += 1
            if args.dry_run and dry_samples_shown < args.sample:
                print(f"[DRY-RUN] No local match for: '{decoded_file}'")
                dry_samples_shown += 1

    print("\n================ NML REMAP COMPLETE ================")
    print(f"Relinked to Stems/Audio  : {relinked_stems:,}")
    print(f"Relinked to Music Folder : {relinked_media:,}")
    print(f"Total Relinked Tracks    : {relinked_stems + relinked_media:,}")
    print(f"Unmatched Tracks         : {not_found:,}")

    elapsed = time.time() - start_time

    if not args.dry_run:
        if OUTPUT_NML.exists():
            if BACKUP_NML.exists():
                BACKUP_NML.unlink()
            OUTPUT_NML.rename(BACKUP_NML)
            print(f"\nBacked up existing local NML to: {BACKUP_NML}")

        tree.write(OUTPUT_NML, encoding="UTF-8", xml_declaration=True)
        print(f"Successfully wrote updated NML to: {OUTPUT_NML}")
    else:
        print(f"\n(DRY RUN: No changes written to disk. Sampled {dry_samples_shown} lines; use --sample N for more.)")

    print(f"Execution time: {elapsed:.2f} seconds.")


if __name__ == "__main__":
    main()
