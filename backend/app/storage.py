"""Local-disk blob storage for evidence attachments. One file per key under
``settings.data_dir/attachments``. Swap the three functions for an S3 client to
move it off the box."""

from __future__ import annotations

import hashlib
import os
import secrets

from .config import settings


def _root() -> str:
    path = os.path.join(settings.data_dir, "attachments")
    os.makedirs(path, exist_ok=True)
    return path


def save(data: bytes) -> tuple[str, str, int]:
    """Write bytes, return (storage_key, sha256_hex, size)."""
    digest = hashlib.sha256(data).hexdigest()
    key = f"{digest[:2]}/{digest}-{secrets.token_hex(4)}"
    full = os.path.join(_root(), key)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as fh:
        fh.write(data)
    return key, digest, len(data)


def load(key: str) -> bytes:
    with open(os.path.join(_root(), key), "rb") as fh:
        return fh.read()


def delete(key: str) -> None:
    try:
        os.remove(os.path.join(_root(), key))
    except FileNotFoundError:
        pass
