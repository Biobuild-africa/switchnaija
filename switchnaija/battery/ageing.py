"""Battery life estimate from a simulated state-of-charge (SOC) history.

Method (linear damage accumulation, as used in tools such as HOMER and SAM):
  * cycle damage   = sum over rainflow cycles of count / N(DoD)
  * calendar damage = 1 / calendar_life(T) per year, faster in hot rooms
  * life (years)    = 1 / (annual cycle damage + annual calendar damage)

End of life means usable capacity has fallen to about 80% of the original.
This is a planning model, not a cell-level electrochemical model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .chemistry import Chemistry
from .rainflow import rainflow


@dataclass
class AgeingResult:
    chemistry: str
    equivalent_full_cycles_per_year: float
    mean_cycle_depth: float
    cycle_damage_per_year: float
    calendar_damage_per_year: float
    life_years: float

    @property
    def dominant_mechanism(self) -> str:
        return "cycling" if self.cycle_damage_per_year >= self.calendar_damage_per_year else "calendar ageing"


def calendar_damage_per_year(chem: Chemistry, temp_c: float | np.ndarray) -> float:
    """Calendar damage per year at one temperature, or averaged over an hourly temperature series.

    Ageing speeds up exponentially with heat, so hot afternoons cost more than cool nights
    save: averaging the damage hour by hour gives a shorter life than using the mean temperature.
    """
    t = np.atleast_1d(np.asarray(temp_c, dtype=float))
    accel = 2.0 ** (np.maximum(t - 25.0, 0.0) / chem.temp_doubling_c)
    return float(np.mean(accel)) / chem.calendar_life_years_25c


def estimate_life(soc: np.ndarray, chem: Chemistry, mean_temp_c: float | np.ndarray,
                  hours_per_year: float | None = None) -> AgeingResult:
    """Estimate battery life from an hourly SOC series (fraction of nominal capacity).

    mean_temp_c: battery temperature in C, either one value or an hourly series.
    """
    soc = np.asarray(soc, dtype=float)
    n_hours = hours_per_year or soc.size
    scale = 8760.0 / n_hours  # annualise if the series is not exactly one year

    cycles = rainflow(soc)
    damage = sum(count / chem.cycles_to_eol(depth) for depth, count in cycles)
    efc = sum(count * depth for depth, count in cycles)
    total_count = sum(count for _, count in cycles)
    mean_depth = (efc / total_count) if total_count else 0.0

    cycle_dmg = damage * scale
    cal_dmg = calendar_damage_per_year(chem, mean_temp_c)
    total = cycle_dmg + cal_dmg
    return AgeingResult(
        chemistry=chem.key,
        equivalent_full_cycles_per_year=efc * scale,
        mean_cycle_depth=mean_depth,
        cycle_damage_per_year=cycle_dmg,
        calendar_damage_per_year=cal_dmg,
        life_years=1.0 / total if total > 0 else float("inf"),
    )
