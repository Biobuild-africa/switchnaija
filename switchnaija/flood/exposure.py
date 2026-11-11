"""Which schools and markets sit in mapped river-flood areas?

Facilities: GRID3 Nigeria schools (about 108,000) and markets (about 11,000), with exact coordinates
and LGA names, served as public ArcGIS feature layers.

Flood hazard: Copernicus Emergency Management Service (EU JRC) global river flood hazard maps,
version 2.1, ~90 m, water depth for floods with a 10-year and a 100-year return period. Tiles are
read over the internet window by window, so nothing large is downloaded.

Limits: these maps cover river (fluvial) floods only. Flash floods from blocked drains, and gully
erosion, are not mapped; the rainfall analysis in `rain.py` covers the heavy-rain side.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..sources.cache import get_json

ARCGIS = "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/ArcGIS/rest/services"
LAYERS = {
    "school": (f"{ARCGIS}/GRID3_Nigeria_Schools_with_LGA_Names/FeatureServer/45", "name", ("category", "management")),
    "market": (f"{ARCGIS}/GRID3_Nigeria_Markets_with_LGA_Names/FeatureServer/46", "market_nam", ("market_typ",)),
}
JRC = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard"
SPURIOUS_DEPTH_M = 10.0   # JRC README: depths above 10 m can be modelling artefacts

RISK_ORDER = ["High", "Medium", "Low", "None"]
RISK_TEXT = {
    "High": "Inside the 1-in-10-year river flood area",
    "Medium": "Inside the 1-in-100-year river flood area",
    "Low": "Within about 100 m of the 1-in-100-year flood area",
    "None": "Not in a mapped river flood area",
}


@dataclass
class Facility:
    kind: str
    name: str
    lat: float
    lon: float
    lga: str
    state: str
    detail: str = ""


def _quote(s: str) -> str:
    return s.replace("'", "''")


def states() -> list[str]:
    """State names as GRID3 spells them (the FCT is "Fct")."""
    url, _, _ = LAYERS["school"]
    d = get_json(f"{url}/query", {"where": "1=1", "returnDistinctValues": "true", "outFields": "state_name",
                                  "returnGeometry": "false", "f": "json"})
    return sorted({f["attributes"]["state_name"] for f in d["features"] if f["attributes"]["state_name"]})


def lgas(state: str) -> list[str]:
    url, _, _ = LAYERS["school"]
    d = get_json(f"{url}/query", {"where": f"state_name='{_quote(state)}'", "returnDistinctValues": "true",
                                  "outFields": "lga_name", "returnGeometry": "false", "f": "json"})
    return sorted({f["attributes"]["lga_name"] for f in d["features"] if f["attributes"]["lga_name"]})


def fetch_facilities(kind: str, state: str, lga: str, page: int = 2000) -> list[Facility]:
    """All GRID3 schools or markets in one LGA (coordinates from the point geometry, not the rounded columns)."""
    url, name_field, extra = LAYERS[kind]
    fields = ",".join((name_field,) + extra)
    out: list[Facility] = []
    offset = 0
    while True:
        d = get_json(f"{url}/query", {
            "where": f"state_name='{_quote(state)}' AND lga_name='{_quote(lga)}'", "outFields": fields,
            "returnGeometry": "true", "outSR": 4326, "resultOffset": offset, "resultRecordCount": page,
            "orderByFields": "FID", "f": "json"})
        feats = d.get("features", [])
        for f in feats:
            a, g = f["attributes"], f.get("geometry") or {}
            if "x" not in g:
                continue
            detail = ", ".join(str(a[k]) for k in extra if a.get(k))
            out.append(Facility(kind, (a.get(name_field) or "Unnamed").strip(), g["y"], g["x"], lga, state, detail))
        if len(feats) < page and not d.get("exceededTransferLimit"):
            break
        offset += page
    return out


def sample_grid(arr: np.ndarray, left: float, top: float, res: float, lats, lons,
                nodata: float | None = None, radius_px: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Water depth at each point, and the largest depth within `radius_px` cells (pure numpy)."""
    a = np.where((arr == nodata) if nodata is not None else np.zeros(arr.shape, bool), 0.0, arr).astype(float)
    a = np.where(np.isfinite(a) & (a > 0), a, 0.0)
    rows = np.floor((top - np.asarray(lats, float)) / res).astype(int)
    cols = np.floor((np.asarray(lons, float) - left) / res).astype(int)
    at = np.zeros(len(rows))
    near = np.zeros(len(rows))
    for i, (r, c) in enumerate(zip(rows, cols)):
        if 0 <= r < a.shape[0] and 0 <= c < a.shape[1]:
            at[i] = a[r, c]
            near[i] = a[max(r - radius_px, 0):r + radius_px + 1, max(c - radius_px, 0):c + radius_px + 1].max()
    return at, near


def _tiles() -> list[dict]:
    d = get_json(f"{JRC}/tile_extents.geojson")
    out = []
    for f in d["features"]:
        xs = [p[0] for p in f["geometry"]["coordinates"][0]]
        ys = [p[1] for p in f["geometry"]["coordinates"][0]]
        out.append({"id": f["properties"]["id"], "name": f["properties"]["name"],
                    "box": (min(xs), min(ys), max(xs), max(ys))})
    return out


def flood_depths(lats, lons, return_period: int) -> tuple[np.ndarray, np.ndarray]:
    """Sample the JRC flood depth map (metres) at each point. Needs `rasterio` (pip install rasterio)."""
    import rasterio
    from rasterio.windows import Window

    lats = np.asarray(lats, float)
    lons = np.asarray(lons, float)
    at = np.zeros(lats.size)
    near = np.zeros(lats.size)
    for t in _tiles():
        x0, y0, x1, y1 = t["box"]
        m = (lons >= x0) & (lons < x1) & (lats >= y0) & (lats < y1)
        if not m.any():
            continue
        rp = f"RP{return_period}"
        path = f"/vsicurl/{JRC}/{rp}/ID{t['id']}_{t['name']}_{rp}_depth.tif"
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(path) as src:
            r0, c0 = src.index(lons[m].min(), lats[m].max())
            r1, c1 = src.index(lons[m].max(), lats[m].min())
            r0, c0 = max(r0 - 2, 0), max(c0 - 2, 0)
            win = Window(c0, r0, min(c1 + 3, src.width) - c0, min(r1 + 3, src.height) - r0)
            arr = src.read(1, window=win)
            tr = src.window_transform(win)
            a, n = sample_grid(arr, tr.c, tr.f, tr.a, lats[m], lons[m], src.nodata)
        at[m], near[m] = a, n
    return at, near


def classify(d10_at: float, d100_at: float, d100_near: float) -> str:
    if d10_at > 0:
        return "High"
    if d100_at > 0:
        return "Medium"
    if d100_near > 0:
        return "Low"
    return "None"


def exposure_table(facilities: list[Facility], d10_at, d100_at, d100_near) -> pd.DataFrame:
    """One row per facility, most exposed first."""
    df = pd.DataFrame([f.__dict__ for f in facilities])
    if df.empty:
        return df
    df["depth_10yr_m"] = np.round(d10_at, 2)
    df["depth_100yr_m"] = np.round(d100_at, 2)
    df["risk"] = [classify(a, b, c) for a, b, c in zip(d10_at, d100_at, d100_near)]
    df["note"] = np.where(np.asarray(d100_at) > SPURIOUS_DEPTH_M, "Depth over 10 m: check on the ground", "")
    df["risk"] = pd.Categorical(df["risk"], RISK_ORDER, ordered=True)
    return df.sort_values(["risk", "depth_100yr_m"], ascending=[True, False]).reset_index(drop=True)


def assess(state: str, lga: str, kinds: tuple[str, ...] = ("school", "market")) -> pd.DataFrame:
    """Fetch facilities for an LGA and rate their river-flood exposure."""
    facs = [f for k in kinds for f in fetch_facilities(k, state, lga)]
    if not facs:
        return pd.DataFrame()
    lats = [f.lat for f in facs]
    lons = [f.lon for f in facs]
    d10, _ = flood_depths(lats, lons, 10)
    d100, near = flood_depths(lats, lons, 100)
    return exposure_table(facs, d10, d100, near)
