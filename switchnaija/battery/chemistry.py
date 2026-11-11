"""Battery chemistry parameters, read from defaults.yaml."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import load_defaults

# NMC is kept for completeness but excluded by default: not commonly sold in Nigeria and
# its parameters are not datasheet-sourced (see defaults.yaml).
CHEMISTRIES = ("lead_acid", "lfp")
ALL_CHEMISTRIES = ("lead_acid", "lfp", "nmc")


@dataclass(frozen=True)
class Chemistry:
    key: str
    label: str
    price_ngn_per_kwh: float
    round_trip_efficiency: float
    max_dod: float
    cycles_at_ref: float
    ref_dod: float
    dod_exponent: float
    calendar_life_years_25c: float
    temp_doubling_c: float
    recyclable_fraction: float
    hazard: str
    kg_per_kwh: float = 0.0        # battery mass per kWh of nominal capacity
    lead_fraction: float = 0.0     # share of battery mass that is lead

    @property
    def charge_efficiency(self) -> float:
        """One-way efficiency, assuming losses split evenly between charge and discharge."""
        return self.round_trip_efficiency ** 0.5

    def cycles_to_eol(self, dod: float) -> float:
        """Full cycles to end of life when cycled repeatedly at depth `dod` (0 to 1)."""
        dod = max(float(dod), 1e-6)
        return self.cycles_at_ref * (self.ref_dod / dod) ** self.dod_exponent

    def calendar_life_years(self, temp_c: float) -> float:
        """Shelf life to end of life at a constant temperature (faster ageing when hot)."""
        accel = 2.0 ** (max(temp_c - 25.0, 0.0) / self.temp_doubling_c)
        return self.calendar_life_years_25c / accel


def get_chemistry(key: str, defaults: dict | None = None) -> Chemistry:
    cfg = (defaults or load_defaults())["battery"][key]
    return Chemistry(key=key, **cfg)
