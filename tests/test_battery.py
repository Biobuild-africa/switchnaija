import numpy as np
import pytest

from switchnaija.battery import estimate_life, get_chemistry, rainflow, turning_points


def test_turning_points_keeps_peaks_and_valleys():
    assert list(turning_points([0, 1, 2, 1, 0, 0.5, 1])) == [0, 2, 0, 1]


def test_rainflow_astm_example():
    # ASTM E1049-85 worked example (Fig. 6): -2, 1, -3, 5, -1, 3, -4, 4, -2
    cycles = rainflow([-2, 1, -3, 5, -1, 3, -4, 4, -2])
    counts: dict[float, float] = {}
    for r, c in cycles:
        counts[r] = counts.get(r, 0) + c
    assert counts == {3.0: 0.5, 4.0: 1.5, 6.0: 0.5, 8.0: 1.0, 9.0: 0.5}


def test_rainflow_full_cycles_of_a_sine():
    soc = 0.5 + 0.4 * np.sin(np.linspace(0, 2 * np.pi * 10, 1000))
    total = sum(c for r, c in rainflow(soc) if r > 0.79)
    assert total == pytest.approx(10, abs=1)


def test_deeper_cycles_shorten_life():
    chem = get_chemistry("lead_acid")
    assert chem.cycles_to_eol(0.8) < chem.cycles_to_eol(0.5) < chem.cycles_to_eol(0.2)


def test_heat_shortens_calendar_life():
    chem = get_chemistry("lead_acid")
    assert chem.calendar_life_years(35) == pytest.approx(chem.calendar_life_years(25) / 2)


def test_lfp_outlives_lead_acid_on_same_daily_cycle():
    day = np.concatenate([np.linspace(1, 0.5, 12), np.linspace(0.5, 1, 12)])
    soc = np.tile(day, 365)
    la = estimate_life(soc, get_chemistry("lead_acid"), 30)
    lfp = estimate_life(soc, get_chemistry("lfp"), 30)
    assert la.equivalent_full_cycles_per_year == pytest.approx(182.5, rel=0.02)
    assert lfp.life_years > 2 * la.life_years
