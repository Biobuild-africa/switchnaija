"""Grid availability from the NERC tariff band.

NERC bands commit a minimum number of supply hours per day (Band A 20 h down to
Band E 4 h). Real outages come in blocks at irregular times, so we generate a
reproducible random schedule: each day the outage hours are split into one to
three blocks placed at random, non-overlapping times.
"""

from __future__ import annotations

import numpy as np


def outage_schedule(supply_hours_per_day: float, n_days: int = 365, seed: int = 42,
                    max_blocks: int = 3) -> np.ndarray:
    """Return a boolean array of length 24*n_days, True where the grid is OFF."""
    outage_h = int(round(24 - supply_hours_per_day))
    outage_h = min(max(outage_h, 0), 24)
    rng = np.random.default_rng(seed)
    off = np.zeros(24 * n_days, dtype=bool)
    if outage_h == 0:
        return off
    if outage_h == 24:
        off[:] = True
        return off
    for day in range(n_days):
        n_blocks = int(rng.integers(1, min(max_blocks, outage_h) + 1))
        # split outage hours into n_blocks positive parts
        cuts = np.sort(rng.choice(np.arange(1, outage_h), size=n_blocks - 1, replace=False)) if n_blocks > 1 else []
        lengths = np.diff(np.concatenate(([0], cuts, [outage_h]))).astype(int)
        # place blocks in random order around the 24 h ring without overlap
        gaps_total = 24 - outage_h
        gap_cuts = np.sort(rng.integers(0, gaps_total + 1, size=n_blocks))
        gaps = np.diff(np.concatenate(([0], gap_cuts)))
        offset = int(rng.integers(0, 24))
        pos = offset
        for g, length in zip(gaps, lengths):
            pos += int(g)
            for h in range(int(length)):
                off[day * 24 + (pos + h) % 24] = True
            pos += int(length)
    return off
