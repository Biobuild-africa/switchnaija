"""Rainflow cycle counting (ASTM E1049-85, three-point method).

Batteries age with every charge/discharge swing, and deeper swings hurt more.
Rainflow counting breaks an irregular state-of-charge history into individual
cycles, each with a depth (range) and a count of 0.5 or 1.0.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np


def turning_points(series: Iterable[float], tol: float = 1e-9) -> np.ndarray:
    """Keep only the local peaks and valleys of a series."""
    x = np.asarray(list(series), dtype=float)
    if x.size < 3:
        return x
    # drop consecutive duplicates
    keep = np.concatenate(([True], np.abs(np.diff(x)) > tol))
    x = x[keep]
    if x.size < 3:
        return x
    d = np.diff(x)
    sign_change = np.sign(d[1:]) != np.sign(d[:-1])
    idx = np.concatenate(([0], np.where(sign_change)[0] + 1, [x.size - 1]))
    return x[idx]


def rainflow(series: Iterable[float]) -> list[tuple[float, float]]:
    """Return a list of (range, count) pairs, where count is 0.5 or 1.0."""
    stack: list[float] = []
    cycles: list[tuple[float, float]] = []
    for point in turning_points(series):
        stack.append(float(point))
        while len(stack) >= 3:
            x = abs(stack[-1] - stack[-2])
            y = abs(stack[-2] - stack[-3])
            if x < y:
                break
            if len(stack) == 3:
                # Y includes the starting point: count it as a half cycle
                cycles.append((y, 0.5))
                stack.pop(0)
            else:
                cycles.append((y, 1.0))
                last = stack.pop()
                stack.pop()
                stack.pop()
                stack.append(last)
    for a, b in zip(stack[:-1], stack[1:]):
        cycles.append((abs(b - a), 0.5))
    return [(r, c) for r, c in cycles if r > 0]
