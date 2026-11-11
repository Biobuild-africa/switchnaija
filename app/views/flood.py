"""FloodSafe: which schools and markets are most exposed to flooding, and is heavy rain getting heavier?"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from switchnaija.flood.exposure import RISK_ORDER, RISK_TEXT, assess, lgas, states
from switchnaija.flood.rain import rain_trend
from switchnaija.sources.nasa_power import fetch_daily

FONT = dict(family="DM Sans, sans-serif", color=ui.MUTED)
RISK_COLORS = {"High": "#B42318", "Medium": ui.ORANGE, "Low": "#E9C46A", "None": "#9AA5B1"}


@st.cache_data(show_spinner="Loading states...")
def state_list() -> list[str]:
    return states()


@st.cache_data(show_spinner="Loading local government areas...")
def lga_list(state: str) -> list[str]:
    return lgas(state)


@st.cache_data(show_spinner="Checking every school and market against EU flood maps...")
def exposure(state: str, lga: str) -> pd.DataFrame:
    return assess(state, lga)


@st.cache_data(show_spinner="Fetching daily rainfall since 1981 from NASA POWER...")
def rainfall(lat: float, lon: float) -> pd.Series:
    return fetch_daily(lat, lon, start="19810101", end="20251231", parameters=("PRECTOTCORR",))["PRECTOTCORR"]


def style(fig: go.Figure, h: int) -> go.Figure:
    fig.update_layout(height=h, font=FONT, plot_bgcolor="#fff", paper_bgcolor="#fff",
                      margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.2))
    fig.update_xaxes(gridcolor="#EEF1EE")
    fig.update_yaxes(gridcolor="#EEF1EE")
    return fig


ui.nav("flood")
ui.hero(
    "03 / FloodSafe",
    "Which Schools and Markets Are Most Exposed to Flooding?",
    "Pick a local government area. We check every school and market on the national GRID3 register against "
    "European Union flood maps, then look at 45 years of daily rainfall to see whether the heaviest storms are "
    "getting heavier.",
)
st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

ui.section("Choose an Area", "STEP 1 OF 1")
c1, c2, _ = st.columns([1, 1, 1], gap="medium")
all_states = state_list()
state = c1.selectbox("State", all_states, index=all_states.index("Anambra"),
                     format_func=lambda s: "FCT" if s == "Fct" else s)
options = lga_list(state)
default = options.index("Ogbaru") if "Ogbaru" in options else 0
lga = c2.selectbox("Local government area", options, index=default)
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
if not st.button("Check Flood Risk"):
    ui.footer()
    st.stop()

df = exposure(state, lga)
st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
ui.section("Flood Exposure", f"{lga.upper()}, {state.upper()}")
if df.empty:
    st.info("No GRID3 schools or markets were found for this area.")
else:
    counts = df.groupby(["kind", "risk"], observed=False).size().unstack(fill_value=0)
    n_s = int(counts.loc["school"].sum()) if "school" in counts.index else 0
    n_m = int(counts.loc["market"].sum()) if "market" in counts.index else 0
    exposed = df[df["risk"].isin(["High", "Medium"])]
    hi = int((df["risk"] == "High").sum())
    k = st.columns(4, gap="small")
    k[0].markdown(ui.kpi(f"{n_s}", "schools checked"), unsafe_allow_html=True)
    k[1].markdown(ui.kpi(f"{n_m}", "markets checked"), unsafe_allow_html=True)
    k[2].markdown(ui.kpi(f"{hi}", "in the 1-in-10-year flood area"), unsafe_allow_html=True)
    k[3].markdown(ui.kpi(f"{len(exposed)}", "in the 1-in-100-year flood area"), unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    if len(exposed):
        top = exposed.iloc[0]
        st.markdown(
            f"""<div class="bb-reco"><b>{len(exposed)} of {len(df)}</b> schools and markets in {lga} sit inside a mapped
            river flood area. The most exposed is <b>{top['name']}</b> ({top['kind']}), where a 1-in-100-year flood
            reaches about <b>{top['depth_100yr_m']:.1f} m</b>.</div>""", unsafe_allow_html=True)
    else:
        st.markdown(
            f"""<div class="bb-reco">None of the {len(df)} schools and markets in {lga} sit inside a mapped river
            flood area. That does not mean they are safe: these maps cover river floods only, not flash floods from
            heavy rain or gully erosion. See the rainfall trend below.</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    fig = go.Figure()
    for risk in reversed(RISK_ORDER):
        g = df[df["risk"] == risk]
        if g.empty:
            continue
        fig.add_trace(go.Scattermap(
            lat=g["lat"], lon=g["lon"], mode="markers", name=RISK_TEXT[risk],
            marker=dict(size=np.where(g["kind"] == "market", 12, 9), color=RISK_COLORS[risk]),
            text=g["name"] + " (" + g["kind"] + ")<br>100-year flood depth: " + g["depth_100yr_m"].astype(str) + " m",
            hoverinfo="text"))
    fig.update_layout(map=dict(style="open-street-map", center=dict(lat=float(df["lat"].mean()),
                                                                   lon=float(df["lon"].mean())), zoom=10.5))
    st.plotly_chart(style(fig, 520), use_container_width=True)

    show = df[df["risk"] != "None"][["risk", "kind", "name", "detail", "depth_10yr_m", "depth_100yr_m", "note"]]
    show.columns = ["Risk", "Type", "Name", "Details", "Depth, 1-in-10-year flood (m)",
                    "Depth, 1-in-100-year flood (m)", "Note"]
    if len(show):
        st.markdown("**Schools and markets in or near a flood area**")
        st.dataframe(show, hide_index=True, use_container_width=True)
    st.download_button("Download the Full List (CSV)", df.to_csv(index=False).encode(),
                       file_name=f"floodsafe_{state}_{lga}.csv".replace(" ", "_"), mime="text/csv")

# ---------------- Rainfall ----------------
lat0 = float(df["lat"].mean()) if not df.empty else 9.06
lon0 = float(df["lon"].mean()) if not df.empty else 7.49
r = rain_trend(rainfall(round(lat0, 3), round(lon0, 3)))
e = r.extremes
st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)
ui.section("Is Heavy Rain Getting Heavier?", f"{r.years[0]} TO {r.years[-1]}")
slope10 = 10 * r.mk_1day["sen_slope"]
if r.trend_significant and slope10 > 0:
    verdict = (f"<b>Yes.</b> The wettest day of each year has been getting wetter, by about <b>{slope10:.1f} mm per "
               f"decade</b>. A storm that came once every {r.T} years around {r.years[0]} now comes about once every "
               f"<b>{r.then_storm_now_every_years:.0f} years</b>.")
elif r.trend_significant and slope10 < 0:
    verdict = f"The wettest day of each year has been getting slightly drier here, by about {abs(slope10):.1f} mm per decade."
else:
    verdict = (f"<b>No clear trend.</b> The wettest day of each year averages about {e['max_1day_mm'].mean():.0f} mm and "
               f"has not changed in a statistically clear way since {r.years[0]} (Mann-Kendall p = {r.mk_1day['p']:.2f}). "
               f"Storms are still heavy: the biggest day on record dropped {e['max_1day_mm'].max():.0f} mm in "
               f"{int(e['max_1day_mm'].idxmax())}.")
st.markdown(f'<div class="bb-reco">{verdict}</div>', unsafe_allow_html=True)
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

yrs = np.array(r.years)
fig = go.Figure()
fig.add_trace(go.Bar(x=yrs, y=e["max_1day_mm"], name="Wettest day of the year", marker_color=ui.GREEN))
mid = np.median(yrs)
fig.add_trace(go.Scatter(x=yrs, y=np.median(e["max_1day_mm"]) + r.mk_1day["sen_slope"] * (yrs - mid),
                         name="Trend (Sen's slope)", line=dict(color=ui.ORANGE, width=3)))
fig.update_layout(yaxis_title="Rain in one day (mm)", bargap=0.15)
st.plotly_chart(style(fig, 360), use_container_width=True)

k = st.columns(3, gap="small")
k[0].markdown(ui.kpi(f"{e['max_1day_mm'].mean():.0f} mm", "average wettest day of the year"), unsafe_allow_html=True)
k[1].markdown(ui.kpi(f"{r.storm_today_mm:.0f} mm", f"in one day: the 1-in-{r.T}-year storm today"), unsafe_allow_html=True)
k[2].markdown(ui.kpi(f"{e['heavy_days'].mean():.1f}", "days a year with 50 mm or more"), unsafe_allow_html=True)

with st.expander("Data, methods and limits"):
    st.markdown(f"""
- **Schools and markets:** GRID3 Nigeria (schools and markets with LGA names), public ArcGIS layers. Collected around
  2018 to 2019, so some new or renamed facilities may be missing.
- **Flood maps:** Copernicus Emergency Management Service global river flood hazard maps (EU Joint Research Centre,
  v2.1, about 90 m). Water depth for floods expected once in 10 and once in 100 years. River floods only: flash floods
  from blocked drains and gully erosion are not mapped. Depths over 10 m can be modelling artefacts and are flagged.
- **Risk levels:** High = inside the 1-in-10-year flood area; Medium = inside the 1-in-100-year area; Low = within about
  100 m (one map cell) of it.
- **Rainfall:** NASA POWER daily corrected precipitation, {r.years[0]} to {r.years[-1]}, on a grid of roughly 50 km, so it
  describes the wider area, not one street.
- **Trend tests:** Mann-Kendall test and Sen's slope on the wettest day of each year; a generalised extreme value (GEV)
  model whose centre can shift over time, tested against a fixed model (likelihood ratio p = {r.gev_trend['lr_p']:.3f}).
  Forty-five years is short for extremes, so treat return periods as rough.
""")
ui.footer()
