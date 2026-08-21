#!/usr/bin/env python3
"""Merge Traktor collection.nml into an existing rekordbox.xml without dropping RB data.

Preserves:
  - All existing Rekordbox TRACK entries (incl. Sampler / PioneerDJ clips)
  - Existing Rekordbox playlists / cue & grid children on unmatched RB tracks

Folds in from Traktor (current session paths):
  - Updated Location for matched tracks (stems_audio + Apple Music remaps)
  - BPM / beatgrid (TEMPO) + cues (POSITION_MARK) from NML when present
  - New TRACK rows for Traktor files not already in the XML
  - Traktor playlists under a "From Traktor" folder (RB playlists untouched)

Dry-run is the default. Pass --execute to write ~/Music/PioneerDJ/rekordbox.xml.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
import urllib.parse
from pathlib import Path
import xml.etree.ElementTree as ET

MASTER_RB = Path("/Volumes/Terrarum/MIGRATION_MASTER/rekordbox.xml")
LOCAL_NML = Path.home() / "Documents/Native Instruments/Traktor 4.5.1/collection.nml"
OUTPUT_RB = Path.home() / "Music/PioneerDJ/rekordbox.xml"

# Traktor CUE_V2 TYPE → rough Rekordbox POSITION_MARK Type
# 0 cue, 1 fade-in, 2 fade-out, 3 load, 4 grid, 5 loop
TRAKTOR_CUE_TO_RB = {
    "0": "0",
    "1": "1",
    "2": "2",
    "3": "3",
    "5": "4",  # loop
}


def nml_location_to_path(loc: ET.Element) -> Path | None:
    directory = loc.get("DIR") or ""
    file_attr = loc.get("FILE") or ""
    if not file_attr:
        return None
    decoded = urllib.parse.unquote(file_attr)
    parts = [p for p in directory.split("/:") if p]
    path = Path("/")
    for part in parts:
        path = path / part
    return path / decoded


def path_to_rb_location(path: Path) -> str:
    # rekordbox: file://localhost/Users/... with percent-encoding
    posix = path.resolve().as_posix()
    if not posix.startswith("/"):
        posix = "/" + posix
    encoded = urllib.parse.quote(posix, safe="/")
    return f"file://localhost{encoded}"


def rb_location_to_path(location: str) -> Path | None:
    if not location:
        return None
    # file://localhost/Users/... or file:///Users/...
    raw = location
    if raw.startswith("file://localhost"):
        raw = raw[len("file://localhost") :]
    elif raw.startswith("file://"):
        raw = raw[len("file://") :]
    raw = urllib.parse.unquote(raw)
    return Path(raw)


def kind_for_path(path: Path) -> str:
    ext = path.suffix.lower()
    mapping = {
        ".mp3": "MP3 File",
        ".m4a": "M4A File",
        ".m4p": "M4A File",
        ".aiff": "AIFF File",
        ".aif": "AIFF File",
        ".wav": "WAV File",
        ".flac": "FLAC File",
        ".mp4": "MP4 File",
        ".aac": "AAC File",
    }
    name = path.name.lower()
    if ".stem." in name:
        return "M4A File" if name.endswith(".m4a") else "MP4 File"
    return mapping.get(ext, "MP3 File")


def open_key_to_tonality(info_key: str | None) -> str:
    """Best-effort: pass Traktor open-key / classical through as Tonality string."""
    return (info_key or "").strip()


def clear_analysis_children(track: ET.Element) -> None:
    for child in list(track):
        if child.tag in ("TEMPO", "POSITION_MARK"):
            track.remove(child)


def apply_traktor_analysis(track: ET.Element, entry: ET.Element) -> tuple[int, int]:
    """Write TEMPO + POSITION_MARK from Traktor ENTRY. Returns (tempo_n, cue_n)."""
    clear_analysis_children(track)
    tempo_n = 0
    cue_n = 0

    tempo = entry.find("TEMPO")
    bpm = None
    if tempo is not None and tempo.get("BPM"):
        try:
            bpm = float(tempo.get("BPM"))
        except ValueError:
            bpm = None
        if bpm:
            track.set("AverageBpm", f"{bpm:.2f}")

    # Grid cue → TEMPO Inizio
    grid_start_sec = None
    for cue in entry.findall("CUE_V2"):
        if cue.get("TYPE") == "4":  # grid
            try:
                grid_start_sec = float(cue.get("START") or "0") / 1000.0
            except ValueError:
                grid_start_sec = 0.0
            break

    if bpm:
        inizio = grid_start_sec if grid_start_sec is not None else 0.0
        ET.SubElement(
            track,
            "TEMPO",
            {
                "Inizio": f"{inizio:.3f}",
                "Bpm": f"{bpm:.2f}",
                "Metro": "4/4",
                "Battito": "1",
            },
        )
        tempo_n = 1

    for cue in entry.findall("CUE_V2"):
        ctype = cue.get("TYPE") or "0"
        if ctype == "4":
            continue  # grid already used as TEMPO
        rb_type = TRAKTOR_CUE_TO_RB.get(ctype)
        if rb_type is None:
            continue
        try:
            start_ms = float(cue.get("START") or "0")
            length_ms = float(cue.get("LEN") or "0")
        except ValueError:
            continue
        start_sec = start_ms / 1000.0
        hot = cue.get("HOTCUE", "-1")
        try:
            num = int(hot)
        except ValueError:
            num = -1
        # Memory cue if not a hotcue slot
        if num < 0:
            num = -1
        attrib = {
            "Name": cue.get("NAME") or "",
            "Type": rb_type,
            "Start": f"{start_sec:.3f}",
            "Num": str(num),
        }
        if rb_type == "4" and length_ms > 0:
            attrib["End"] = f"{(start_ms + length_ms) / 1000.0:.3f}"
        ET.SubElement(track, "POSITION_MARK", attrib)
        cue_n += 1

    info = entry.find("INFO")
    if info is not None:
        tonality = open_key_to_tonality(info.get("KEY"))
        if tonality:
            track.set("Tonality", tonality)
        playcount = info.get("PLAYCOUNT")
        if playcount:
            track.set("PlayCount", str(playcount))
        genre = info.get("GENRE")
        if genre and not track.get("Genre"):
            track.set("Genre", genre)

    # ElementTree cannot serialize attribute values of None
    for key, val in list(track.attrib.items()):
        if val is None:
            track.set(key, "")

    return tempo_n, cue_n


def build_track_from_entry(entry: ET.Element, path: Path, track_id: int) -> ET.Element:
    info = entry.find("INFO")
    album = entry.find("ALBUM")
    size = "0"
    total_time = "0"
    bitrate = "0"
    date_added = "2026-08-08"
    genre = ""
    if info is not None:
        if info.get("FILESIZE"):
            try:
                # Traktor FILESIZE is often KB
                size = str(int(float(info.get("FILESIZE"))) * 1024)
            except ValueError:
                size = "0"
        if info.get("PLAYTIME"):
            total_time = str(int(float(info.get("PLAYTIME"))))
        if info.get("BITRATE"):
            try:
                bitrate = str(int(float(info.get("BITRATE")) // 1000))
            except ValueError:
                bitrate = "0"
        if info.get("IMPORT_DATE"):
            # 2019/12/7 → 2019-12-07 best effort
            raw = info.get("IMPORT_DATE") or ""
            parts = raw.split("/")
            if len(parts) == 3:
                y, m, d = parts
                date_added = f"{y}-{int(m):02d}-{int(d):02d}"
        genre = info.get("GENRE") or ""

    track_number = "0"
    if album is not None and album.get("TRACK"):
        track_number = str(album.get("TRACK"))
    album_title = ""
    if album is not None and album.get("TITLE"):
        album_title = album.get("TITLE") or ""

    track = ET.Element(
        "TRACK",
        {
            "TrackID": str(track_id),
            "Name": entry.get("TITLE") or path.stem,
            "Artist": entry.get("ARTIST") or "",
            "Composer": "",
            "Album": album_title,
            "Grouping": "",
            "Genre": genre or "",
            "Kind": kind_for_path(path),
            "Size": size,
            "TotalTime": total_time,
            "DiscNumber": "0",
            "TrackNumber": track_number,
            "Year": "0",
            "AverageBpm": "0.00",
            "DateAdded": date_added,
            "BitRate": bitrate,
            "SampleRate": "44100",
            "Comments": "",
            "PlayCount": (info.get("PLAYCOUNT") if info is not None and info.get("PLAYCOUNT") else "0"),
            "Rating": "0",
            "Location": path_to_rb_location(path),
            "Remixer": "",
            "Tonality": open_key_to_tonality(info.get("KEY") if info is not None else None) or "",
            "Label": "",
            "Mix": "",
        },
    )
    apply_traktor_analysis(track, entry)
    return track


def index_rb_by_basename(collection: ET.Element) -> dict[str, list[ET.Element]]:
    index: dict[str, list[ET.Element]] = {}
    for track in collection.findall("TRACK"):
        loc = track.get("Location") or ""
        if not loc:
            continue
        path = rb_location_to_path(loc)
        if path is None:
            continue
        index.setdefault(path.name.lower(), []).append(track)
    return index


def next_track_id(collection: ET.Element) -> int:
    max_id = 0
    for track in collection.findall("TRACK"):
        try:
            max_id = max(max_id, int(track.get("TrackID") or "0"))
        except ValueError:
            continue
    return max_id + 1


def ensure_from_traktor_folder(playlists_root: ET.Element) -> ET.Element:
    """Return the NODE folder 'From Traktor', creating under ROOT if needed."""
    root_node = playlists_root.find("NODE")
    if root_node is None:
        root_node = ET.SubElement(
            playlists_root, "NODE", {"Type": "0", "Name": "ROOT", "Count": "0"}
        )
    for node in root_node.findall("NODE"):
        if node.get("Name") == "From Traktor" and node.get("Type") == "0":
            return node
    folder = ET.SubElement(
        root_node,
        "NODE",
        {"Type": "0", "Name": "From Traktor", "Count": "0"},
    )
    # bump ROOT count
    try:
        root_node.set("Count", str(int(root_node.get("Count") or "0") + 1))
    except ValueError:
        root_node.set("Count", str(len(root_node.findall("NODE"))))
    return folder


def add_traktor_playlists(
    playlists_root: ET.Element,
    nml_root: ET.Element,
    key_by_basename: dict[str, str],
) -> tuple[int, int]:
    """Add Traktor playlists under From Traktor. Returns (playlists, entries_linked)."""
    folder = ensure_from_traktor_folder(playlists_root)
    # Remove previous From Traktor children if re-running
    for child in list(folder):
        folder.remove(child)

    added_pl = 0
    linked = 0
    nml_playlists = nml_root.find("PLAYLISTS")
    if nml_playlists is None:
        return 0, 0

    for node in nml_playlists.iter("NODE"):
        if node.get("TYPE") != "PLAYLIST":
            continue
        name = node.get("NAME") or "Untitled"
        keys: list[str] = []
        for pk in node.iter("PRIMARYKEY"):
            if pk.get("TYPE") not in ("TRACK", "STEM"):
                continue
            fname = urllib.parse.unquote((pk.get("KEY") or "").split("/:")[-1])
            tid = key_by_basename.get(fname.lower())
            if tid:
                keys.append(tid)
                linked += 1
        pl = ET.SubElement(
            folder,
            "NODE",
            {
                "Name": name,
                "Type": "1",
                "KeyType": "0",
                "Entries": str(len(keys)),
            },
        )
        for tid in keys:
            ET.SubElement(pl, "TRACK", {"Key": tid})
        added_pl += 1

    folder.set("Count", str(added_pl))
    return added_pl, linked


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge Traktor NML into existing rekordbox.xml (preserve Sampler + RB crates)."
    )
    parser.add_argument("--execute", action="store_true", help="Write merged XML to disk.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No writes (default). Accepted so --dry-run is a valid flag.",
    )
    parser.add_argument("--master", type=Path, default=MASTER_RB, help="Base rekordbox.xml")
    parser.add_argument("--nml", type=Path, default=LOCAL_NML, help="Traktor collection.nml")
    parser.add_argument("--output", type=Path, default=OUTPUT_RB, help="Output rekordbox.xml")
    parser.add_argument("--sample", type=int, default=15, help="Sample log lines")
    parser.add_argument(
        "--missing-ok",
        action="store_true",
        help="Include Traktor entries even if file missing on disk (default: skip missing).",
    )
    args = parser.parse_args()
    dry = not args.execute

    if not args.master.exists():
        print(f"Error: master Rekordbox XML not found: {args.master}", file=sys.stderr)
        return 1
    if not args.nml.exists():
        print(f"Error: NML not found: {args.nml}", file=sys.stderr)
        return 1

    print(f"{'DRY-RUN' if dry else 'EXECUTE'}: merge Traktor → Rekordbox")
    print(f"  base NML : {args.nml}")
    print(f"  base XML : {args.master}")
    print(f"  output   : {args.output}")
    started = time.time()

    rb_tree = ET.parse(args.master)
    rb_root = rb_tree.getroot()
    collection = rb_root.find("COLLECTION")
    playlists = rb_root.find("PLAYLISTS")
    if collection is None:
        print("Error: COLLECTION missing in rekordbox.xml", file=sys.stderr)
        return 1
    if playlists is None:
        playlists = ET.SubElement(rb_root, "PLAYLISTS")

    product = rb_root.find("PRODUCT")
    if product is not None:
        product.set("Name", "rekordbox")
        product.set("Version", "7.2.17")
        product.set("Company", "AlphaTheta")

    rb_index = index_rb_by_basename(collection)
    preserved = len(collection.findall("TRACK"))
    samplerish = sum(
        1
        for t in collection.findall("TRACK")
        if "/Sampler/" in (t.get("Location") or "") or "OSC_SAMPLER" in (t.get("Location") or "")
    )

    nml_root = ET.parse(args.nml).getroot()
    nml_coll = nml_root.find("COLLECTION")
    if nml_coll is None:
        print("Error: COLLECTION missing in NML", file=sys.stderr)
        return 1

    updated = 0
    added = 0
    skipped_missing = 0
    skipped_dupe_basename = 0
    analysis_tempo = 0
    analysis_cues = 0
    updated_stems = 0
    updated_music = 0
    added_stems = 0
    added_music = 0
    samples = 0
    # basename -> TrackID for playlist linking (prefer live path's track)
    key_by_basename: dict[str, str] = {}
    for tracks in rb_index.values():
        for t in tracks:
            path = rb_location_to_path(t.get("Location") or "")
            if path:
                key_by_basename[path.name.lower()] = t.get("TrackID") or ""

    next_id = next_track_id(collection)
    seen_new: set[str] = set()

    for entry in nml_coll.findall("ENTRY"):
        loc = entry.find("LOCATION")
        if loc is None:
            continue
        path = nml_location_to_path(loc)
        if path is None:
            continue
        base = path.name.lower()
        exists = path.exists()
        if not exists and not args.missing_ok:
            skipped_missing += 1
            continue

        matches = rb_index.get(base) or []
        if matches:
            track = matches[0]
            old_loc = track.get("Location") or ""
            new_loc = path_to_rb_location(path)
            track.set("Location", new_loc)
            # refresh name/artist if empty
            if not track.get("Name") and entry.get("TITLE"):
                track.set("Name", entry.get("TITLE") or "")
            if not track.get("Artist") and entry.get("ARTIST"):
                track.set("Artist", entry.get("ARTIST") or "")
            t_n, c_n = apply_traktor_analysis(track, entry)
            analysis_tempo += t_n
            analysis_cues += c_n
            updated += 1
            key_by_basename[base] = track.get("TrackID") or ""
            if "stems_audio" in str(path):
                updated_stems += 1
            elif "Music/Music" in str(path) or "Media.localized" in str(path):
                updated_music += 1
            if samples < args.sample and old_loc != new_loc:
                print(f"[UPDATE] {path.name}")
                print(f"    from: {old_loc[:90]}")
                print(f"    to:   {new_loc[:90]}")
                samples += 1
        else:
            if base in seen_new:
                skipped_dupe_basename += 1
                continue
            track = build_track_from_entry(entry, path, next_id)
            # Only mutate tree when executing — but for dry-run we still need counts;
            # build stats the same and append only on execute. For playlist key map we
            # assign provisional IDs in dry-run too.
            tid = str(next_id)
            key_by_basename[base] = tid
            seen_new.add(base)
            next_id += 1
            added += 1
            if "stems_audio" in str(path):
                added_stems += 1
            elif "Music/Music" in str(path) or "Media.localized" in str(path):
                added_music += 1
            # count analysis already applied in builder
            analysis_tempo += len(track.findall("TEMPO"))
            analysis_cues += len(track.findall("POSITION_MARK"))
            if not dry:
                collection.append(track)
            if samples < args.sample:
                print(f"[ADD] {path} (TrackID={tid})")
                samples += 1

    # On dry-run, also simulate playlist counts without mutating permanently for adds
    # For execute path, update location already done; append adds done.
    # Playlist merge: on dry-run, clone structure in memory is already mutated for updates.
    # Re-parse note: updates already applied to rb_tree in both modes for Location —
    # that's OK for dry-run as we don't write.

    pl_added, pl_linked = add_traktor_playlists(playlists, nml_root, key_by_basename)

    # Fix Entries count (on dry-run, adds were counted but not appended)
    final_count = len(collection.findall("TRACK")) + (added if dry else 0)
    if not dry:
        collection.set("Entries", str(len(collection.findall("TRACK"))))
    else:
        collection.set("Entries", str(final_count))

    print("\n================ REKORDBOX MERGE ================")
    print(f"Mode                         : {'DRY-RUN' if dry else 'EXECUTE'}")
    print(f"Preserved RB TRACK rows      : {preserved:,} (sampler-ish ~{samplerish})")
    print(f"Updated Location from Traktor: {updated:,}  (stems_audio={updated_stems:,}, apple_music={updated_music:,})")
    print(f"New TRACK rows from Traktor  : {added:,}  (stems_audio={added_stems:,}, apple_music={added_music:,})")
    print(f"Skipped missing on disk      : {skipped_missing:,}")
    print(f"Skipped dupe basename adds   : {skipped_dupe_basename:,}")
    print(f"Analysis written (tempo/cues): {analysis_tempo:,} TEMPO / {analysis_cues:,} POSITION_MARK")
    print(f"Traktor playlists folded     : {pl_added:,} lists / {pl_linked:,} entries linked")
    print(f"Output collection size       : {final_count:,}  (preserved + new adds)")
    print(f"Execution time               : {time.time() - started:.2f}s")

    if dry:
        print("\nNo XML written. Existing rekordbox.xml on Terrarum untouched.")
        print("Re-run with --execute to write:", args.output)
        print("Import in Rekordbox: File → Import Collection → rekordbox.xml")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    backup = args.output.with_suffix(".xml.bak")
    if args.output.exists():
        if backup.exists():
            backup.unlink()
        shutil.copy2(args.output, backup)
        print(f"\nBacked up existing output to: {backup}")
    # Also keep a copy of the master baseline beside output for safety
    master_copy = args.output.parent / "rekordbox.master_baseline.xml"
    if not master_copy.exists() and args.master.exists():
        shutil.copy2(args.master, master_copy)
        print(f"Saved master baseline copy: {master_copy}")

    # Sanitize any None attrs inherited from master XML before serialize
    for elem in rb_root.iter():
        for key, val in list(elem.attrib.items()):
            if val is None:
                elem.set(key, "")

    # Pretty-ish write (Py3.9 needs str path)
    ET.indent(rb_tree, space="  ")
    rb_tree.write(str(args.output), encoding="UTF-8", xml_declaration=True)
    print(f"Wrote merged XML: {args.output}")
    print("In Rekordbox 7: File → Import Collection → select this XML (merge/import; Sampler preserved in file).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
