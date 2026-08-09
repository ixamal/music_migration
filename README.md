# music_migration

Traktor / Rekordbox / Apple Music library migration tooling for [ixamal](https://github.com/ixamal) / [alkalurops.org](https://www.alkalurops.org).

This repo tracks **scripts + docs only** — not the audio library. Local SSD paths and collection files stay on the machine / backup volume.

**Living log:** `docs/PROGRESS.md` + `git log` = lightweight Confluence (decisions, counts, gotchas).

## What this project does

1. Consolidate orphan / stem audio onto `~/Music/stems_audio`
2. Relink Traktor `collection.nml` to local SSD paths
3. Reorganize stems into `{Artist}/{Album}/{Track}.ext`
4. Repair playlist `PRIMARYKEY`s after moves (`TYPE=TRACK` + `TYPE=STEM`)
5. Bridge Traktor → Rekordbox XML (merge + path heal)
6. Restore / document Rekordbox sampler DB + Capture audio
7. Document the performance rig (BlackHole, S88 MkII, S8, DDJ-FLX10)

## Docs

| Doc | Purpose |
|-----|---------|
| [`docs/MASTER_CONTEXT.md`](docs/MASTER_CONTEXT.md) | Architecture, paths, milestones, next tasks |
| [`docs/PROGRESS.md`](docs/PROGRESS.md) | Chronological session log |
| `git log` | Immutable checkpoint trail |

## Key scripts

| Script | Role |
|--------|------|
| `update_nml_paths.py` | Index local audio → remap Traktor COLLECTION (`--dry-run`) |
| `fix_nml_playlists.py` | Rewrite playlist PRIMARYKEYs (`--execute`) |
| `organize_stems.py` | Metadata reorg of `stems_audio` → Artist/Album |
| `cleanup_staging.py` | Rescue staging-only files; delete duplicate trees |
| `traktor_to_rekordbox.py` | Merge Traktor into Terrarum RB XML → local XML |
| `heal_rekordbox_paths.py` | Heal dead RB XML locations by basename |
| `restore_rekordbox_master_db.py` | Restore `master.db` from Terrarum old prefs |
| `audio_media_catalog.py` | Catalog builder |
| `execute_local_migration.py` | Local consolidation helper |

## Quick start

```bash
# Safe remap preview (no disk writes)
python3 update_nml_paths.py --dry-run

# Repair playlist keys after path moves (quit Traktor first)
python3 fix_nml_playlists.py --dry-run
python3 fix_nml_playlists.py --execute

# Rekordbox XML merge (quit Rekordbox first for --execute)
python3 traktor_to_rekordbox.py --dry-run
python3 heal_rekordbox_paths.py --dry-run
```

Requires: Python 3.9+, `mutagen`, `tinytag`.

Rekordbox 7: Preferences → View → Layout → enable **rekordbox xml**; Advanced → Database → Imported Library → `~/Music/PioneerDJ/rekordbox.xml`.

## Status (2026-08-08 evening wrap)

**Traktor:** Accepted. Stems tree organized; playlists repaired; analysis complete.

**Rekordbox:** Merged XML (~23k tracks) + path heal (602) working in Performance mode. Sampler Capture WAVs restored; pad banks partially recovered via old `master.db` — finish manually another day.

**Parked:** Apple Music / `Media.localized` reorg.

**Next session:** Sampler pads; rescued stragglers; BlackHole + controllers.

## Remote

- GitHub: https://github.com/ixamal/music_migration
- Profile: https://github.com/ixamal
