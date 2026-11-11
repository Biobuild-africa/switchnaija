"""Energy Planner: generator to solar + battery."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from switchnaija.battery.chemistry import get_chemistry
from switchnaija.config import load_defaults, towns
from switchnaija.energy import PRESETS, Generator, Site, calibrate_generator, plan, sensitivity
from switchnaija.energy.load import Appliance, LoadProfile
from switchnaija.report import impact_card
from switchnaija.sources.pvgis import fetch_pv_hourly

D = load_defaults()
FONT = dict(family="DM Sans, sans-serif", color=ui.MUTED)


@st.cache_data(show_spinner="Fetching hourly solar data for your location from PVGIS...")
def weather(lat: float, lon: float) -> pd.DataFrame:
    return fetch_pv_hourly(lat, lon)


def naira(x: float) -> str:
    return f"₦{x:,.0f}"


def style(fig: go.Figure, h: int) -> go.Figure:
    fig.update_layout(height=h, font=FONT, plot_bgcolor="#fff", paper_bgcolor="#fff",
                      margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.15))
    fig.update_xaxes(gridcolor="#EEF1EE")
    fig.update_yaxes(gridcolor="#EEF1EE")
    return fig


ui.nav("energy")
ui.hero(
    "01 / Energy Planner",
    "Switch From Generator to Solar, With Your Own Numbers",
    "Tell us where you are, your electricity band and what you power. We pull real hourly solar data for "
    "your exact location and test 72 solar and battery combinations to find the cheapest "
    "one over ten years.",
)
st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

# ---------------- Inputs ----------------
ui.section("Tell Us About Your Place", "STEP 1 OF 2")
c1, c2, c3 = st.columns(3, gap="medium")
with c1.container(border=True):
    st.markdown("#### Location")
    T = towns()
    states = sorted({t["state"] for t in T})
    state = st.selectbox("State", states, index=states.index("Osun"))
    options = [t for t in T if t["state"] == state]
    town = st.selectbox("Town", [t["town"] for t in options])
    t = next(x for x in options if x["town"] == town)
    custom = st.toggle("Use my own coordinates")
    lat = st.number_input("Latitude", value=float(t["lat"]), format="%.4f", disabled=not custom)
    lon = st.number_input("Longitude", value=float(t["lon"]), format="%.4f", disabled=not custom)
with c2.container(border=True):
    st.markdown("#### Electricity")
    bands = list(D["grid"]["band_hours"].keys())
    band = st.selectbox("NERC tariff band (printed on your bill)", bands, index=2)
    st.caption(f"Band {band}: about {D['grid']['band_hours'][band]} hours of grid supply a day "
               f"(NERC minimum). 'No grid' means fully off-grid.")
    target = st.slider("Minimum share of outage hours covered by solar", 0, 100, 0, 5,
                       help="0 gives the cheapest option; the generator stays as backup.") / 100
with c3.container(border=True):
    st.markdown("#### Generator today")
    fuel = st.radio("Fuel", ["petrol", "diesel"], horizontal=True)
    kva = st.number_input("Generator size (kVA)", 0.8, 50.0, 2.5, 0.5)
    when = st.selectbox("When do you run it?", ["Evenings only (6pm to midnight)", "Whenever the grid is off",
                                                "My own hours"])
    if when == "My own hours":
        h1, h2 = st.columns(2)
        gs = h1.number_input("From (hour)", 0, 23, 18)
        ge = h2.number_input("To (hour)", 1, 24, 24)
        gen_hours = (int(gs), int(ge))
    else:
        gen_hours = (18, 24) if when.startswith("Evenings") else None
    fdef = D["fuel"][fuel]
    fuel_price = st.number_input(f"{fuel.title()} price you pay (₦/litre)", 100.0, 10000.0,
                                 float(fdef["price_ngn_per_litre"]), 10.0, help=f"Default: {fdef['source']}.")
    know_fuel = st.toggle("I know how many litres I buy per day")
    litres_day = st.number_input("Litres per day", 0.5, 100.0, 4.0, 0.5, disabled=not know_fuel)

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
ui.section("What Do You Power?", "STEP 2 OF 2")
preset = st.radio("Start from a typical profile, then edit", list(PRESETS.keys()), horizontal=True)
edited = st.data_editor(
    pd.DataFrame([a.__dict__ for a in PRESETS[preset].appliances]), num_rows="dynamic", use_container_width=True,
    column_config={
        "name": "Appliance",
        "watts": st.column_config.NumberColumn("Watts", min_value=1),
        "quantity": st.column_config.NumberColumn("Qty", min_value=1),
        "hours_per_day": st.column_config.NumberColumn("Hours/day", min_value=0, max_value=24),
        "start_hour": st.column_config.NumberColumn("From (hour)", min_value=0, max_value=23),
        "end_hour": st.column_config.NumberColumn("To (hour)", min_value=0, max_value=24),
        "duty": st.column_config.NumberColumn("Duty", min_value=0.05, max_value=1.0,
                                              help="Fridges and freezers switch on and off: about 0.4"),
    })
apps = [Appliance(name=str(r["name"]), watts=float(r["watts"]), quantity=int(r["quantity"]),
                  hours_per_day=float(r["hours_per_day"]), start_hour=int(r["start_hour"]),
                  end_hour=int(r["end_hour"]), duty=float(r["duty"]))
        for r in edited.dropna().to_dict("records")]
load = LoadProfile("Custom", apps)
k1, k2, _ = st.columns([1, 1, 2])
k1.markdown(ui.kpi(f"{load.daily_kwh():.1f} kWh", "energy used per day"), unsafe_allow_html=True)
k2.markdown(ui.kpi(f"{load.peak_kw():.2f} kW", "peak demand"), unsafe_allow_html=True)
st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

if not st.button("Find My Best System"):
    ui.footer()
    st.stop()

# ---------------- Run ----------------
w = weather(round(lat, 4), round(lon, 4))
site = Site(f"{town}, {state}", lat, lon, band=band, load=load, generator=Generator(kva, fuel), weather=w,
            gen_hours=gen_hours)
if know_fuel:
    site.generator.calibration = calibrate_generator(site, litres_day, D)
with st.spinner("Simulating 8,760 hours for every system size and battery type..."):
    r = plan(site, min_solar_share=target, fuel_price=fuel_price, defaults=D)
b = r.best
chem = get_chemistry(b.chemistry)
sav1 = r.baseline.cashflow.baseline_cost[1] - b.cashflow.solar_cost[1]

st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
ui.section("Your Result", f"{town.upper()}, {state.upper()}  /  BAND {band}")
st.markdown(
    f"""<div class="bb-reco"><b>Recommended:</b> {b.pv_kwp:.2f} kWp of solar panels, a {b.battery_kwh:.1f} kWh
    {chem.label} battery and a {b.inverter_kw:.1f} kW inverter, keeping your generator as backup.
    Upfront cost about <b>{naira(b.capex.total)}</b>.</div>""", unsafe_allow_html=True)
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
dark_saved = r.baseline.operation.dark_hours - b.operation.dark_hours
kpis = [(naira(sav1), "saved in year one"),
        ("n/a" if b.payback_years is None else f"{b.payback_years * 12:.0f} months", "to pay back"),
        (f"{r.fuel_saved_litres_per_year:,.0f} L", f"of {fuel} avoided each year"),
        (f"{r.co2_saved_t_per_year:.1f} t", "of CO₂ avoided each year")]
if dark_saved > 1:
    kpis.append((f"{dark_saved:,.0f} h", "fewer hours in the dark each year"))
cols = st.columns(len(kpis), gap="small")
for col, (v, l) in zip(cols, kpis):
    col.markdown(ui.kpi(v, l), unsafe_allow_html=True)
if not know_fuel:
    st.caption("For a sharper estimate, switch on 'I know how many litres I buy per day'.")

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["A Week of Your Power", "Battery Comparison", "Ten-Year Money", "Data and Assumptions"])

with tab1:
    res = b.dispatch
    week = st.slider("Week of the year", 1, 51, 10)
    sl = slice((week - 1) * 168, week * 168)
    x = r.site.weather.index[sl]
    fig = go.Figure()
    for name, arr, col in [("Solar", res.pv_used_kw, ui.YELLOW), ("Battery", res.batt_discharge_kw, ui.GREEN),
                           ("Grid", res.grid_import_kw - res.grid_charge_kw, "#9AA5B1"),
                           ("Generator", res.gen_kw, ui.ORANGE)]:
        fig.add_trace(go.Scatter(x=x, y=arr[sl], name=name, stackgroup="one", line=dict(width=0.4, color=col)))
    fig.add_trace(go.Scatter(x=x, y=res.load_kw[sl], name="Demand", line=dict(color="#111", width=1.4)))
    fig.add_trace(go.Bar(x=x, y=np.where(res.grid_off[sl], res.load_kw.max() * 1.1, 0), name="Grid outage",
                         marker_color="rgba(218,122,44,0.10)", hoverinfo="skip"))
    fig.update_layout(bargap=0, yaxis_title="kW")
    st.plotly_chart(style(fig, 400), use_container_width=True)
    soc = go.Figure(go.Scatter(x=x, y=res.soc[sl] * 100, line=dict(color=ui.GREEN, width=2), name="Battery charge"))
    soc.update_layout(yaxis_title="Battery charge (%)")
    st.plotly_chart(style(soc, 220), use_container_width=True)

with tab2:
    rows = []
    for key, o in r.best_per_chemistry().items():
        c = get_chemistry(key)
        rows.append({"Battery": c.label, "Best system": f"{o.pv_kwp:.2f} kWp + {o.battery_kwh:.1f} kWh",
                     "Upfront": naira(o.capex.total), "Lasts (years)": round(o.ageing.life_years, 1),
                     "Replacements in 10 years": len(o.cashflow.battery_replacement_years),
                     "10-year cost (today's money)": naira(o.npv_ngn),
                     "Outage hours on solar": f"{100 * o.operation.solar_share_of_outage_load:.0f}%"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.markdown("The cheapest battery to buy is not always the cheapest to own. Heat and deep daily cycling "
                "wear lead-acid out fastest. See **Battery Afterlife** for the full picture.")

with tab3:
    yrs = b.cashflow.years
    f2 = go.Figure([go.Scatter(x=yrs, y=np.cumsum(b.cashflow.baseline_cost), name="Generator only",
                               line=dict(color=ui.ORANGE, width=3)),
                    go.Scatter(x=yrs, y=np.cumsum(b.cashflow.solar_cost), name="Solar + battery",
                               line=dict(color=ui.GREEN, width=3))])
    f2.update_layout(xaxis_title="Year", yaxis_title="Total spent so far (₦)")
    st.plotly_chart(style(f2, 380), use_container_width=True)
    sens = sensitivity(r)
    sens["payback_years"] = sens["payback_years"].map(lambda v: "n/a" if v is None else f"{v:.1f}")
    sens.columns = ["Fuel price (₦/L)", "Payback (years)", "Net saving over 10 years (₦)"]
    st.markdown("**If fuel prices fall or rise**")
    st.dataframe(sens, hide_index=True)

with tab4:
    st.markdown(f"""
- **Solar:** PVGIS v5.3 (EU Joint Research Centre; SARAH3 satellite and ERA5), 2023, optimal tilt, 14% losses.
  Here: **{r.site.weather['pv_kw_per_kwp'].sum():,.0f} kWh per kWp per year**.
- **Grid:** {D['grid']['band_hours'][band]} h/day of supply (NERC Band {band}); outages placed in random daily blocks.
- **Fuel:** {naira(fuel_price)}/L, CO₂ {D['fuel'][fuel]['co2_kg_per_litre']} kg/L, rising {100 * D['fuel']['escalation_per_year']:.0f}% a year.
- **Equipment prices:** Nigerian retailer listings, Oct to Nov 2026 (panels about ₦300k/kWp, hybrid inverter ₦120k/kW, LFP ₦250k/kWh, lead-acid ₦140k/kWh). Check them against installer quotes.
- **Tariffs:** NERC ORDER/NERC/2026/093 (Sep 2026), residential.
- **Battery life:** rainflow cycle counting plus heat-accelerated calendar ageing.
- Full method in `docs/METHODS.md` on GitHub.
""")

card = impact_card(f"{town}, {state}", f"{b.pv_kwp:.2f} kWp solar + {b.battery_kwh:.1f} kWh {chem.label}",
                   sav1, b.payback_years, r.fuel_saved_litres_per_year, r.co2_saved_t_per_year,
                   f"Battery: replace every {b.ageing.life_years:.1f} years. Recycle old batteries safely, never dump them.")
st.download_button("Download My Impact Card", card, file_name="switchnaija_impact.png", mime="image/png")
st.caption("Planning estimate, not a quote.")
ui.footer()
