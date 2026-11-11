import numpy as np
import pytest

from switchnaija.battery import get_chemistry
from switchnaija.config import towns
from switchnaija.energy import PRESETS, Generator, Site, outage_schedule, plan, sensitivity, simulate
from switchnaija.energy.economics import Cashflow, Capex, npv, payback_years
from switchnaija.energy.load import Appliance, LoadProfile


def test_all_states_and_fct_present():
    states = {t["state"] for t in towns() if t["capital"]}
    assert len(states) == 37


@pytest.mark.parametrize("hours", [0, 4, 8, 12, 16, 20, 24])
def test_outage_hours_match_band(hours):
    off = outage_schedule(hours, n_days=60, seed=1)
    per_day = off.reshape(60, 24).sum(axis=1)
    assert (per_day == 24 - hours).all()


def test_wrapping_window_and_daily_energy():
    a = Appliance("fan", 100, 1, 8, 22, 6)
    assert sorted(a.window_hours()) == [0, 1, 2, 3, 4, 5, 22, 23]
    assert a.daily_profile_kw().sum() == pytest.approx(0.8)
    lp = PRESETS["Small home"]
    assert lp.daily_kwh() == pytest.approx(sum(x.daily_kwh() for x in lp.appliances))


def test_generator_fuel_curve():
    g = Generator(2.5, "diesel")
    lit = g.fuel_litres(np.array([0.0, 1.0]))
    assert lit[0] == 0
    assert lit[1] == pytest.approx(0.08145 * 2.0 + 0.246 * 1.0)


def test_petrol_curve_matches_firman_spg3000_datasheet():
    # Sumec Firman SPG3000 (2.5 kVA): 15 L tank lasts about 14 h at 50% load = 1.07 L/h
    g = Generator(2.5, "petrol")
    assert g.rated_kw == pytest.approx(2.5)
    assert g.fuel_litres(np.array([1.25]))[0] == pytest.approx(1.07, rel=0.10)


def test_dispatch_energy_balance(ede_weather):
    n = len(ede_weather)
    load = PRESETS["Small home"].hourly_kw(n)
    off = outage_schedule(12, n_days=n // 24)[:n]
    res = simulate(load, off, ede_weather["pv_kw_per_kwp"].to_numpy() * 1.0, 3.0,
                   get_chemistry("lfp"), 1.0, Generator(), grid_charging=True)
    assert res.energy_balance_error() < 1e-9
    assert res.soc.min() >= 1 - get_chemistry("lfp").max_dod - 1e-9
    assert res.soc.max() <= 1 + 1e-9
    assert (res.grid_import_kw[off] == 0).all()
    assert (res.gen_kw[~off] == 0).all()


def test_no_generator_means_unmet_load():
    load = np.full(48, 0.5)
    off = np.ones(48, dtype=bool)
    res = simulate(load, off, np.zeros(48), 0.0, None, 0.0, None)
    assert res.unmet_kw.sum() == pytest.approx(24.0)


def test_npv_and_payback():
    assert npv([-100, 110], 0.10) == pytest.approx(0.0)
    cf = Cashflow([0, 1, 2, 3], [0, 50, 50, 50], [100, 0, 0, 0], Capex(pv_ngn=100))
    assert payback_years(cf) == pytest.approx(2.0)


def test_plan_on_real_ede_data(ede_weather):
    site = Site.from_town("Ede", band="C", weather=ede_weather)
    r = plan(site, pv_multipliers=(0.75, 1.0, 1.5), batt_multipliers=(0.5, 1.0))
    base = r.baseline.operation
    assert base.generator_hours == pytest.approx(12 * 365, rel=0.01)
    assert r.best.npv_ngn < r.baseline.npv_ngn
    assert r.best.operation.fuel_litres < base.fuel_litres
    assert r.co2_saved_t_per_year > 0
    best = r.best_per_chemistry()
    # lead-acid wears out faster than LFP in a hot battery room
    assert best["lead_acid"].ageing.life_years < best["lfp"].ageing.life_years
    s = sensitivity(r)
    assert s["payback_years"].is_monotonic_decreasing


def test_solar_yield_is_realistic(ede_weather):
    # Southwest Nigeria: roughly 1,300 to 1,600 kWh per kWp per year
    assert 1300 < ede_weather["pv_kw_per_kwp"].sum() < 1600


def test_evening_only_generator_leaves_other_outages_dark(ede_weather):
    all_hours = plan(Site.from_town("Ede", band="C", weather=ede_weather),
                     pv_multipliers=(1.0,), batt_multipliers=(1.0,))
    evenings = plan(Site.from_town("Ede", band="C", weather=ede_weather, gen_hours=(18, 24)),
                    pv_multipliers=(1.0,), batt_multipliers=(1.0,))
    assert evenings.baseline.operation.fuel_litres < all_hours.baseline.operation.fuel_litres
    assert evenings.baseline.operation.dark_hours > 0
    # solar + battery gives the evening-only household many more hours of power
    assert evenings.best.operation.dark_hours < evenings.baseline.operation.dark_hours
