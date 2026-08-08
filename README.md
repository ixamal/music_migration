# music_migration

Traktor / Rekordbox / Apple Music library migration tooling for [ixamal](https://github.com/ixamal) / [alkalurops.org](https://www.alkalurops.org).

This repo tracks **scripts + docs only** — not the audio library. Local SSD paths and collection files stay on the machine / backup volume.

## What this project does

1. Consolidate orphan / stem audio onto `~/Music/stems_audio`
2. Relink Traktor `collection.nml` to local SSD paths
3. Reorganize stems into `{Artist}/{Album}/{Track}.ext`
4. Bridge Traktor cues / grids / playlists → Rekordbox XML
5. Document the performance rig (BlackHole, S88 MkII, S8, DDJ-FLX10)

## Docs

| Doc | Purpose |
|-----|---------|
| [`docs/MASTER_CONTEXT.md`](docs/MASTER_CONTEXT.md) | Architecture, paths, milestones, next tasks |
| [`docs/PROGRESS.md`](docs/PROGRESS.md) | Chronological session log |

## Key scripts

| Script | Role |
|--------|------|
| `update_nml_paths.py` | Index local audio → remap Traktor NML (`--dry-run` supported) |
| `audio_media_catalog.py` | Catalog builder |
| `execute_local_migration.py` | Local consolidation helper |
| `organize_stems.py` | *(planned)* metadata-based stems tree reorg |

## Quick start

```bash
# Safe remap preview (no disk writes)
python3 update_nml_paths.py --dry-run

# Live remap (backs up existing collection.nml first)
python3 update_nml_paths.py
```

Requires: Python 3.9+, `mutagen`, `tinytag`. Master NML is read from `/Volumes/Terrarum/MIGRATION_MASTER/collection.nml`.

## Current status (high level)

- **33,621** Traktor tracks relinked (92.2%)
- **2,812** unmatched (mostly deleted temp / cloud orphans)
- Traktor background analysis running on ~22k newly mapped tracks
- Next: `organize_stems.py` → NML re-remap → Rekordbox bridge → BlackHole / controllers

## Remote

- GitHub: https://github.com/ixamal/music_migration
- Profile: https://github.com/ixamal
