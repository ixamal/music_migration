# 🚀 ALKALUROPS / DAVID MASTER ENVIRONMENT & MIGRATION CONTEXT

## 1. System Architecture & Environment
- **User / Machine**: David / Mac (Apple Silicon)
- **Primary Shell**: Zsh (`~/.zshrc` configured, errors resolved)
- **IDE**: Cursor (with Cursor Grok 4.5 agent enabled)
- **Python Environment**: System/Framework Python 3.9+ with `mutagen`, `tinytag` installed
- **Audio Software**: Traktor Pro 4.5.1, Rekordbox 7.2.17, Apple Music
- **GitHub Project**: https://github.com/ixamal/music_migration (scripts + docs only; no audio)
- **Project journal**: `docs/PROGRESS.md` + `git log` (lightweight Confluence)
- **Future Tech Stack**: Local LLMs (Ollama / MCP), Verse / Unreal Engine 6.0, Xcode / Swift, Git workflows

---

## 2. Directory & Path Mapping
- **Staging / Migration Root**: `~/Music/MIGRATED_ORPHANS` *(scripts/docs only after cleanup; ~38MB)*
- **Master External Backup Volume**: `/Volumes/Terrarum/MIGRATION_MASTER`
  - Master Collection: `/Volumes/Terrarum/MIGRATION_MASTER/collection.nml` (52 MB)
  - Master Rekordbox XML: `/Volumes/Terrarum/MIGRATION_MASTER/rekordbox.xml`
- **Consolidated Local Audio Root (SSD)**: `~/Music/stems_audio` — `{Artist}/{Album}/{Track}` (~578 artists, ~3.8k files)
- **Apple Music Media Root (SSD)**: `~/Music/Music/Media` — **do not reorganize yet**
- **Traktor 4.5.1 Local Collection**: `~/Documents/Native Instruments/Traktor 4.5.1/collection.nml`
- **Rekordbox Local Target**: `~/Music/PioneerDJ/rekordbox.xml`

---

## 3. Milestones Accomplished
1. **Local Migration Execution**: Consolidated loose audio/stems/orphans onto `~/Music/stems_audio`.
2. **Traktor NML Relink (`update_nml_paths.py`)**: O(1) basename index; **33,621** initial relinks (92.2%).
3. **Traktor analysis pass**: COMPLETE.
4. **Playlist PRIMARYKEY repair (`fix_nml_playlists.py`)**: Fixed `TYPE=STEM` + `TRACK` keys after path moves (~1,476 repairs).
5. **Stems tree organize (`organize_stems.py`)**: 3,872 files → `{Artist}/{Album}/`.
6. **Staging cleanup (`cleanup_staging.py`)**: Rescued 7 uniques; removed duplicate staging trees.
7. **Sanity pass 2026-08-08**: User confirmed crates/tree; agent verified playlist liveness (Stems 127/130, April Fools 26/26, etc.). **Traktor phase accepted.**

---

## 4. Next Technical Tasks
1. **Rekordbox 7 XML Bridge**:
   - Convert/write Traktor cues, grids, and playlists into `~/Music/PioneerDJ/rekordbox.xml`.
2. **Optional hygiene (later)**:
   - Fold `_rescued_from_staging/` into Artist/Album; remove locked `stems_audio/Library` Google Drive shortcut via Finder.
   - Apple Music / `Media.localized` cleanup as a separate project (re-wrap Traktor after).
3. **Dev Tools & Local AI Integration**:
   - Configure Ollama MCP servers in Cursor for offline coding.
   - Hook in Unreal Engine (Verse/C++) and Xcode project templates.
4. **Performance Rig: BlackHole + Controllers** (after library paths are stable):
   - **BlackHole** for virtual audio + MIDI between Traktor and Rekordbox.
   - Traktor: **S88 MkII** + **S8**; Rekordbox: **DDJ-FLX10**.
   - One app ↔ one primary controller first, then dual-software via BlackHole.
