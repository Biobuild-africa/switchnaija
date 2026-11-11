"""Battery Afterlife: which battery really lasts in a Nigerian room, and what to do when it dies."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from switchnaija.battery import ROOMS, BatteryUse, compare, room_sensitivity
from switchnaija.config import load_defaults, towns
from switchnaija.sources.pvgis import fetch_pv_hourly

D = load_defaults()
FONT = dict(family="DM Sans, sans-serif", color=ui.MUTED)
COLORS = {"lead_acid": ui.ORANGE, "lfp": ui.GREEN}


@st.cache_data(show_spinner="Fetching hourly temperatures for your location...")
def temperatures(lat: float, lon: float):
    return fetch_pv_hourly(lat, lon)["temp_c"].to_numpy()


def naira(x: float) -> str:
    return f"₦{x:,.0f}"


def style(fig: go.Figure, h: int) -> go.Figure:
    fig.update_layout(height=h, font=FONT, plot_bgcolor="#fff", paper_bgcolor="#fff",
                      margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.2))
    fig.update_xaxes(gridcolor="#EEF1EE")
    fig.update_yaxes(gridcolor="#EEF1EE")
    return fig


ui.nav("battery")
ui.hero(
    "02 / Battery Afterlife",
    "Which Battery Really Lasts, and Where Should It Go After?",
    "Cheap batteries die early in Nigerian heat and too many end up broken open for scrap. Compare lead-acid "
    "and lithium (LFP) for your own use and room: how long each lasts, what it really costs over ten years, "
    "and how much waste and lead it leaves behind.",
)
st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

ui.section("Tell Us How You Use Your Battery", "STEP 1 OF 1")
c1, c2, c3 = st.columns(3, gap="medium")
with c1.container(border=True):
    st.markdown("#### Location")
    T = towns()
    states = sorted({t["state"] for t in T})
    state = st.selectbox("State", states, index=states.index("Osun"))
    options = [t for t in T if t["state"] == state]
    town = st.selectbox("Town", [t["town"] for t in options])
    t = next(x for x in options if x["town"] == town)
    room = st.selectbox("Where is the battery kept?", list(ROOMS), index=1,
                        help="Batteries age faster when hot. A closed cabinet or a space under a metal roof "
                             "runs much hotter than the air outside.")
with c2.container(border=True):
    st.markdown("#### Daily use")
    daily = st.number_input("Energy taken from the battery per day (kWh)", 0.2, 50.0, 2.0, 0.1,
                            help="A fan, TV and lights for an evening is about 1 to 2 kWh. The Energy Planner "
                                 "can estimate this for you.")
    days = st.slider("Days a week the battery is used", 1, 7, 7)
    oversize = st.slider("Extra capacity", 1.0, 2.0, 1.0, 0.1,
                         help="1.0 = the smallest bank that delivers your daily energy safely. A bigger bank "
                              "is emptied less deeply each day, which helps lead-acid last longer.")
with c3.container(border=True):
    st.markdown("#### Prices you pay")
    p_la = st.number_input("Lead-acid (₦ per kWh)", 20000, 1000000,
                           int(D["battery"]["lead_acid"]["price_ngn_per_kwh"]), 5000,
                           help="A 12 V 200 Ah battery holds 2.4 kWh: divide its price by 2.4.")
    p_lfp = st.number_input("Lithium LFP (₦ per kWh)", 50000, 2000000,
                            int(D["battery"]["lfp"]["price_ngn_per_kwh"]), 5000,
                            help="A 48 V 100 Ah pack holds about 5 kWh: divide its price by 5.")
    st.caption("Defaults: Nigerian retailer listings, Oct to Nov 2026.")

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
if not st.button("Compare Batteries"):
    ui.footer()
    st.stop()

temps = temperatures(round(t["lat"], 4), round(t["lon"], 4))
use = BatteryUse(daily, days, oversize, room)
res = compare(use, temps, defaults=D, prices={"lead_acid": p_la, "lfp": p_lfp})
la, lfp = res["lead_acid"], res["lfp"]
best = min(res.values(), key=lambda r: r.cost_npv_ngn)
other = lfp if best is la else la
saving = other.cost_npv_ngn - best.cost_npv_ngn

st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
ui.section("Your Result", f"{town.upper()}, {state.upper()}  /  {room.upper()}")
st.markdown(
    f"""<div class="bb-reco"><b>{best.label}</b> is the better buy here. It lasts about
    <b>{best.life_years:.1f} years</b> against {other.life_years:.1f} for {other.label}, and saves about
    <b>{naira(saving)}</b> over ten years in today's money. Your battery space averages
    {best.mean_battery_temp_c:.0f} °C.</div>""", unsafe_allow_html=True)
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

cols = st.columns(2, gap="medium")
for col, r in zip(cols, (la, lfp)):
    with col.container(border=True):
        st.markdown(f"#### {r.label}")
        k1, k2 = st.columns(2)
        k1.markdown(ui.kpi(f"{r.life_years:.1f} yrs", "until it needs replacing"), unsafe_allow_html=True)
        k2.markdown(ui.kpi(f"{r.batteries_bought}", "batteries bought in 10 years"), unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        k3, k4 = st.columns(2)
        k3.markdown(ui.kpi(naira(r.cost_per_kwh_ngn), "per kWh you actually use"), unsafe_allow_html=True)
        k4.markdown(ui.kpi(f"{r.waste_kg:,.0f} kg", "of battery waste in 10 years"), unsafe_allow_html=True)
        st.caption(f"Bank size {r.capacity_kwh:.1f} kWh, emptied to {100 * (1 - r.cycle_depth):.0f}% each use, "
                   f"upfront {naira(r.upfront_ngn)}. Worn out mainly by {r.dominant_mechanism}."
                   + (f" Those {r.batteries_bought} batteries hold about {r.lead_kg:,.0f} kg of lead." if r.lead_kg else ""))

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["Ten-Year Cost", "Heat and Battery Life", "Data and Assumptions"])
with tab1:
    fig = go.Figure()
    for r in (la, lfp):
        fig.add_trace(go.Scatter(x=list(range(0, 11)), y=r.cumulative_cost_ngn, name=r.label, mode="lines+markers",
                                 line=dict(color=COLORS[r.chemistry], width=3, shape="hv")))
    fig.update_layout(xaxis_title="Year", yaxis_title="Total spent on batteries (₦)")
    st.plotly_chart(style(fig, 380), use_container_width=True)
    st.caption("Each step up is a replacement battery. The last year is credited with the life left in the "
               "battery still in use.")
with tab2:
    sens = room_sensitivity(use, temps, defaults=D)
    fig = go.Figure()
    for key, label in ((k, r.label) for k, r in res.items()):
        g = sens[sens["chemistry"] == label]
        fig.add_trace(go.Bar(x=g["room"], y=g["life_years"], name=label, marker_color=COLORS[key],
                             text=[f"{v:.1f}" for v in g["life_years"]], textposition="outside"))
    fig.update_layout(barmode="group", yaxis_title="Years until replacement")
    st.plotly_chart(style(fig, 380), use_container_width=True)
    st.markdown("Battery ageing roughly doubles for every 10 °C of extra heat for lead-acid, and every 15 °C "
                "for LFP. Moving a battery out of a hot cabinet is often the cheapest upgrade you can make.")
with tab3:
    st.markdown(f"""
- **Temperature:** hourly 2023 air temperature for your location (PVGIS, EU Joint Research Centre), adjusted
  for the battery space. Room adjustments are rules of thumb: measure your own room if you can.
- **Ageing:** daily cycles counted with rainflow counting, plus calendar ageing averaged hour by hour
  (hot afternoons cost more than cool nights save). End of life = 80% of original capacity.
- **Lead-acid:** 1,200 cycles at 50% depth (tubular and AGM datasheets), emptied to 50% at most, 80% round-trip efficiency.
- **LFP:** 4,000 cycles at 80% depth (conservative; datasheets quote 6,000+ at 25 °C), emptied to 10%, 95% efficiency.
- **Cost:** ten-year present value at a {100 * D['finance']['discount_rate']:.0f}% real discount rate, with replacements and a
  credit for life left at year ten. Cost per kWh = present cost divided by discounted kWh delivered.
  Real LFP packs come in fixed sizes (about 2.5 or 5 kWh), so your actual bank may be a little bigger.
- **Waste:** lead-acid about 29 kg per kWh and 55% lead by weight (US EPA); LFP about 9 kg per kWh (Pylontech US3000C datasheet).
- Full method in `docs/METHODS.md` on GitHub.
""")

st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)
ui.section("When Your Battery Dies")
d1, d2, d3 = st.columns(3, gap="medium")
d1.markdown(ui.card(
    "✓", "Do",
    "Keep dead batteries upright, dry and away from children and food. Tape over the terminals. Return them to "
    "the seller or installer when you buy a replacement, and ask whether they pass them to a recycler with a "
    "NESREA permit."), unsafe_allow_html=True)
d2.markdown(ui.card(
    "✕", "Don't",
    "Never break a battery open, pour out the acid, or burn or melt it. Don't sell to buyers who crack batteries "
    "open by the roadside. Keep swollen or damaged lithium batteries outside, away from anything that can burn."),
    unsafe_allow_html=True)
d3.markdown(ui.card(
    "!", "Why it matters",
    "In 2025 reporters tested 70 people in Ogijo, Ogun State, near lead battery recycling plants. Every factory "
    "worker tested had raised blood lead, and 8 of 14 children were above the 5 µg/dL level the WHO treats as "
    "hazardous. Nigeria's National Environmental (Battery Control) Regulations, 2024 now cover how used batteries "
    "are collected, stored and recycled."), unsafe_allow_html=True)
st.caption("Sources: Premium Times / ICIR investigation (Nov 2025); Premium Times (Mar 2025); "
           "Federal Ministry of Environment launch of the Battery Control Regulations (Aug 2024).")
ui.footer()
