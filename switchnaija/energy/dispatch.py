"""Hour-by-hour energy balance for a home or shop with grid, solar, battery and generator.

Rules (a typical Nigerian hybrid-inverter set-up, "solar first"):
  1. Solar always serves the load first.
  2. Surplus solar charges the battery; anything left is curtailed.
  3. When the grid is ON, any remaining load is bought from the grid. The battery
     is not discharged, so it stays full for the next outage. Optionally the grid
     tops up the battery.
  4. When the grid is OFF, the battery covers the remaining load down to its
     minimum state of charge; after that the generator (if kept as backup) runs.
     If there is no generator, the remaining load is unserved.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..battery.chemistry import Chemistry
from .generator import Generator


@dataclass
class DispatchResult:
    load_kw: np.ndarray
    grid_off: np.ndarray
    pv_kw: np.ndarray
    pv_used_kw: np.ndarray
    curtailed_kw: np.ndarray
    batt_charge_kw: np.ndarray
    batt_discharge_kw: np.ndarray
    soc: np.ndarray
    grid_import_kw: np.ndarray
    grid_charge_kw: np.ndarray
    gen_kw: np.ndarray
    unmet_kw: np.ndarray

    # Summary helpers (energy in kWh over the simulated period)
    def total(self, name: str) -> float:
        return float(getattr(self, name).sum())

    @property
    def outage_load_kwh(self) -> float:
        return float(self.load_kw[self.grid_off].sum())

    @property
    def solar_share_of_outage_load(self) -> float:
        """Share of the load during outages met by solar or battery (not generator)."""
        out = self.outage_load_kwh
        if out <= 0:
            return 1.0
        served_clean = out - float(self.gen_kw[self.grid_off].sum()) - float(self.unmet_kw[self.grid_off].sum())
        return max(0.0, served_clean / out)

    def energy_balance_error(self) -> float:
        """Load minus all sources; should be ~0. Used in tests."""
        supplied = (self.pv_used_kw + self.batt_discharge_kw + self.grid_import_kw - self.grid_charge_kw
                    + self.gen_kw + self.unmet_kw)
        return float(np.abs(self.load_kw - supplied).max())


def simulate(load_kw: np.ndarray, grid_off: np.ndarray, pv_kw: np.ndarray,
             battery_kwh: float, chem: Chemistry | None, inverter_kw: float,
             generator: Generator | None, grid_charging: bool = False,
             c_rate: float = 0.5, gen_allowed: np.ndarray | None = None) -> DispatchResult:
    """gen_allowed: optional boolean array, True in hours when the household is willing to
    run the generator (e.g. evenings only). Outage load outside those hours goes unserved."""
    n = len(load_kw)
    load = np.asarray(load_kw, dtype=float)
    pv = np.asarray(pv_kw, dtype=float)
    off = np.asarray(grid_off, dtype=bool)

    pv_used = np.zeros(n); curtailed = np.zeros(n)
    ch = np.zeros(n); dis = np.zeros(n); soc_arr = np.zeros(n)
    grid = np.zeros(n); gch = np.zeros(n); gen = np.zeros(n); unmet = np.zeros(n)

    has_batt = battery_kwh > 0 and chem is not None
    eta = chem.charge_efficiency if has_batt else 1.0
    soc_min = (1.0 - chem.max_dod) if has_batt else 0.0
    p_batt_max = min(inverter_kw, c_rate * battery_kwh) if has_batt else 0.0
    gen_cap = generator.rated_kw if generator else 0.0
    soc = 1.0

    allow_l = (np.ones(n, dtype=bool) if gen_allowed is None else np.asarray(gen_allowed, dtype=bool)).tolist()
    load_l = load.tolist(); pv_l = pv.tolist(); off_l = off.tolist()
    for t in range(n):
        L = load_l[t]
        # solar output is limited by the inverter rating
        P = min(pv_l[t], inverter_kw) if inverter_kw > 0 else 0.0
        used = min(P, L)
        rem_load = L - used
        surplus = P - used

        c = 0.0
        if has_batt and surplus > 0:
            room_kwh = (1.0 - soc) * battery_kwh / eta
            c = min(surplus, p_batt_max, room_kwh)
            soc += c * eta / battery_kwh
        curtailed[t] = surplus - c

        d = 0.0
        if off_l[t]:
            if has_batt and rem_load > 0:
                avail_kwh = max(soc - soc_min, 0.0) * battery_kwh * eta
                d = min(rem_load, p_batt_max, avail_kwh)
                soc -= d / eta / battery_kwh
                rem_load -= d
            g = min(rem_load, gen_cap) if allow_l[t] else 0.0
            gen[t] = g
            unmet[t] = rem_load - g
        else:
            grid[t] = rem_load
            if has_batt and grid_charging and soc < 1.0:
                room_kwh = (1.0 - soc) * battery_kwh / eta
                gc = min(p_batt_max - c, room_kwh)
                if gc > 0:
                    soc += gc * eta / battery_kwh
                    grid[t] += gc
                    gch[t] = gc
                    c += gc
        pv_used[t] = used
        ch[t] = c
        dis[t] = d
        soc_arr[t] = soc

    return DispatchResult(load, off, pv, pv_used, curtailed, ch, dis, soc_arr, grid, gch, gen, unmet)
