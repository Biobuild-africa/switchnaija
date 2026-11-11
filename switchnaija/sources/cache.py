"""Tiny JSON/Parquet-free cache so repeated runs do not re-download data."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

import requests

USER_AGENT = "switchnaija/0.1 (+https://github.com/Biobuild-africa/switchnaija)"


def cache_dir() -> Path:
    root = Path(os.environ.get("SWITCHNAIJA_CACHE", Path.home() / ".cache" / "switchnaija"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _key(url: str, params: dict[str, Any] | None) -> str:
    raw = url + json.dumps(params or {}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def get_json(url: str, params: dict[str, Any] | None = None, timeout: int = 90,
             loader: Callable[[requests.Response], Any] | None = None) -> Any:
    """GET a JSON document, caching the result on disk."""
    path = cache_dir() / f"{_key(url, params)}.json"
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    resp = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    data = loader(resp) if loader else resp.json()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return data
