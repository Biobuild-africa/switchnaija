import numpy as np
import pandas as pd
import pytest
from scipy import stats

from switchnaija.flood import (annual_extremes, classify, exposure_table, gev_fit, gev_nonstationary, mann_kendall,
                               rain_trend, return_level, sample_grid)
from switchnaija.flood.exposure import Facility


def test_mann_kendall_textbook_values():
    r = mann_kendall(np.arange(10.0))
    assert r["S"] == 45
    assert r["z"] == pytest.approx(44 / np.sqrt(125))     # var = n(n-1)(2n+5)/18 = 125
    assert r["sen_slope"] == pytest.approx(1.0)
    assert r["p"] < 0.001
    flat = mann_kendall(np.full(20, 5.0))
    assert flat["S"] == 0 and flat["p"] == pytest.approx(1.0)


def test_mann_kendall_tie_correction_lowers_variance():
    x = np.array([1, 1, 2, 2, 3, 3, 4, 4], float)
    r = mann_kendall(x)
    n = x.size
    var_no_ties = n * (n - 1) * (2 * n + 5) / 18
    assert abs(r["z"]) > (r["S"] - 1) / np.sqrt(var_no_ties)


def test_annual_extremes():
    idx = pd.date_range("2001-01-01", "2002-12-31", freq="D")
    s = pd.Series(1.0, index=idx)
    s["2001-06-10"] = 80.0
    s["2001-06-11"] = 30.0
    s["2002-07-01"] = 55.0
    e = annual_extremes(s)
    assert list(e.index) == [2001, 2002]
    assert e.loc[2001, "max_1day_mm"] == 80
    assert e.loc[2001, "max_3day_mm"] == pytest.approx(111)
    assert e.loc[2001, "heavy_days"] == 1 and e.loc[2002, "heavy_days"] == 1


def test_gev_fit_recovers_parameters():
    x = stats.genextreme.rvs(-0.1, loc=60, scale=15, size=3000, random_state=1)
    c, loc, scale = gev_fit(x)
    assert loc == pytest.approx(60, rel=0.03)
    assert scale == pytest.approx(15, rel=0.06)
    assert return_level(100, c, loc, scale) == pytest.approx(
        stats.genextreme.ppf(0.99, -0.1, loc=60, scale=15), rel=0.06)


def test_nonstationary_gev_detects_a_real_trend_and_not_a_fake_one():
    t = np.arange(45.0)
    trend = stats.genextreme.rvs(-0.1, loc=50 + 1.0 * t, scale=8, random_state=3)
    flat = stats.genextreme.rvs(-0.1, loc=50, scale=8, size=45, random_state=4)
    r1 = gev_nonstationary(trend, t)
    assert r1["mu1"] == pytest.approx(1.0, abs=0.3)
    assert r1["lr_p"] < 0.01
    assert gev_nonstationary(flat, t)["lr_p"] > 0.05


def test_rain_trend_end_to_end():
    rng = np.random.default_rng(7)
    idx = pd.date_range("1981-01-01", "2025-12-31", freq="D")
    base = rng.gamma(0.4, 12, idx.size)
    years = idx.year.to_numpy() - 1981
    storms = pd.Series(base, index=idx)
    for y in range(45):   # one storm per year that grows by 1.5 mm a year
        storms[f"{1981 + y}-07-15"] = 70 + 1.5 * y + rng.normal(0, 6)
    r = rain_trend(storms)
    assert r.trend_significant
    assert r.mk_1day["sen_slope"] == pytest.approx(1.5, abs=0.4)
    assert r.storm_now_mm > r.storm_then_mm
    assert r.then_storm_now_every_years < r.T
    assert len(years) == idx.size


def test_sample_grid_and_classify():
    arr = np.zeros((10, 10), np.float32)
    arr[5, 5] = 2.0
    arr[0, 0] = -9999.0
    left, top, res = 3.0, 7.0, 0.01        # cell (r, c) covers lon 3+c*0.01, lat 7-r*0.01
    lats = [7 - 5.5 * res, 7 - 5.5 * res, 7 - 0.5 * res, 7 - 8.5 * res]
    lons = [3 + 5.5 * res, 3 + 6.5 * res, 3 + 0.5 * res, 3 + 1.5 * res]
    at, near = sample_grid(arr, left, top, res, lats, lons, nodata=-9999.0)
    assert list(at) == [2.0, 0.0, 0.0, 0.0]
    assert list(near) == [2.0, 2.0, 0.0, 0.0]
    assert classify(1.0, 2.0, 2.0) == "High"
    assert classify(0.0, 2.0, 2.0) == "Medium"
    assert classify(0.0, 0.0, 2.0) == "Low"
    assert classify(0.0, 0.0, 0.0) == "None"


def test_exposure_table_orders_most_exposed_first():
    facs = [Facility("school", n, 6.0, 6.8, "X", "Y") for n in ("a", "b", "c", "d")]
    df = exposure_table(facs, [0, 0.5, 0, 0], [0, 1.0, 12.0, 0], [0, 1.0, 12.0, 0.3])
    assert list(df["name"]) == ["b", "c", "d", "a"]
    assert list(df["risk"].astype(str)) == ["High", "Medium", "Low", "None"]
    assert df.loc[df["name"] == "c", "note"].item().startswith("Depth over 10 m")
