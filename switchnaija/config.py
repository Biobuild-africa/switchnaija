"""Load default assumptions and the list of Nigerian towns."""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).parent / "data"


@lru_cache(maxsize=1)
def _defaults_cached() -> dict[str, Any]:
    with open(DATA_DIR / "defaults.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_defaults() -> dict[str, Any]:
    """Return a fresh, editable copy of the default assumptions."""
    return copy.deepcopy(_defaults_cached())


@lru_cache(maxsize=1)
def towns() -> list[dict[str, Any]]:
    """State capitals of all 36 states and the FCT, plus a few extra towns.

    Coordinates come from OpenStreetMap Nominatim.
    """
    with open(DATA_DIR / "towns.json", encoding="utf-8") as fh:
        return json.load(fh)


def find_town(name: str) -> dict[str, Any]:
    """Look up a town by name (case-insensitive)."""
    for t in towns():
        if t["town"].lower() == name.lower():
            return t
    raise KeyError(f"Unknown town: {name!r}")
