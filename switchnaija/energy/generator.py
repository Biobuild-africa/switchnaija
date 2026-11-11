"""Generator fuel use and emissions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import load_defaults


@dataclass
class Generator:
    rated_kva: float = 2.5
    fuel: str = "petrol"            # "petrol" or "diesel"
    F0: float | None = None         # litres per hour per kW rated (no-load burn)
    F1: float | None = None         # litres per kWh delivered
    calibration: float = 1.0        # multiply fuel use to match a user's real consumption
    power_factor: float | None = None  # kVA to kW; petrol sets ~1.0, diesel sets 0.8

    def __post_init__(self) -> None:
        g = load_defaults()["generator"]
        curve = g["fuel_curve"][self.fuel]
        self.F0 = curve["F0"] if self.F0 is None else self.F0
        self.F1 = curve["F1"] if self.F1 is None else self.F1
        if self.power_factor is None:
            self.power_factor = g["power_factor"][self.fuel]

    def om_ngn_per_hour(self, defaults: dict | None = None) -> float:
        g = (defaults or load_defaults())["generator"]
        return g["om_ngn_per_hour_per_kva"] * self.rated_kva

    @property
    def rated_kw(self) -> float:
        return self.rated_kva * self.power_factor

    def fuel_litres(self, output_kw: np.ndarray) -> np.ndarray:
        """Litres burned in each hour; zero when the set is off (output 0)."""
        out = np.minimum(np.asarray(output_kw, dtype=float), self.rated_kw)
        running = out > 1e-9
        litres = (self.F0 * self.rated_kw + self.F1 * out) * running
        return litres * self.calibration
