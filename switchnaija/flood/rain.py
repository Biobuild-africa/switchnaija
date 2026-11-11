"""Is heavy rain getting heavier? Annual rainfall extremes, trend tests and return levels.

Methods
-------
* Annual maxima of 1-day and 3-day rainfall, and the number of days with at least 50 mm.
* Mann-Kendall trend test (with tie correction) and Sen's slope: is there a monotonic trend?
* Generalised extreme value (GEV) distribution fitted to annual maxima by maximum likelihood,
  first stationary, then with a location parameter that changes linearly with time. A likelihood
  ratio test says whether the time-varying model is a significantly better fit, and the fitted
  model gives the size of the "1-in-N-year" storm at the start and at the end of the record.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import optimize, stats

HEAVY_MM = 50.0


def annual_extremes(daily_mm: pd.Series, heavy_mm: float = HEAVY_MM, min_days: int = 330) -> pd.DataFrame:
    """Per year: wettest day, wettest 3 days, days with at least `heavy_mm`, and total rain."""
    s = daily_mm.astype(float).dropna()
    three = s.rolling(3).sum()
    g = s.groupby(s.index.year)
    out = pd.DataFrame({
        "max_1day_mm": g.max(),
        "max_3day_mm": three.groupby(three.index.year).max(),
        "heavy_days": g.apply(lambda x: int((x >= heavy_mm).sum())),
        "total_mm": g.sum(),
        "n_days": g.size(),
    })
    out = out[out["n_days"] >= min_days].drop(columns="n_days")
    out.index.name = "year"
    return out


def mann_kendall(x: np.ndarray) -> dict[str, float]:
    """Two-sided Mann-Kendall trend test with tie correction, plus Sen's slope (units per step)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = x.size
    diff = x[None, :] - x[:, None]
    s = float(np.sign(diff[np.triu_indices(n, 1)]).sum())
    _, counts = np.unique(x, return_counts=True)
    var = (n * (n - 1) * (2 * n + 5) - np.sum(counts * (counts - 1) * (2 * counts + 5))) / 18.0
    if s > 0:
        z = (s - 1) / np.sqrt(var)
    elif s < 0:
        z = (s + 1) / np.sqrt(var)
    else:
        z = 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    i, j = np.triu_indices(n, 1)
    slope = float(np.median((x[j] - x[i]) / (j - i)))
    return {"S": s, "z": float(z), "p": float(p), "sen_slope": slope, "n": n}


def gev_fit(x: np.ndarray) -> tuple[float, float, float]:
    """Stationary GEV fit (scipy shape convention c = -xi). Returns (c, loc, scale)."""
    return tuple(float(v) for v in stats.genextreme.fit(np.asarray(x, dtype=float)))


def return_level(T: float, c: float, loc: float, scale: float) -> float:
    """Rainfall expected to be exceeded on average once every T years."""
    return float(stats.genextreme.ppf(1 - 1 / T, c, loc=loc, scale=scale))


def gev_nonstationary(x: np.ndarray, t: np.ndarray) -> dict[str, float]:
    """GEV with location = mu0 + mu1 * t (t in years from the start), fitted by maximum likelihood.

    Returns the parameters, both log-likelihoods and the likelihood-ratio test p-value.
    """
    x = np.asarray(x, dtype=float)
    t = np.asarray(t, dtype=float)
    c0, loc0, sc0 = gev_fit(x)
    ll0 = float(np.sum(stats.genextreme.logpdf(x, c0, loc=loc0, scale=sc0)))

    def nll(p):
        mu0, mu1, log_sc, c = p
        if abs(c) > 0.5:  # keep the shape physically reasonable
            return 1e10
        ll = stats.genextreme.logpdf(x, c, loc=mu0 + mu1 * t, scale=np.exp(log_sc))
        return 1e10 if not np.all(np.isfinite(ll)) else -float(np.sum(ll))

    best = None
    for start in ([loc0, 0.0, np.log(sc0), c0], [loc0, 0.0, np.log(sc0), 0.0]):
        r = optimize.minimize(nll, start, method="Nelder-Mead", options={"maxiter": 4000, "xatol": 1e-6, "fatol": 1e-8})
        if best is None or r.fun < best.fun:
            best = r
    mu0, mu1, log_sc, c = best.x
    ll1 = -float(best.fun)
    lr = max(2 * (ll1 - ll0), 0.0)
    return {"mu0": float(mu0), "mu1": float(mu1), "scale": float(np.exp(log_sc)), "c": float(c),
            "loglik_stationary": ll0, "loglik_trend": ll1, "lr_p": float(1 - stats.chi2.cdf(lr, 1))}


@dataclass
class RainTrend:
    years: list[int]
    extremes: pd.DataFrame
    mk_1day: dict[str, float]
    mk_heavy_days: dict[str, float]
    gev: tuple[float, float, float]
    gev_trend: dict[str, float]
    storm_then_mm: float          # 1-in-T-year 1-day rain at the start of the record (trend model)
    storm_now_mm: float           # same, at the end of the record
    then_storm_now_every_years: float  # how often the old 1-in-T storm happens now
    T: int

    @property
    def trend_significant(self) -> bool:
        return self.mk_1day["p"] < 0.05 or self.gev_trend["lr_p"] < 0.05

    @property
    def storm_today_mm(self) -> float:
        """1-in-T-year one-day rain today: from the trend model if the trend is significant, else the fixed model."""
        return self.storm_now_mm if self.trend_significant else return_level(self.T, *self.gev)


def rain_trend(daily_mm: pd.Series, T: int = 25) -> RainTrend:
    """Full heavy-rain analysis for one location."""
    ext = annual_extremes(daily_mm)
    x = ext["max_1day_mm"].to_numpy()
    yrs = ext.index.to_numpy()
    t = yrs - yrs[0]
    gev = gev_fit(x)
    tr = gev_nonstationary(x, t)
    loc_then, loc_now = tr["mu0"], tr["mu0"] + tr["mu1"] * t[-1]
    then = return_level(T, tr["c"], loc_then, tr["scale"])
    now = return_level(T, tr["c"], loc_now, tr["scale"])
    p_now = stats.genextreme.sf(then, tr["c"], loc=loc_now, scale=tr["scale"])
    every = float(1 / p_now) if p_now > 0 else float("inf")
    return RainTrend(list(map(int, yrs)), ext, mann_kendall(x), mann_kendall(ext["heavy_days"].to_numpy()),
                     gev, tr, then, now, every, T)
