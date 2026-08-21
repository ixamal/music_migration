"""Repo-relative paths. JSON catalogs and move manifests live in config/."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"

HOIST_MANIFEST = CONFIG_DIR / "hoist_apple_music_manifest.json"
ORGANIZE_STEMS_MANIFEST = CONFIG_DIR / "organize_stems_manifest.json"
AUDIO_MEDIA_CATALOG = CONFIG_DIR / "audio_media_catalog.json"
MIGRATION_CANDIDATES = CONFIG_DIR / "migration_candidates.json"


def ensure_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR
