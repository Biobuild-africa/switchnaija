import streamlit as st

import ui

ui.nav("")
ui.hero(
    "BioBuild Africa  /  SwitchNaija",
    "Cleaner Energy and Safer Communities for Nigeria",
    "Free tools built on open satellite, weather and government data. Find out what switching from your "
    "generator to solar would really cost and save, which battery lasts longest in Nigerian heat, and "
    "which schools and markets are most exposed to flooding.",
    [("Plan My Switch", "/energy", True), ("See Flood Risk", "/flood", False)],
    image=ui.HERO_ART,
)

st.markdown("<div style='height:56px'></div>", unsafe_allow_html=True)
ui.section("Three Tools, One Goal")
c1, c2, c3 = st.columns(3, gap="medium")
c1.markdown(ui.card("☀", "Energy Planner",
                    "Real hourly solar data for your exact location, your NERC band and your generator. "
                    "Get the right system size, the payback time, and the fuel and CO₂ you avoid.",
                    "Plan my switch", "/energy"), unsafe_allow_html=True)
c2.markdown(ui.card("🔋", "Battery Afterlife",
                    "Lead-acid or LFP? See how long each really lasts in a hot room, what it costs over "
                    "ten years, and how to store and recycle it safely instead of dumping it.",
                    "Compare batteries", "/battery"), unsafe_allow_html=True)
c3.markdown(ui.card("🌧", "FloodSafe",
                    "Forty-five years of rainfall records and flood-hazard maps, used to rank the schools and "
                    "markets most at risk in Idemili South, Ede and Lagos.",
                    "Check flood risk", "/flood"), unsafe_allow_html=True)

st.markdown("<div style='height:56px'></div>", unsafe_allow_html=True)
ui.section("Why This Matters")
a, b = st.columns([1.1, 1], gap="large")
a.markdown(
    """
Seven in ten Nigerian businesses own or share a generator. Households burn petrol through every outage,
breathe its fumes and pay more each month. Cheap batteries fail early and are often dumped, leaking lead
and acid into soil and water. And heavy rain keeps flooding the roads children walk to school and the
markets traders depend on.

SwitchNaija turns free public data into answers anyone can act on, and every number shows where it came from.
"""
)
b.markdown(
    "".join([
        ui.kpi("37", "states and FCT covered"),
        "<div style='height:12px'></div>",
        ui.kpi("8,760", "hours simulated for every option"),
        "<div style='height:12px'></div>",
        ui.kpi("100% open", "data sources and code"),
    ]),
    unsafe_allow_html=True,
)
ui.footer()
