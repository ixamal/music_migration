"""MRBT library migration tooling (Music / Rekordbox / Traktor).

Packages
--------
traktor      NML remap + playlist PRIMARYKEY repair
rekordbox    XML merge/heal + Collection master.db relocate
apple_music  Media.localized hoist + Music.app path compat
stems        stems_audio organize + staging cleanup

JSON catalogs and move manifests: ``config/`` (gitignored).
"""

__version__ = "0.2.0"
