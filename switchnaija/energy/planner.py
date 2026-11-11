"""High-level planner: compare "generator only" with solar + battery options and pick the best.

Typical use
-----------
>>> from switchnaija.energy.planner import Site, plan
>>> site = Site.from_town("Ede", band="C")
>>> result = plan(site)
>>> result.best.summary()
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..battery.ageing import AgeingResult, estimate_life
from ..battery.chemistry import CHEMISTRIES, Chemistry, get_chemistry
from ..config import find_town, load_defaults
from ..sources.pvgis import fetch_pv_hourly
from .dispatch import DispatchResult, simulate
from .economics import (AnnualOperation, Capex, Cashflow, Prices, build_cashflow, npv,
                        operation_from_dispatch, payback_years)
from .generator import Generator
from .grid import outage_schedule
from .load import PRESETS, LoadProfile


@dataclass
class Site:
    name: str
    lat: float
    lon: float
    band: str = "C"                       # NERC band, or "No grid"
    load: LoadProfile = field(default_factory=lambda: PRESETS["Small home"])
    generator: Generator = field(default_factory=Generator)
    load_scale: float = 1.0
    weather: pd.DataFrame | None = None   # hourly pv_kw_per_kwp and temp_c; fetched if None
    seed: int = 42
    gen_hours: tuple[int, int] | None = None  # e.g. (18, 24): generator only used 6pm to midnight

    def gen_mask(self, n: int) -> np.ndarray | None:
        if self.gen_hours is None:
            return None
        s, e = self.gen_hours
        hours = set(range(s, e if e > s else e + 24))
        day = np.array([(h in hours) or (h + 24 in hours) for h in range(24)])
        return np.tile(day, int(np.ceil(n / 24)))[:n]

    @classmethod
    def from_town(cls, town: str, **kw: Any) -> "Site":
        t = find_town(town)
        return cls(name=f"{t['town']}, {t['state']}", lat=t["lat"], lon=t["lon"], **kw)

    def get_weather(self, year: int = 2023) -> pd.DataFrame:
        if self.weather is None:
            self.weather = fetch_pv_hourly(self.lat, self.lon, year=year)
        return self.weather


@dataclass
class Option:
    label: str
    pv_kwp: float
    battery_kwh: float
    chemistry: str | None
    inverter_kw: float
    dispatch: DispatchResult
    operation: AnnualOperation
    capex: Capex
    cashflow: Cashflow
    npv_ngn: float
    payback_years: float | None
    co2_t_per_year: float
    ageing: AgeingResult | None

    def summary(self) -> dict[str, Any]:
        return {
            "option": self.label,
            "pv_kwp": round(self.pv_kwp, 2),
            "battery_kwh": round(self.battery_kwh, 1),
            "chemistry": self.chemistry or "-",
            "inverter_kw": round(self.inverter_kw, 1),
            "upfront_ngn": round(self.capex.total),
            "npv_10y_ngn": round(self.npv_ngn),
            "payback_years": None if self.payback_years is None else round(self.payback_years, 1),
            "fuel_litres_per_year": round(self.operation.fuel_litres),
            "generator_hours_per_year": round(self.operation.generator_hours),
            "solar_share_of_outages_pct": round(100 * self.operation.solar_share_of_outage_load, 1),
            "hours_without_power_per_year": round(self.operation.dark_hours),
            "co2_t_per_year": round(self.co2_t_per_year, 2),
            "battery_life_years": None if not self.ageing else round(self.ageing.life_years, 1),
        }


@dataclass
class PlanResult:
    site: Site
    baseline: Option
    options: list[Option]
    best: Option
    prices: Prices

    def table(self) -> pd.DataFrame:
        return pd.DataFrame([self.baseline.summary()] + [o.summary() for o in self.options])

    def best_per_chemistry(self) -> dict[str, Option]:
        out: dict[str, Option] = {}
        for o in self.options:
            if o.chemistry and (o.chemistry not in out or o.npv_ngn < out[o.chemistry].npv_ngn):
                out[o.chemistry] = o
        return out

    @property
    def co2_saved_t_per_year(self) -> float:
        return self.baseline.co2_t_per_year - self.best.co2_t_per_year

    @property
    def fuel_saved_litres_per_year(self) -> float:
        return self.baseline.operation.fuel_litres - self.best.operation.fuel_litres


def prices_from_defaults(fuel: str, band: str, d: dict | None = None,
                         fuel_price: float | None = None, generator_kva: float = 2.5) -> Prices:
    d = d or load_defaults()
    f = d["fuel"][fuel]
    return Prices(
        fuel_ngn_per_litre=fuel_price if fuel_price else f["price_ngn_per_litre"],
        fuel_co2_kg_per_litre=f["co2_kg_per_litre"],
        grid_tariff_ngn_per_kwh=d["grid"]["tariff_ngn_per_kwh"][band],
        grid_co2_kg_per_kwh=d["grid"]["co2_kg_per_kwh"],
        gen_om_ngn_per_hour=d["generator"]["om_ngn_per_hour_per_kva"] * generator_kva,
        fuel_escalation=d["fuel"]["escalation_per_year"],
        discount_rate=d["finance"]["discount_rate"],
        horizon_years=d["finance"]["horizon_years"],
    )


def calibrate_generator(site: Site, litres_per_day: float, d: dict | None = None) -> float:
    """Return the fuel calibration factor that makes the model match a user's real
    daily fuel use with today's (generator-only) set-up."""
    d = d or load_defaults()
    w = site.get_weather()
    n = len(w)
    off = outage_schedule(d["grid"]["band_hours"][site.band], n_days=n // 24, seed=site.seed)[:n]
    load = site.load.hourly_kw(n, site.load_scale)
    gen = Generator(site.generator.rated_kva, site.generator.fuel, power_factor=site.generator.power_factor)
    res = simulate(load, off, np.zeros(n), 0.0, None, 0.0, gen, gen_allowed=site.gen_mask(n))
    modelled = float(gen.fuel_litres(res.gen_kw).sum()) / (n / 24)
    return litres_per_day / modelled if modelled > 0 else 1.0


def _evaluate(label: str, site: Site, load: np.ndarray, off: np.ndarray, pv1: np.ndarray, temp_c: float,
              pv_kwp: float, batt_kwh: float, chem: Chemistry | None, p: Prices, d: dict,
              base_op: AnnualOperation | None) -> tuple[Option, AnnualOperation]:
    peak = float(load.max())
    inverter_kw = 0.0 if pv_kwp == 0 and batt_kwh == 0 else math.ceil(max(1.3 * peak, 0.8 * pv_kwp) * 2) / 2
    res = simulate(load, off, pv1 * pv_kwp, batt_kwh, chem, inverter_kw, site.generator,
                   c_rate=0.2 if chem and chem.key == "lead_acid" else 0.5, gen_allowed=site.gen_mask(len(load)))
    op = operation_from_dispatch(res, site.generator)
    s = d["solar"]
    batt_cost = batt_kwh * chem.price_ngn_per_kwh if chem else 0.0
    pv_cost = pv_kwp * s["pv_ngn_per_kwp"]
    inv_cost = inverter_kw * s["inverter_ngn_per_kw"]
    capex = Capex(pv_cost, inv_cost, batt_cost, s["installation_fraction"] * (pv_cost + inv_cost + batt_cost))
    ageing = estimate_life(res.soc, chem, temp_c + d["battery"]["room_temp_offset_c"]) if chem and batt_kwh > 0 else None
    base = base_op or op
    cf = build_cashflow(base, op, capex, p, ageing.life_years if ageing else None, batt_cost,
                        s["om_fraction_per_year"] * (pv_cost + inv_cost))
    co2 = op.co2_kg(p) / 1000.0
    opt = Option(label, pv_kwp, batt_kwh, chem.key if chem else None, inverter_kw, res, op, capex, cf,
                 npv(cf.solar_cost, p.discount_rate), (float(pb) if (pb := payback_years(cf)) is not None else None) if base_op else None, co2, ageing)
    return opt, op


def plan(site: Site, chemistries: tuple[str, ...] = CHEMISTRIES, min_solar_share: float = 0.0,
         fuel_price: float | None = None, defaults: dict | None = None,
         pv_multipliers: tuple[float, ...] = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0),
         batt_multipliers: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)) -> PlanResult:
    """Search solar and battery sizes for each chemistry and return the lowest-cost option.

    min_solar_share: require at least this share of outage-hour demand to be covered
    by solar and battery (0 to 1). The generator is kept as backup in every option.
    """
    d = defaults or load_defaults()
    w = site.get_weather()
    n = len(w)
    pv1 = w["pv_kw_per_kwp"].to_numpy()
    temp_c = float(w["temp_c"].mean())
    off = outage_schedule(d["grid"]["band_hours"][site.band], n_days=n // 24, seed=site.seed)[:n]
    load = site.load.hourly_kw(n, site.load_scale)
    p = prices_from_defaults(site.generator.fuel, site.band, d, fuel_price, site.generator.rated_kva)

    baseline, base_op = _evaluate("Generator only (today)", site, load, off, pv1, temp_c, 0.0, 0.0, None, p, d, None)
    baseline.payback_years = None

    daily_load = float(load.sum()) / (n / 24)
    daily_outage_load = float(load[off].sum()) / (n / 24)
    yield_per_kwp_day = float(pv1.sum()) / (n / 24)
    kwp_needed = daily_load / max(yield_per_kwp_day, 0.1)

    options: list[Option] = []
    for key in chemistries:
        chem = get_chemistry(key, d)
        for pm in pv_multipliers:
            pv_kwp = max(round(kwp_needed * pm, 2), 0.25)
            for bm in batt_multipliers:
                batt = max(round(daily_outage_load * bm / chem.max_dod, 1), 0.5)
                opt, _ = _evaluate(f"{chem.label}: {pv_kwp:.2f} kWp + {batt:.1f} kWh", site, load, off, pv1,
                                   temp_c, pv_kwp, batt, chem, p, d, base_op)
                options.append(opt)

    feasible = [o for o in options if o.operation.solar_share_of_outage_load >= min_solar_share] or options
    best = min(feasible, key=lambda o: o.npv_ngn)
    return PlanResult(site, baseline, options, best, p)


def sensitivity(result: PlanResult, fuel_multipliers: tuple[float, ...] = (0.7, 1.0, 1.3)) -> pd.DataFrame:
    """Payback of the chosen option if fuel prices are lower or higher than expected."""
    rows = []
    for m in fuel_multipliers:
        p = Prices(**{**result.prices.__dict__, "fuel_ngn_per_litre": result.prices.fuel_ngn_per_litre * m})
        b = result.best
        base_op = result.baseline.operation
        batt_cost = b.capex.battery_ngn
        pv_om = load_defaults()["solar"]["om_fraction_per_year"] * (b.capex.pv_ngn + b.capex.inverter_ngn)
        cf = build_cashflow(base_op, b.operation, b.capex, p, b.ageing.life_years if b.ageing else None,
                            batt_cost, pv_om)
        rows.append({"fuel_price_ngn_per_litre": round(p.fuel_ngn_per_litre),
                     "payback_years": payback_years(cf),
                     "savings_10y_ngn": round(float(cf.savings[1:].sum() - b.capex.total))})
    return pd.DataFrame(rows)
