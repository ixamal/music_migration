# Progress Log — music_migration

Chronological notes for the DJ library migration. Canonical paths and architecture live in [`MASTER_CONTEXT.md`](MASTER_CONTEXT.md).

This file + `git log` is the project journal (Confluence without the ceremony).

---

## 2026-08-08 — Traktor phase confirmed; staging cleaned; git checkpoint

### Sanity pass (user + agent)

- User verified crates/playlists in Traktor; `stems_audio` Artist/Album tree looks correct.
- Automated check (same session):
  - COLLECTION: **24,944** entries (Traktor pruned dead links after remap)
  - `stems_audio` COLLECTION: **669 / 669** live
  - `.stem.*` COLLECTION: **527 / 542** live on disk
  - STEM playlist keys: **1,493** live / **37** miss (factory + a few true missing)
  - Headline playlists: Stems 127/130, Xmas 236/239, April Fools 26/26, 2024 Alive 311/322
- **Apple Music / iTunes Media:** parked — do not reorganize before Rekordbox

### Done this session

1. Hardened `update_nml_paths.py` (O(1) basename map, `--dry-run`, no print spam) → **33,621** initial relinks
2. Diagnosed empty playlists: COLLECTION remapped but playlist `PRIMARYKEY` still pointed at `~/Documents/Stems/...`; stem keys use `TYPE=STEM` not only `TRACK`
3. `fix_nml_playlists.py` → repaired **1,476** keys
4. `organize_stems.py --execute` → **3,872** files into `{Artist}/{Album}/`
5. Post-reorg NML remap + playlist repair again
6. `cleanup_staging.py` → rescued **7** uniques to `_rescued_from_staging/`; deleted staging Desktop/Documents/Downloads/Library (**~129GB → ~38MB** repo)
7. GitHub: https://github.com/ixamal/music_migration

### Lessons (keep)

- Always repair playlist PRIMARYKEYs after any path remap
- Quit Traktor before writing `collection.nml` (or it may overwrite)
- Dry-run before moves; basename-stable renames keep NML filename lookup working
- Rekordbox export only after paths are final for that phase
- Git commits = tooling + docs checkpoints; never commit audio/NML/giant JSON

### Next

1. Rekordbox 7 XML bridge → `~/Music/PioneerDJ/rekordbox.xml`
2. Optional later: fold `_rescued_from_staging` into Artist/Album + minor Traktor wrap
3. Optional later: Apple Music Media cleanup (own project; re-wrap Traktor after)
4. BlackHole + S88 MkII / S8 / DDJ-FLX10

### Safety rules

- Never move audio without `--dry-run` first
- Never commit audio, `collection.nml`, or giant catalog JSON to git
- Re-remap NML + playlist keys after any path-changing pass
