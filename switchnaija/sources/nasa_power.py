"""NASA POWER: free daily and hourly weather data for any point on Earth (no API key).

Docs: https://power.larc.nasa.gov/docs/services/api/
"""

from __future__ import annotations

import pandas as pd

from .cache import get_json

DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
HOURLY_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
FILL = -999.0


def _frame(payload: dict, fmt: str) -> pd.DataFrame:
    params = payload["properties"]["parameter"]
    df = pd.DataFrame(params)
    df.index = pd.to_datetime(df.index, format=fmt)
    return df.replace(FILL, float("nan")).sort_index()


def fetch_daily(lat: float, lon: float, start: str = "19810101", end: str = "20251231",
                parameters: tuple[str, ...] = ("PRECTOTCORR", "T2M_MAX")) -> pd.DataFrame:
    """Daily series (e.g. rainfall in mm/day as PRECTOTCORR) from 1981 onward."""
    payload = get_json(
        DAILY_URL,
        {
            "parameters": ",".join(parameters),
            "community": "AG",
            "longitude": round(lon, 4),
            "latitude": round(lat, 4),
            "start": start,
            "end": end,
            "format": "JSON",
        },
        timeout=180,
    )
    return _frame(payload, "%Y%m%d")


def fetch_hourly_solar(lat: float, lon: float, year: int = 2023) -> pd.DataFrame:
    """Hourly global horizontal irradiance (W/m2) and air temperature, local time.

    Used as a fallback when PVGIS is unavailable.
    """
    payload = get_json(
        HOURLY_URL,
        {
            "parameters": "ALLSKY_SFC_SW_DWN,T2M",
            "community": "RE",
            "longitude": round(lon, 4),
            "latitude": round(lat, 4),
            "start": f"{year}0101",
            "end": f"{year}1231",
            "format": "JSON",
            "time-standard": "LST",
        },
        timeout=180,
    )
    df = _frame(payload, "%Y%m%d%H")
    return df.rename(columns={"ALLSKY_SFC_SW_DWN": "ghi_wm2", "T2M": "temp_c"})


def simple_pv_from_ghi(ghi_wm2: pd.Series, temp_c: pd.Series, performance_ratio: float = 0.80,
                       temp_coeff_per_c: float = -0.004, noct_rise_c: float = 25.0) -> pd.Series:
    """Very simple PV model (kW per kWp) for the NASA fallback.

    Cell temperature is approximated as air temperature plus a rise proportional to
    irradiance (about 25 C at 800 W/m2).
    """
    cell_t = temp_c + noct_rise_c * ghi_wm2 / 800.0
    derate = 1.0 + temp_coeff_per_c * (cell_t - 25.0)
    return (ghi_wm2 / 1000.0) * performance_ratio * derate.clip(lower=0)
