"""Hourly electricity demand built from a list of appliances."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Appliance:
    name: str
    watts: float
    quantity: int = 1
    hours_per_day: float = 1.0
    start_hour: int = 0      # usage window start (0 to 23)
    end_hour: int = 24       # usage window end; may wrap past midnight (e.g. 20 to 6)
    duty: float = 1.0        # fraction of time actually drawing power (fridges cycle)

    def window_hours(self) -> list[int]:
        s, e = self.start_hour % 24, self.end_hour
        if e <= s:
            e += 24
        return [h % 24 for h in range(s, e)]

    def daily_kwh(self) -> float:
        return self.watts * self.quantity * self.duty * self.hours_per_day / 1000.0

    def daily_profile_kw(self) -> np.ndarray:
        prof = np.zeros(24)
        hours = self.window_hours()
        if not hours:
            return prof
        frac = min(self.hours_per_day / len(hours), 1.0)
        for h in hours:
            prof[h] += self.watts * self.quantity * self.duty * frac / 1000.0
        return prof


@dataclass
class LoadProfile:
    name: str
    appliances: list[Appliance] = field(default_factory=list)

    def daily_profile_kw(self) -> np.ndarray:
        prof = np.zeros(24)
        for a in self.appliances:
            prof += a.daily_profile_kw()
        return prof

    def daily_kwh(self) -> float:
        return float(self.daily_profile_kw().sum())

    def peak_kw(self) -> float:
        return float(self.daily_profile_kw().max())

    def hourly_kw(self, n_hours: int = 8760, scale: float = 1.0) -> np.ndarray:
        """Repeat the daily profile across the year."""
        reps = int(np.ceil(n_hours / 24))
        return np.tile(self.daily_profile_kw(), reps)[:n_hours] * scale


PRESETS: dict[str, LoadProfile] = {
    "Small home": LoadProfile(
        "Small home",
        [
            Appliance("LED bulbs", 10, 6, 6, 18, 24),
            Appliance("Ceiling fan", 70, 2, 9, 21, 6),
            Appliance("Television + decoder", 100, 1, 5, 18, 23),
            Appliance("Phone charging", 10, 4, 3, 19, 23),
            Appliance("Fridge", 150, 1, 24, 0, 24, duty=0.4),
            Appliance("Laptop", 60, 1, 4, 9, 17),
        ],
    ),
    "Barbing salon": LoadProfile(
        "Barbing salon",
        [
            Appliance("Clippers", 15, 3, 8, 9, 20),
            Appliance("LED bulbs", 10, 4, 10, 9, 21),
            Appliance("Standing fan", 60, 2, 9, 10, 20),
            Appliance("Television", 100, 1, 9, 10, 20),
            Appliance("Sterilizer / dryer", 300, 1, 1, 12, 18),
        ],
    ),
    "Provision shop with freezer": LoadProfile(
        "Provision shop with freezer",
        [
            Appliance("Chest freezer", 200, 1, 24, 0, 24, duty=0.5),
            Appliance("LED bulbs", 10, 4, 6, 17, 23),
            Appliance("Standing fan", 60, 1, 8, 10, 20),
            Appliance("Phone charging point", 10, 10, 6, 10, 20),
        ],
    ),
}
