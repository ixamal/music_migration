# ALKALUROPS / DAVID — Master Environment & Migration Context

## 1. System Architecture & Environment
- **User / Machine**: David / Mac (Apple Silicon)
- **Primary Shell**: Zsh
- **IDE**: Cursor (Cursor Grok 4.5 agent)
- **Python**: 3.9+ with `mutagen`, `tinytag`
- **Audio Software**: Traktor Pro 4.5.1, Rekordbox 7.2.17, Apple Music
- **GitHub**: https://github.com/ixamal/music_migration (scripts + docs only; no audio)
- **Journal**: `docs/PROGRESS.md` + `git log`
- **Later**: Ollama/MCP, Verse/Unreal, Xcode; BlackHole + controllers

---

## 2. Directory & Path Mapping
- **Repo / scripts**: `~/Music/MIGRATED_ORPHANS` (~38MB after staging cleanup)
- **Terrarum master**: `/Volumes/Terrarum/MIGRATION_MASTER`
  - `collection.nml`, `rekordbox.xml`, Music, PioneerDJ, `rekordbox_old_prefs/`
- **Stems tree**: `~/Music/stems_audio` — `{Artist}/{Album}/{Track}` (~578 artists)
- **Apple Music**: `~/Music/Music/Media` — **do not reorganize yet**
- **Traktor NML**: `~/Documents/Native Instruments/Traktor 4.5.1/collection.nml`
- **Rekordbox XML**: `~/Music/PioneerDJ/rekordbox.xml` (healed merge, ~23k tracks)
- **Rekordbox live DB**: `~/Library/Pioneer/rekordbox/master.db`
- **Rekordbox app settings**: `~/Library/Application Support/Pioneer/rekordbox6/`
- **Sampler audio**: `~/Music/PioneerDJ/Sampler/` (Capture + OSC presets)

---

## 3. Milestones (as of 2026-08-08 evening wrap)
1. Consolidated stems/orphans → `~/Music/stems_audio`; staged cleanup done.
2. Traktor relink (`update_nml_paths.py`): **33,621** / unmatched **2,812**.
3. Traktor analysis: **COMPLETE**.
4. Playlist PRIMARYKEY repair (`fix_nml_playlists.py`): `TYPE=STEM` + `TRACK` (~1,476).
5. Organize stems (`organize_stems.py`): **3,872** → Artist/Album.
6. Staging cleanup (`cleanup_staging.py`): 7 rescued; duplicate trees removed.
7. Traktor crates verified — **Traktor phase accepted**.
8. Rekordbox merge bridge (`traktor_to_rekordbox.py`): Terrarum base + Traktor fold-in → local XML **23,004** tracks; **From Traktor** playlists.
9. Path heal (`heal_rekordbox_paths.py`): **602** Documents/acapella paths → stems_audio.
10. Sampler WAVs restored; old `master.db` restored from Terrarum prefs (partial pad recovery).
11. User confirmed XML library usable in Performance mode; **happy wrap for the day**.

---

## 4. Key scripts
| Script | Role |
|--------|------|
| `update_nml_paths.py` | Remap Traktor LOCATION by basename |
| `fix_nml_playlists.py` | Repair playlist PRIMARYKEYs after remap |
| `organize_stems.py` | Move stems_audio → Artist/Album |
| `cleanup_staging.py` | Rescue uniques; delete staging dup trees |
| `traktor_to_rekordbox.py` | Merge Traktor → Rekordbox XML |
| `heal_rekordbox_paths.py` | Heal dead RB XML paths by basename |
| `restore_rekordbox_master_db.py` | Restore Library `master.db` from Terrarum prefs |

---

## 5. Next (another day)
1. Sampler pads: finish manually from Capture, or dig DB/RB7 slot model further.
2. Fold `_rescued_from_staging/`; optional Traktor wrap.
3. Apple Music / `Media.localized` cleanup (separate project).
4. BlackHole + S88 MkII / S8 / DDJ-FLX10.
