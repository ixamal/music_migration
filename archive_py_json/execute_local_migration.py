#!/usr/bin/env python3

import json
import shutil
import sys
from pathlib import Path

# Paths to ignore (app system audio, game SFX, steam sounds, etc.)
EXCLUDE_PATH_PREFIXES = (
    "Library/Application Support",
    "Library/Caches",
    ".Trash",
)


def run_local_migration(candidates_json_path, target_dir):
    candidates_file = Path(candidates_json_path)

    if not candidates_file.exists():
        print(
            f"Error: Candidate file '{candidates_json_path}' not found.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(candidates_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    files_to_migrate = data.get("non_music_files", [])
    total_files = len(files_to_migrate)

    destination_root = Path(target_dir).expanduser().resolve()

    print(f"Loaded {total_files} candidate files from '{candidates_json_path}'.")
    print(f"Destination: {destination_root}\n")

    copied_count = 0
    skipped_count = 0
    error_count = 0

    for idx, item in enumerate(files_to_migrate, start=1):
        source_path = Path(item["absolute_path"])
        rel_path_str = item["relative_path"]

        # Filter out system/app assets
        if any(rel_path_str.startswith(prefix) for prefix in EXCLUDE_PATH_PREFIXES):
            skipped_count += 1
            continue

        if not source_path.exists():
            print(f"[{idx}/{total_files}] SKIP (Not found): {source_path}")
            error_count += 1
            continue

        destination_file = destination_root / rel_path_str

        try:
            # Ensure parent directories exist
            destination_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file preserving metadata (mtime, permissions)
            shutil.copy2(source_path, destination_file)
            copied_count += 1
        except Exception as e:
            print(f"[{idx}/{total_files}] ERROR copying to {destination_file}: {e}")
            error_count += 1

        if idx % 500 == 0 or idx == total_files:
            print(f"Progress: [{idx}/{total_files}] Processed ({copied_count} copied, {skipped_count} app-junk skipped)")

    print("\n================ LOCAL CONSOLIDATION COMPLETE ================")
    print(f"Total Candidate Files   : {total_files}")
    print(f"Audio Files Copied      : {copied_count}")
    print(f"App/Game Audio Skipped  : {skipped_count}")
    print(f"Errors/Missing Files    : {error_count}")
    print(f"All orphaned files are now consolidated in: {destination_root}")


if __name__ == "__main__":
    json_input = "migration_candidates.json"

    # Single local destination inside your home Music directory
    local_destination = "~/Music/MIGRATED_ORPHANS"

    run_local_migration(json_input, local_destination)
