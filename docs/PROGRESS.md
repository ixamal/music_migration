# Progress Log — music_migration

Chronological notes for the DJ library migration. Canonical paths and architecture live in [`MASTER_CONTEXT.md`](MASTER_CONTEXT.md).

This file + `git log` is the project journal (Confluence without the ceremony).

---

## 2026-08-20 — Apple Music hoist EXECUTED; Traktor + Rekordbox remapped

- Sampler pads: David will rebuild by hand over time. Parked.
- `hoist_apple_music.py --execute` with Music/Traktor/Rekordbox quit:
  - **18,194** moved, **0** errors, **121** kept as `(2)` collisions
  - Nested `Media.localized/Music/` removed (only leftover `.DS_Store` dirs, then pruned)
  - Tree now `{Artist}/{Album}/` — **22,759** of **22,769** audio at depth 3
- Terrarum not mounted → remapped **live** NML (not master). `update_nml_paths.py --nml` + hoist-prefix strip.
- Traktor COLLECTION: **22,259** live / **2,685** miss (old unmatched + factory sounds). Playlist keys: **2,382** live, **905** repaired across two passes, **144** unresolved (recordings/loops/known orphans).
- Rekordbox XML heal: **17,351** nested Music/ paths fixed; **22,930** live / **74** miss / **0** still nested.
- **You:** open Music.app and let it relink; reload rekordbox xml in RB7; reopen Traktor.
- Next: BlackHole + controllers.

### Library.musicdb is encrypted — symlink compat (same night)

Music.app asked Locate per-track (`Less Than Burning Hawt`). `Library.musicdb` is hfma/encrypted; cannot rewrite paths. Locate also started recreating `Media.localized/Music/` (3 files pulled back).

`fix_apple_music_library_paths.py --execute`:
- Backed up musicdb → `~/Music/PioneerDJ/apple_music_library_backups/20260820_221307/`
- Moved the 3 Locate strays back to `{Artist}/{Album}/`
- Replaced nested `Music/` with symlink **`Media.localized/Music` → `.`**
- Old library path now resolves: `Media.localized/Music/Pivots/These Beets/Less Than Burning Hawt.m4a`

Reopen Music.app — playlists should find files without Locate. If Music has **Keep Media folder organized** on, turn it off so it doesn’t fight the symlink.

David confirmed: Music playback/playlists worked; he also cleaned playlists by hand.

**Rekordbox Collection relocate (same night):** XML was already healthy (22,930 live). Per-track Relocate was **Collection** (`master.db`), not XML. With RB quit, `relocate_rekordbox_collection.py --execute` updated **1,157** `FolderPath`s by basename (stems_audio). Left: **224** streaming URLs + **19** dead Downloads/Documents. Backup: `~/Music/PioneerDJ/rekordbox_library_backup_before_old_db/collection_relocate_20260820_223948/`. Reopen Rekordbox.

**Parked — MRBT genre retag (later, with Ollama):** redo genre across Music + Rekordbox + Traktor. Source of truth = file tags; crates/set names (Pivots, Humidor, In My Soul, …) as the vocabulary. First pass is local LLM *inference* + a genre list, not fine-tuning on audio. Fine-tune later only if the label set needs it.

**Next session:** BlackHole + controllers.

---

## 2026-08-10 — Disable Cursor git co-author attribution

- Turned off Commit + PR attribution for local Agent:
  - IDE storage: `attributeCommitsToAgent=false`, `attributePRsToAgent=false`
  - CLI: `~/.cursor/cli-config.json` → `attribution.attributeCommitsToAgent/PRsToAgent: false`
- Project rule: `.cursor/rules/no-cursor-attribution.mdc` + note in `.cursorrules`
- Goal: future commits/PRs authored by David alone (no `Co-authored-by: Cursor` / `Made-with: Cursor`)
- UI cross-check: Cursor Settings → Git & PRs → Attribution (both off). Restart Cursor if toggles look stale.

---

## 2026-08-08 (evening wrap) — Traktor + Rekordbox day; user happy; call it

### Verdict

Huge day. Traktor library + stems tree are in good shape. Rekordbox XML bridge works (acapellas, From Traktor, Apple Music remaps). Sampler **audio** restored; sampler **pad banks** partially recovered via old `master.db` — still imperfect; **manual pad rebuild acceptable**. Apple Music Media left alone. **Stop here for the night.**

---

## Session timeline (what we did)

### A. Traktor NML (earlier → afternoon)

1. Hardened `update_nml_paths.py`
   - O(1) basename dict (avoids `[bracket]` glob blowups)
   - URL-decode + case-insensitive match
   - Removed per-file print spam; `--dry-run` + `--sample`
   - Initial remaps: **33,621** / unmatched **2,812**
2. Traktor analysis on ~22k tracks — **COMPLETE** (user confirmed)
3. Empty playlists diagnosed: COLLECTION remapped but playlist `PRIMARYKEY` still pointed at `~/Documents/Stems/...`
   - Stem keys use `TYPE=STEM` (not only `TRACK`) — **1,530** STEM keys
4. `fix_nml_playlists.py` → repaired **~1,476** keys (Stems 127/130, Xmas 236/239, April Fools 26/26, etc.)
5. `organize_stems.py --execute` → **3,872** files into `stems_audio/{Artist}/{Album}/`
6. Post-reorg: NML remap + playlist repair again
7. Staging cleanup `cleanup_staging.py`
   - Rescued **7** Unicode-only files → `_rescued_from_staging/`
   - Deleted `MIGRATED_ORPHANS/{Desktop,Documents,Downloads,Library}` (~**129GB → ~38MB**)
8. User verified crates/tree — **Traktor phase accepted**
9. GitHub bootstrap: https://github.com/ixamal/music_migration

### B. Rekordbox (evening)

1. **Parked** Apple Music / `Media.localized` reorg (path risk; do later)
2. `traktor_to_rekordbox.py` — **merge**, don’t replace
   - Base: Terrarum `rekordbox.xml` (preserve Sampler TRACK rows + old RB crates)
   - Fold in live Traktor paths (stems_audio + Apple Music remaps), cues/grids, playlists under **From Traktor**
   - Output: `~/Music/PioneerDJ/rekordbox.xml` — **23,004** tracks
   - Preserved **1,574** RB rows; updated **789**; added **21,430**; **33** Traktor playlists
3. Rekordbox 7 has **no** File → Import Collection
   - Use: Preferences → View → Layout → enable **rekordbox xml**
   - Advanced → Database → Imported Library → point at our XML
4. `heal_rekordbox_paths.py` — acapellas still pointed at `~/Documents/Stems…/acapella/`
   - Healed **602** paths by basename → stems_audio Artist/Album
   - Acapella (Spoken) **3→19/21**; Song **14→85/88**; Feb 2026 **17→131/144**
5. Sampler WAVs restored from Terrarum → `~/Music/PioneerDJ/Sampler/` (Capture **71**, OSC presets)
6. Pad banks stayed empty until old DB found
   - **Lesson:** `~/Music/rekordbox` = sample audio only
   - Pad map lives in `~/Library/Pioneer/rekordbox/master.db`
7. User copied old prefs to Terrarum:
   - `/Volumes/Terrarum/MIGRATION_MASTER/rekordbox_old_prefs/Library_Pioneer_rekordbox/` (**master.db 24MB**)
   - `.../Library_Application_Support_Pioneer_rekordbox/` (SamplerSettings, pads, MIDI)
8. Restored old `master.db` + companions into live `~/Library/Pioneer/rekordbox/`
   - Backup of prior live DB: `~/Music/PioneerDJ/rekordbox_library_backup_before_old_db/20260808_224131/`
   - SamplerSettings1.xml into `rekordbox6` (mostly OSC presets NOISE/SINE/SIREN/HORN)
9. User confirmed XML library usable (Acapella Spoken loading, analysis/cues visible). Sampler banks still not fully satisfying → **wrap for today; happy enough.**

---

## Lessons (keep)

- Always repair playlist `PRIMARYKEY`s (`TRACK` **and** `STEM`) after path remaps
- Quit Traktor / Rekordbox before writing their DBs/NML
- Dry-run before moves; keep basenames stable for filename-keyed remaps
- Rekordbox 7 XML = Preferences Imported Library, not File → Import Collection
- Merge RB XML (keep Sampler + old crates); then heal leftover Documents paths
- Sampler **files** ≠ sampler **slots**; slots need `Library/Pioneer/rekordbox/master.db`
- Never commit audio, NML, master.db, or giant JSON to git

---

## Key on-disk artifacts (not in git)

| Artifact | Path |
|----------|------|
| Healed merged XML | `~/Music/PioneerDJ/rekordbox.xml` |
| Master baseline XML | `~/Music/PioneerDJ/rekordbox.master_baseline.xml` |
| Sampler Capture | `~/Music/PioneerDJ/Sampler/Capture/` (71 wav) |
| Old prefs backup (Terrarum) | `/Volumes/Terrarum/MIGRATION_MASTER/rekordbox_old_prefs/` |
| Live DB backup before swap | `~/Music/PioneerDJ/rekordbox_library_backup_before_old_db/` |
| Stems tree | `~/Music/stems_audio/{Artist}/{Album}/` |
| Rescued stragglers | `~/Music/stems_audio/_rescued_from_staging/` |

---

## Next (another day)

1. Sampler pads: finish manually from Capture, or further dig old DB vs RB7 slot model
2. Fold `_rescued_from_staging` into Artist/Album; optional Traktor wrap
3. Apple Music Media cleanup (own project)
4. BlackHole + S88 MkII / S8 / DDJ-FLX10
5. Optional: commit more docs after sampler settled

---

## Safety rules

- Never move audio without `--dry-run` first
- Never commit audio, `collection.nml`, `master.db`, or giant catalog JSON
- Re-remap NML + playlist keys after any path-changing pass
- Backup live `~/Library/Pioneer/rekordbox/` before any DB swap
