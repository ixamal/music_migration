#!/usr/bin/env python3

import json
import os
from pathlib import Path

from music_migration.paths import AUDIO_MEDIA_CATALOG, ensure_config_dir

# Common extensions supported by Traktor, Rekordbox, iTunes/Apple Music
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
}


def scan_audio_files(root_dir="."):
    root_path = Path(root_dir).resolve()

    found_files = []
    by_folder = {}
    skipped_paths = []

    def handle_dir_error(os_error):
        error_msg = f"{os_error.strerror} ({os_error.errno})" if hasattr(os_error, "strerror") else str(os_error)
        skipped_paths.append({
            "path": os_error.filename if hasattr(os_error, "filename") else "Unknown",
            "reason": error_msg,
            "type": "directory_traversal_error"
        })

    for dirpath, _, filenames in os.walk(root_path, onerror=handle_dir_error, followlinks=False):
        for filename in filenames:
            try:
                full_path = Path(dirpath) / filename

                is_stem = filename.lower().endswith(
                    (".stem.mp4", ".stem.m4a", ".stem.mp3")
                )
                ext = full_path.suffix.lower()

                if ext in AUDIO_EXTENSIONS or is_stem:
                    try:
                        rel_path = full_path.relative_to(root_path)
                        parent_folder = str(rel_path.parent)
                    except ValueError:
                        rel_path = full_path
                        parent_folder = str(dirpath)

                    try:
                        file_size = full_path.stat().st_size
                    except (OSError, PermissionError) as err:
                        file_size = -1
                        skipped_paths.append({
                            "path": str(full_path),
                            "reason": f"Failed stat: {err.strerror}",
                            "type": "file_stat_error"
                        })

                    file_info = {
                        "filename": filename,
                        "relative_path": str(rel_path),
                        "absolute_path": str(full_path),
                        "extension": ".stem.mp4" if is_stem else ext,
                        "size_bytes": file_size,
                        "is_stem": is_stem,
                    }

                    found_files.append(file_info)

                    if parent_folder not in by_folder:
                        by_folder[parent_folder] = []
                    by_folder[parent_folder].append(filename)

            except (OSError, PermissionError) as err:
                skipped_paths.append({
                    "path": os.path.join(dirpath, filename),
                    "reason": str(err),
                    "type": "file_access_error"
                })

    output_data = {
        "scanned_directory": str(root_path),
        "total_files_found": len(found_files),
        "total_errors_skipped": len(skipped_paths),
        "summary_by_extension": get_extension_summary(found_files),
        "folder_hierarchy": by_folder,
        "files": found_files,
        "skipped_errors": skipped_paths,
    }

    return output_data


def get_extension_summary(files):
    summary = {}
    for f in files:
        ext = f["extension"]
        summary[ext] = summary.get(ext, 0) + 1
    return summary


if __name__ == "__main__":
    print("Starting audio media scan...")
    data = scan_audio_files(Path.cwd())

    json_output = json.dumps(data, indent=2)

    ensure_config_dir()
    output_path = AUDIO_MEDIA_CATALOG
    output_path.write_text(json_output, encoding="utf-8")

    print(f"\n--- Scan Complete ---")
    print(f"Total audio files found: {data['total_files_found']}")
    print(f"Total skipped paths (errors): {data['total_errors_skipped']}")
    print(f"Saved catalog to: {output_path}")
