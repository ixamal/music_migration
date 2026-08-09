# music_migration

Traktor / Rekordbox / Apple Music library migration tooling for [ixamal](https://github.com/ixamal) / [alkalurops.org](https://www.alkalurops.org).

This repo tracks **scripts + docs only** — not the audio library. Local SSD paths and collection files stay on the machine / backup volume.

**Living log:** `docs/PROGRESS.md` + `git log` = lightweight Confluence (decisions, counts, gotchas) without the overhead.

## What this project does

1. Consolidate orphan / stem audio onto `~/Music/stems_audio`
2. Relink Traktor `collection.nml` to local SSD paths
3. Reorganize stems into `{Artist}/{Album}/{Track}.ext`
4. Repair playlist `PRIMARYKEY`s after moves (`TYPE=TRACK` + `TYPE=STEM`)
5. Bridge Traktor cues / grids / playlists → Rekordbox XML *(next)*
6. Document the performance rig (BlackHole, S88 MkII, S8, DDJ-FLX10)

## Docs

| Doc | Purpose |
|-----|---------|
| [`docs/MASTER_CONTEXT.md`](docs/MASTER_CONTEXT.md) | Architecture, paths, milestones, next tasks |
| [`docs/PROGRESS.md`](docs/PROGRESS.md) | Chronological session log (the “what happened”) |
| `git log` | Immutable checkpoint trail of tooling + decisions |

## Key scripts

| Script | Role |
|--------|------|
| `update_nml_paths.py` | Index local audio → remap Traktor COLLECTION (`--dry-run`) |
| `fix_nml_playlists.py` | Rewrite playlist PRIMARYKEYs to match COLLECTION (`--execute`) |
| `organize_stems.py` | Metadata reorg of `stems_audio` → Artist/Album (dry-run default) |
| `cleanup_staging.py` | Rescue staging-only files; delete duplicate staging trees |
| `audio_media_catalog.py` | Catalog builder |
| `execute_local_migration.py` | Local consolidation helper |

## Quick start

```bash
# Safe remap preview (no disk writes)
python3 update_nml_paths.py --dry-run

# Repair playlist keys after path moves (quit Traktor first)
python3 fix_nml_playlists.py --dry-run
python3 fix_nml_playlists.py --execute
```

Requires: Python 3.9+, `mutagen`, `tinytag`. Master NML: `/Volumes/Terrarum/MIGRATION_MASTER/collection.nml`.

## Status (2026-08-08 sanity pass — confirmed)

**Tree:** `~/Music/stems_audio` → **~578** artist folders, **3,881** audio files, `{Artist}/{Album}/` layout. Staging mirrors gone (`MIGRATED_ORPHANS` ~38MB scripts/docs). `_rescued_from_staging/` holds **7** Unicode stragglers.

**Traktor (user-verified crates + automated check):**

| Check | Result |
|-------|--------|
| Stems playlist | **127 / 130** live |
| Xmas 2023 | **236 / 239** live |
| April Fools 2024 | **26 / 26** live |
| 2024 Alive | **311 / 322** live |
| All STEM playlist keys | **1,493** live / **37** miss |
| `stems_audio` COLLECTION | **669 / 669** live |
| Apple Music Media | **leave alone for now** |

**Parked:** Apple Music/`Media.localized` path cleanup (later).  
**Next:** Rekordbox 7 XML bridge → `~/Music/PioneerDJ/rekordbox.xml`.

## Remote

- GitHub: https://github.com/ixamal/music_migration
- Profile: https://github.com/ixamal
