import numpy as np
import pytest

from switchnaija.battery import ROOMS, BatteryUse, calendar_damage_per_year, compare, get_chemistry, room_sensitivity
from switchnaija.battery.lifecycle import soc_series


def test_soc_series_shape_and_depth():
    s = soc_series(0.5, 7)
    assert s.size == 8760
    assert s.min() == pytest.approx(0.5)
    assert s.max() == pytest.approx(1.0)
    # 3 days a week: the other days stay full
    assert (soc_series(0.5, 3).reshape(365, 24).min(axis=1) == 1.0).sum() == pytest.approx(365 * 4 / 7, abs=1)


def test_hot_afternoons_age_faster_than_the_mean_suggests():
    chem = get_chemistry("lead_acid")
    temps = np.array([25.0, 35.0])
    assert calendar_damage_per_year(chem, temps) > calendar_damage_per_year(chem, temps.mean())


def test_same_usable_energy_and_lead_acid_needs_bigger_bank(ede_weather):
    r = compare(BatteryUse(daily_kwh=2.0), ede_weather["temp_c"].to_numpy())
    la, lfp = r["lead_acid"], r["lfp"]
    for x in (la, lfp):
        chem = get_chemistry(x.chemistry)
        assert x.capacity_kwh * x.cycle_depth * chem.charge_efficiency == pytest.approx(2.0)
    assert la.capacity_kwh > 1.8 * lfp.capacity_kwh


def test_lfp_lasts_longer_costs_less_per_kwh_and_leaves_less_waste(ede_weather):
    r = compare(BatteryUse(daily_kwh=2.0), ede_weather["temp_c"].to_numpy())
    la, lfp = r["lead_acid"], r["lfp"]
    assert lfp.life_years > 2 * la.life_years
    assert lfp.cost_per_kwh_ngn < la.cost_per_kwh_ngn
    assert lfp.waste_kg < la.waste_kg / 5
    assert la.lead_kg == pytest.approx(0.55 * la.waste_kg)
    assert lfp.lead_kg == 0


def test_hotter_rooms_shorten_life(ede_weather):
    df = room_sensitivity(BatteryUse(daily_kwh=2.0), ede_weather["temp_c"].to_numpy())
    for chem, g in df.groupby("chemistry"):
        g = g.set_index("room").loc[list(ROOMS)]
        assert g["mean_temp_c"].is_monotonic_increasing
        assert g["life_years"].is_monotonic_decreasing


def test_oversizing_lead_acid_means_shallower_cycles_and_longer_life(ede_weather):
    t = ede_weather["temp_c"].to_numpy()
    small = compare(BatteryUse(2.0, oversize=1.0), t, chemistries=("lead_acid",))["lead_acid"]
    big = compare(BatteryUse(2.0, oversize=1.5), t, chemistries=("lead_acid",))["lead_acid"]
    assert big.cycle_depth < small.cycle_depth
    assert big.life_years > small.life_years


def test_replacements_follow_life(ede_weather):
    r = compare(BatteryUse(2.0), ede_weather["temp_c"].to_numpy())["lead_acid"]
    assert r.batteries_bought == 1 + len(r.replacement_years)
    assert r.replacement_years[0] == int(np.ceil(r.life_years))
    assert len(r.cumulative_cost_ngn) == 11
