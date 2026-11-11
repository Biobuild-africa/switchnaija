"""PVGIS (EU Joint Research Centre): hourly solar PV output for any location.

API docs: https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en

We request the hourly output of a 1 kWp system at the optimal tilt and azimuth,
with 14% system losses, then scale it to any system size.
"""

from __future__ import annotations

import pandas as pd

from .cache import get_json

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"
NIGERIA_UTC_OFFSET_H = 1  # West Africa Time, no daylight saving


def parse_seriescalc(payload: dict) -> pd.DataFrame:
    """Turn a PVGIS seriescalc JSON payload into an hourly DataFrame in local time.

    Columns: pv_kw_per_kwp (kW per kWp installed), temp_c (2 m air temperature),
    poa_wm2 (irradiance on the panel plane).
    """
    rows = payload["outputs"]["hourly"]
    df = pd.DataFrame(rows)
    ts = pd.to_datetime(df["time"], format="%Y%m%d:%H%M")
    # PVGIS timestamps are UTC with a minute offset (e.g. 12:06). Round to the hour
    # and shift to West Africa Time.
    ts = ts.dt.floor("h") + pd.Timedelta(hours=NIGERIA_UTC_OFFSET_H)
    out = pd.DataFrame(
        {
            "pv_kw_per_kwp": df["P"].to_numpy() / 1000.0,
            "temp_c": df["T2m"].to_numpy(),
            "poa_wm2": df["G(i)"].to_numpy(),
        },
        index=pd.DatetimeIndex(ts, name="time_wat"),
    )
    return out


def fetch_pv_hourly(lat: float, lon: float, year: int = 2023, loss_pct: float = 14.0) -> pd.DataFrame:
    """Hourly PV output of a 1 kWp system (kW) and air temperature for one year."""
    params = {
        "lat": round(lat, 4),
        "lon": round(lon, 4),
        "outputformat": "json",
        "startyear": year,
        "endyear": year,
        "pvcalculation": 1,
        "peakpower": 1,
        "loss": loss_pct,
        "optimalangles": 1,
    }
    payload = get_json(PVGIS_URL, params)
    return parse_seriescalc(payload)
