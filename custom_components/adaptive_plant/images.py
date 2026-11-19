"""Private storage for uploaded plant photos (blocking helpers: run in an executor).

Uploaded photos live under <config>/adaptive_plant/images/, which Home Assistant
never serves. The plant's image entity serves them to signed-in users. 1.2.4 and
earlier saved them under <config>/www/adaptive_plant/, which HA serves to anyone
at /local/; migrate_legacy_image moves such a file into private storage.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .const import IMAGE_DIR, LEGACY_IMAGE_DIR, is_owned_image_path, owned_image_filename

# The shape of a file name the integration gave an upload (uuid4 hex + .jpg).
_UPLOAD_NAME_RE = re.compile(r"^[0-9a-f]{32}\.jpg$")

MIGRATED = "migrated"
ALREADY_PRIVATE = "already_private"
MISSING = "missing"


def private_image_dir(config_dir: str) -> Path:
    return Path(config_dir).joinpath(*IMAGE_DIR)


def legacy_image_dir(config_dir: str) -> Path:
    return Path(config_dir).joinpath(*LEGACY_IMAGE_DIR)


def private_image_file(config_dir: str, path: str) -> Path | None:
    """The private file behind an owned reference, or None for any other path."""
    if not is_owned_image_path(path):
        return None
    return private_image_dir(config_dir) / owned_image_filename(path)


def delete_owned_image(config_dir: str, path: str | None) -> None:
    """Best-effort delete of an owned image, wherever it is (private or legacy www/)."""
    if not is_owned_image_path(path):
        return
    name = owned_image_filename(path)
    for folder in (private_image_dir(config_dir), legacy_image_dir(config_dir)):
        try:
            (folder / name).unlink()
        except OSError:
            pass


def migrate_legacy_image(config_dir: str, path: str | None) -> str | None:
    """Move an owned image from www/adaptive_plant/ into private storage.

    Crash-safe by ordering: the private copy is written to a temp file, fsynced
    and renamed into place, and only then is the public file removed. A restart
    between the two steps finds both files and just finishes the removal. The
    config entry keeps the same reference, so nothing else needs rewriting.
    Returns None for a path that isn't owned, else MIGRATED / ALREADY_PRIVATE /
    MISSING. Raises OSError if the copy or the removal fails.
    """
    if not is_owned_image_path(path):
        return None
    name = owned_image_filename(path)
    public = legacy_image_dir(config_dir) / name
    private = private_image_dir(config_dir) / name

    if not public.exists():
        return ALREADY_PRIVATE if private.exists() else MISSING

    size = public.stat().st_size
    if not (private.exists() and private.stat().st_size == size):
        private.parent.mkdir(parents=True, exist_ok=True)
        tmp = private.with_name(private.name + ".part")
        with open(public, "rb") as src, open(tmp, "wb") as dst:
            dst.write(src.read())
            dst.flush()
            os.fsync(dst.fileno())
        if tmp.stat().st_size != size:
            tmp.unlink()
            raise OSError(f"incomplete copy of {name}")
        os.replace(tmp, private)
    public.unlink()
    return MIGRATED


def unused_public_uploads(config_dir: str, referenced: set[str]) -> list[str]:
    """Upload-shaped files left in www/adaptive_plant/ that no plant uses.

    Only names the integration generates are considered, so a user's own
    images there (monstera.png) are never listed.
    """
    folder = legacy_image_dir(config_dir)
    try:
        entries = list(folder.iterdir())
    except OSError:
        return []
    return sorted(
        p.name for p in entries
        if _UPLOAD_NAME_RE.match(p.name) and p.name not in referenced and p.is_file()
    )


def delete_public_uploads(config_dir: str, names: list[str]) -> int:
    """Delete the named upload-shaped files from www/adaptive_plant/; returns how many."""
    folder = legacy_image_dir(config_dir)
    deleted = 0
    for name in names:
        if not _UPLOAD_NAME_RE.match(name):
            continue
        try:
            (folder / name).unlink()
            deleted += 1
        except OSError:
            pass
    return deleted
