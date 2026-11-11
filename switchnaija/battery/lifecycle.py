"""Battery Afterlife: how long each battery type lasts in a given room, what it costs over
ten years, and how much battery waste (and lead) it leaves behind.

Every chemistry is sized to deliver the same usable energy each day, so the comparison is fair:
lead-acid should only be emptied to about 50%, so it needs roughly twice the nominal capacity of LFP.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import load_defaults
from .ageing import estimate_life
from .chemistry import CHEMISTRIES, get_chemistry

ROOMS = tuple(load_defaults()["battery"]["rooms"].keys())


@dataclass
class BatteryUse:
    daily_kwh: float = 2.0                 # energy drawn from the battery on a day it is used
    days_per_week: float = 7.0             # how many days a week the battery is emptied
    oversize: float = 1.0                  # 1.0 = smallest bank that delivers daily_kwh safely
    room: str = "Ventilated room indoors"


@dataclass
class LifecycleResult:
    chemistry: str
    label: str
    capacity_kwh: float
    cycle_depth: float
    equivalent_full_cycles_per_year: float
    life_years: float
    dominant_mechanism: str
    mean_battery_temp_c: float
    batteries_bought: int
    replacement_years: list[int]
    upfront_ngn: float
    cost_npv_ngn: float
    cost_per_kwh_ngn: float
    kwh_delivered: float
    kwh_lost_charging: float
    waste_kg: float
    lead_kg: float
    cumulative_cost_ngn: list[float] = field(default_factory=list)


def room_temperature(outdoor_c: np.ndarray, room: str, defaults: dict | None = None) -> np.ndarray:
    """Hourly battery temperature for a type of battery space."""
    r = (defaults or load_defaults())["battery"]["rooms"][room]
    t = np.asarray(outdoor_c, dtype=float)
    return np.full_like(t, r["fixed_c"]) if "fixed_c" in r else t + r["offset_c"]


def _usage_days(days_per_week: float, n_days: int) -> np.ndarray:
    """Spread the days of use evenly through the year."""
    f = min(max(days_per_week, 0.0), 7.0) / 7.0
    i = np.arange(n_days)
    return np.floor((i + 1) * f) > np.floor(i * f)


def soc_series(depth: float, days_per_week: float, n_days: int = 365) -> np.ndarray:
    """Hourly state of charge, one day per block starting at 6pm: emptied evenly over 12 hours
    (6pm to 6am), idle until 9am, recharged by solar 9am to 3pm, then full until 6pm.
    Days without use stay full. Only the cycles matter here, not the clock time."""
    day = np.concatenate([1 - depth * np.arange(1, 13) / 12,     # 6pm to 6am
                          np.full(3, 1 - depth),                 # 6am to 9am
                          1 - depth + depth * np.arange(1, 7) / 6,  # 9am to 3pm
                          np.ones(3)])                           # 3pm to 6pm
    idle = np.ones(24)
    return np.concatenate([day if u else idle for u in _usage_days(days_per_week, n_days)])


def evaluate(key: str, use: BatteryUse, outdoor_temp_c: np.ndarray, defaults: dict | None = None,
             price_ngn_per_kwh: float | None = None) -> LifecycleResult:
    d = defaults or load_defaults()
    chem = get_chemistry(key, d)
    eta = chem.charge_efficiency
    capacity = use.daily_kwh / eta / chem.max_dod * max(use.oversize, 1.0)
    depth = use.daily_kwh / eta / capacity if capacity > 0 else 0.0

    temps = room_temperature(outdoor_temp_c, use.room, d)
    soc = soc_series(depth, use.days_per_week, n_days=len(temps) // 24 or 365)
    temps = np.resize(temps, soc.size)
    age = estimate_life(soc, chem, temps)

    horizon = int(d["finance"]["horizon_years"])
    rate = float(d["finance"]["discount_rate"])
    price = chem.price_ngn_per_kwh if price_ngn_per_kwh is None else price_ngn_per_kwh
    cost = capacity * price
    cash = [cost] + [0.0] * horizon
    repl: list[int] = []
    life = age.life_years
    if math.isfinite(life) and life > 0:
        k = 1
        while k * life < horizon:
            yr = max(1, math.ceil(k * life))
            repl.append(yr)
            cash[yr] += cost
            k += 1
        used_in_last = (horizon - (k - 1) * life) / life
        cash[-1] -= cost * max(0.0, 1.0 - used_in_last)   # credit for life left at the end
    npv_cost = float(sum(c / (1 + rate) ** t for t, c in enumerate(cash)))

    kwh_year = use.daily_kwh * 365 * min(use.days_per_week, 7) / 7
    disc_kwh = sum(kwh_year / (1 + rate) ** t for t in range(1, horizon + 1))
    bought = 1 + len(repl)
    waste = bought * capacity * chem.kg_per_kwh
    return LifecycleResult(
        chemistry=key, label=chem.label, capacity_kwh=capacity, cycle_depth=depth,
        equivalent_full_cycles_per_year=age.equivalent_full_cycles_per_year, life_years=life,
        dominant_mechanism=age.dominant_mechanism, mean_battery_temp_c=float(np.mean(temps)),
        batteries_bought=bought, replacement_years=repl, upfront_ngn=cost, cost_npv_ngn=npv_cost,
        cost_per_kwh_ngn=npv_cost / disc_kwh if disc_kwh else float("nan"),
        kwh_delivered=kwh_year * horizon, kwh_lost_charging=kwh_year * horizon * (1 / chem.round_trip_efficiency - 1),
        waste_kg=waste, lead_kg=waste * chem.lead_fraction,
        cumulative_cost_ngn=list(np.cumsum(cash)),
    )


def compare(use: BatteryUse, outdoor_temp_c: np.ndarray, chemistries: tuple[str, ...] = CHEMISTRIES,
            defaults: dict | None = None, prices: dict[str, float] | None = None) -> dict[str, LifecycleResult]:
    """Lifecycle result for each chemistry, all sized to deliver the same daily energy."""
    prices = prices or {}
    return {k: evaluate(k, use, outdoor_temp_c, defaults, prices.get(k)) for k in chemistries}


def room_sensitivity(use: BatteryUse, outdoor_temp_c: np.ndarray, chemistries: tuple[str, ...] = CHEMISTRIES,
                     defaults: dict | None = None) -> pd.DataFrame:
    """Battery life (years) for every type of battery space."""
    rows = []
    for room in ROOMS:
        u = BatteryUse(use.daily_kwh, use.days_per_week, use.oversize, room)
        for k in chemistries:
            r = evaluate(k, u, outdoor_temp_c, defaults)
            rows.append({"room": room, "chemistry": r.label, "life_years": r.life_years,
                         "mean_temp_c": r.mean_battery_temp_c})
    return pd.DataFrame(rows)
