#!/usr/bin/env python3
import json
import os
import shutil
import sys
from pathlib import Path


def bytes_to_human(size_bytes):
    """Converts raw byte sizes to human-readable strings (MB / GB)."""
    if size_bytes < 0:
        return "Unknown"
    megabytes = size_bytes / (1024 * 1024)
    if megabytes >= 1024:
        gigabytes = megabytes / 1024
        return f"{gigabytes:.2f} GB"
    return f"{megabytes:.2f} MB"


def analyze_migration_candidates(catalog_json_path, target_volume_path="/"):
    catalog_file = Path(catalog_json_path)

    if not catalog_file.exists():
        print(
            f"Error: Could not find catalog file at '{catalog_json_path}'",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(catalog_file, "r", encoding="utf-8") as f:
        catalog_data = json.load(f)

    all_files = catalog_data.get("files", [])

    candidates = []
    total_bytes = 0
    missing_size_count = 0

    # Traverse all files and isolate those NOT in Music/ or subdirectories of Music/
    for file_info in all_files:
        rel_path = file_info.get("relative_path", "")

        # Skip files that already reside in the top-level 'Music/' folder structure
        if rel_path.startswith("Music/") or rel_path == "Music":
            continue

        file_size = file_info.get("size_bytes", -1)

        # Handle size accounting
        if file_size >= 0:
            total_bytes += file_size
        else:
            missing_size_count += 1

        candidate_entry = {
            "filename": file_info.get("filename"),
            "relative_path": rel_path,
            "absolute_path": file_info.get("absolute_path"),
            "extension": file_info.get("extension"),
            "is_stem": file_info.get("is_stem", False),
            "size_bytes": file_size,
            "size_formatted": bytes_to_human(file_size),
        }
        candidates.append(candidate_entry)

    # Check target hard drive disk space availability
    target_path = Path(target_volume_path)
    if not target_path.exists():
        # Fallback to root or user home if custom target path is not mounted yet
        target_path = Path.home()

    try:
        disk_usage = shutil.disk_usage(target_path)
        free_bytes = disk_usage.free
        total_drive_bytes = disk_usage.total
    except OSError:
        free_bytes = -1
        total_drive_bytes = -1

    will_fit = free_bytes >= total_bytes if free_bytes != -1 else None

    # Summary payload
    analysis_report = {
        "source_catalog": str(catalog_file.resolve()),
        "target_check_volume": str(target_path),
        "migration_summary": {
            "total_non_music_files": len(candidates),
            "total_required_bytes": total_bytes,
            "total_required_formatted": bytes_to_human(total_bytes),
            "files_with_unknown_sizes": missing_size_count,
            "target_volume_free_bytes": free_bytes,
            "target_volume_free_formatted": bytes_to_human(free_bytes),
            "will_fit_on_disk": will_fit,
            "remaining_space_after_copy_bytes": free_bytes - total_bytes
            if free_bytes >= 0
            else None,
            "remaining_space_after_copy_formatted": bytes_to_human(
                free_bytes - total_bytes
            )
            if free_bytes >= 0
            else "Unknown",
        },
        "non_music_files": candidates,
    }

    return analysis_report


if __name__ == "__main__":
    config_dir = Path(__file__).resolve().parent.parent / "config"
    catalog_filename = config_dir / "audio_media_catalog.json"
    output_filename = config_dir / "migration_candidates.json"

    # Optional: Set the target drive to check (defaults to current disk or external target)
    target_volume = (
        "/Volumes/Terrarum" if Path("/Volumes/Terrarum").exists() else "/"
    )

    print(f"Parsing '{catalog_filename}' for files outside 'Music/'...")
    report_data = analyze_migration_candidates(
        catalog_filename, target_volume
    )

    # Save structured JSON
    json_output = json.dumps(report_data, indent=2)
    output_filename.parent.mkdir(parents=True, exist_ok=True)
    output_filename.write_text(json_output, encoding="utf-8")

    # Print summary report
    summary = report_data["migration_summary"]
    print("\n--- MIGRATION CANDIDATE ANALYSIS ---")
    print(f"Target Volume Checked : {report_data['target_check_volume']}")
    print(f"Non-Music Files Found : {summary['total_non_music_files']}")
    print(f"Total Required Space  : {summary['total_required_formatted']}")
    print(f"Drive Free Space      : {summary['target_volume_free_formatted']}")
    print("------------------------------------")

    if summary["will_fit_on_disk"]:
        print(" SUCCESS: Space is available! Copying will NOT overfill the disk.")
        print(
            f" Remaining Space After Copy: {summary['remaining_space_after_copy_formatted']}"
        )
    elif summary["will_fit_on_disk"] is False:
        print(" WARNING: Insufficient disk space! Copying will overfill the disk.")
        shortfall = summary["total_required_bytes"] - summary["target_volume_free_bytes"]
        print(f" Storage Shortfall: {bytes_to_human(shortfall)}")
    else:
        print(" UNKNOWN: Could not verify free space on target volume.")

    print(f"\nSaved migration report to: {output_filename}")
