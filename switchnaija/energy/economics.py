"""Costs, savings, payback and emissions over the analysis horizon."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..battery.ageing import AgeingResult
from ..battery.chemistry import Chemistry
from .dispatch import DispatchResult
from .generator import Generator


@dataclass
class Prices:
    fuel_ngn_per_litre: float
    fuel_co2_kg_per_litre: float
    grid_tariff_ngn_per_kwh: float
    grid_co2_kg_per_kwh: float
    gen_om_ngn_per_hour: float
    fuel_escalation: float = 0.05
    discount_rate: float = 0.12
    horizon_years: int = 10


@dataclass
class Capex:
    pv_ngn: float = 0.0
    inverter_ngn: float = 0.0
    battery_ngn: float = 0.0
    installation_ngn: float = 0.0

    @property
    def total(self) -> float:
        return self.pv_ngn + self.inverter_ngn + self.battery_ngn + self.installation_ngn


@dataclass
class AnnualOperation:
    fuel_litres: float
    generator_hours: float
    grid_kwh: float
    unmet_kwh: float
    solar_share_of_outage_load: float
    dark_hours: float = 0.0          # outage hours with some demand left unserved

    def cost_ngn(self, p: Prices, year: int = 1, pv_om_ngn: float = 0.0) -> float:
        fuel_price = p.fuel_ngn_per_litre * (1 + p.fuel_escalation) ** (year - 1)
        return (self.fuel_litres * fuel_price + self.generator_hours * p.gen_om_ngn_per_hour
                + self.grid_kwh * p.grid_tariff_ngn_per_kwh + pv_om_ngn)

    def co2_kg(self, p: Prices) -> float:
        return self.fuel_litres * p.fuel_co2_kg_per_litre + self.grid_kwh * p.grid_co2_kg_per_kwh


def operation_from_dispatch(res: DispatchResult, gen: Generator | None) -> AnnualOperation:
    scale = 8760.0 / len(res.load_kw)
    litres = float(gen.fuel_litres(res.gen_kw).sum()) if gen else 0.0
    return AnnualOperation(
        fuel_litres=litres * scale,
        generator_hours=float((res.gen_kw > 1e-9).sum()) * scale,
        grid_kwh=res.total("grid_import_kw") * scale,
        unmet_kwh=res.total("unmet_kw") * scale,
        solar_share_of_outage_load=res.solar_share_of_outage_load,
        dark_hours=float((res.unmet_kw > 1e-6).sum()) * scale,
    )


@dataclass
class Cashflow:
    years: list[int]
    baseline_cost: list[float]
    solar_cost: list[float]
    capex: Capex
    battery_replacement_years: list[int] = field(default_factory=list)
    battery_salvage_ngn: float = 0.0

    @property
    def savings(self) -> np.ndarray:
        return np.array(self.baseline_cost) - np.array(self.solar_cost)


def build_cashflow(base: AnnualOperation, solar: AnnualOperation, capex: Capex, p: Prices,
                   battery_life_years: float | None, battery_cost_ngn: float,
                   pv_om_ngn_per_year: float) -> Cashflow:
    years = list(range(0, p.horizon_years + 1))
    base_cost = [0.0] + [base.cost_ngn(p, y) for y in years[1:]]
    solar_cost = [capex.total] + [solar.cost_ngn(p, y, pv_om_ngn_per_year) for y in years[1:]]

    replacements: list[int] = []
    salvage = 0.0
    if battery_life_years and math.isfinite(battery_life_years) and battery_cost_ngn > 0:
        k = 1
        while k * battery_life_years < p.horizon_years:
            yr = max(1, math.ceil(k * battery_life_years))
            replacements.append(yr)
            solar_cost[yr] += battery_cost_ngn
            k += 1
        # value of battery life left over at the end of the horizon (straight-line)
        used_in_last = (p.horizon_years - (k - 1) * battery_life_years) / battery_life_years
        salvage = battery_cost_ngn * max(0.0, 1.0 - used_in_last)
        solar_cost[-1] -= salvage
    return Cashflow(years, base_cost, solar_cost, capex, replacements, salvage)


def npv(values: list[float], rate: float) -> float:
    return float(sum(v / (1 + rate) ** t for t, v in enumerate(values)))


def payback_years(cf: Cashflow, rate: float = 0.0) -> float | None:
    """Years until cumulative (optionally discounted) savings repay the upfront cost."""
    cum = 0.0
    for t, s in enumerate(cf.savings):
        disc = s / (1 + rate) ** t
        prev = cum
        cum += disc
        if t > 0 and cum >= 0 > prev:
            return t - 1 + (-prev / disc if disc else 0.0)
    return None


def annual_battery_note(age: AgeingResult | None, chem: Chemistry | None) -> str:
    if not age or not chem:
        return "No battery"
    return (f"{chem.label}: about {age.equivalent_full_cycles_per_year:.0f} full cycles a year, "
            f"replace every {age.life_years:.1f} years (mainly {age.dominant_mechanism})")
