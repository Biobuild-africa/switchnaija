# SwitchNaija

**Open-data tools for cleaner, cheaper energy and safer communities in Nigeria.**
A BioBuild Africa project.

[![tests](https://github.com/Biobuild-africa/switchnaija/actions/workflows/ci.yml/badge.svg)](https://github.com/Biobuild-africa/switchnaija/actions)

70.7% of Nigerian firms own or share a generator (AfDB African Economic Outlook 2026, citing World Bank Enterprise Surveys), households
burn petrol through every outage, cheap batteries die early and get dumped, and floods keep hitting
schools and markets. SwitchNaija turns free public data into practical answers.

| Module | Question | Status |
|---|---|---|
| **Energy Planner** | Should I switch from my generator to solar? What size, which battery, what payback, how much CO2? | Working |
| **Battery Afterlife** | Which battery is cheapest over its life in a hot Nigerian room, and how do I dispose of it safely? | Working |
| **FloodSafe** | Which schools and markets are most exposed to flooding, and is heavy rain getting more frequent? | Working |

## Energy Planner: what it does

For any town in the 36 states and the FCT (or any coordinates):

1. Pulls **hourly solar output for that exact spot** from PVGIS (EU Joint Research Centre, SARAH3 satellite data).
2. Builds an **hourly demand profile** from your appliances, or calibrates it to the litres of fuel you really buy.
3. Generates **grid outages** from your NERC tariff band (Band A about 20 h of supply a day, Band E about 4 h).
4. Simulates **all 8,760 hours of the year** for dozens of solar and battery sizes and two battery chemistries
   (lead-acid and LFP, the two sold widely in Nigeria), with the generator kept as backup.
5. Estimates **battery life** with rainflow cycle counting and heat-accelerated calendar ageing.
6. Picks the option with the **lowest 10-year cost** and reports upfront cost, payback, fuel and CO2 avoided,
   plus a shareable impact card.

Example (small home in Ede, Osun State, Band C, 2.5 kVA petrol generator used 6pm to midnight,
petrol N1,400/L, November 2026 market prices):

| | Generator only | Recommended: 1.0 kWp + 2.2 kWh LFP |
|---|---|---|
| Upfront cost | none | about N1.07m |
| Petrol per year | about 560 L | about 6 L |
| Hours without power per year | about 3,300 | about 410 |
| CO2 per year | 1.6 t | 0.3 t |
| Battery life | n/a | about 6.6 years (lead-acid: about 2.7) |
| Payback | | about 13 months |

Every default (fuel, tariffs, equipment prices, battery parameters) is in `switchnaija/data/defaults.yaml` with its source and date. It was last checked against NERC tariff orders, fuel market reports, manufacturer datasheets and Nigerian retailer listings in November 2026. Prices move monthly: enter what you actually pay.

## Battery Afterlife: what it does

For your town, your daily battery use and where the battery is kept (air-conditioned room, ventilated
room, closed cabinet, or outside under a metal roof):

1. Sizes a lead-acid and an LFP bank to deliver **the same usable energy** (lead-acid should only be emptied to 50%).
2. Ages each battery **hour by hour** with rainflow cycle counting and heat-accelerated calendar ageing,
   using real hourly temperatures for the location (PVGIS).
3. Reports life in years, batteries bought over ten years, **cost per kWh actually used**, and the
   **battery waste and lead** each choice leaves behind.
4. Shows how much the battery space alone changes battery life, and gives safe end-of-life steps
   (Nigeria's National Environmental (Battery Control) Regulations, 2024).

Example (Osogbo, 2 kWh a day, ventilated room, default prices): lead-acid lasts about 1.9 years and costs
about N524 per kWh used; LFP lasts about 5.4 years at about N202 per kWh, and leaves 41 kg of battery waste
over ten years instead of 778 kg (about 430 kg of it lead).

## FloodSafe: what it does

For any local government area in Nigeria:

1. Pulls every school and market on the **GRID3 Nigeria** register (about 108,000 schools and 11,000 markets).
2. Reads the **EU Copernicus / JRC global river flood maps** (about 90 m) at each one, for floods expected once in
   10 and once in 100 years, and ranks them High, Medium or Low. Only the map pixels needed are read over the internet.
3. Analyses **45 years of daily rainfall** (NASA POWER, 1981 to 2025): wettest day of each year, Mann-Kendall trend
   test with Sen's slope, and a GEV extreme-value model whose centre can shift over time, to answer "is heavy rain
   getting heavier here?"
4. Shows a map, a downloadable list for the LGA, and the rainfall trend in plain words.

Examples: in **Ogbaru, Anambra** (Niger floodplain), 46 of 100 schools and markets sit inside the mapped
1-in-100-year flood area, 35 of them inside the 1-in-10-year area, with up to 5.8 m of water. In **Idemili South**, none
do: the risk there is flash flooding and gully erosion, which river maps do not show. Around **Ede, Osun**, the
wettest day of the year has risen by about 3 mm a decade since 1981 (Mann-Kendall p = 0.04).

## Quick start

```bash
git clone https://github.com/Biobuild-africa/switchnaija.git
cd switchnaija
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Or from Python:

```python
from switchnaija.energy import Site, plan
r = plan(Site.from_town("Ikeja", band="B"))
print(r.best.summary())
```

Run the tests: `pytest` (add `-m "not network"` to skip the live API checks).

## Project layout

```
switchnaija/
  sources/    PVGIS, NASA POWER connectors (cached)
  energy/     load profiles, outages, generator fuel curve, hourly dispatch, economics, optimiser
  battery/    chemistries, rainflow counting, ageing model, lifetime cost and waste
  flood/      rainfall extremes and trend tests, flood exposure of schools and markets
  data/       defaults.yaml (every assumption, with sources), towns.json (37 state capitals + more)
app/          Streamlit web app, styled to match biobuildafrica.org (app/ui.py)
tests/        pytest suite, including real PVGIS data for Ede (2023)
run_app.bat   one-click launcher for Windows
docs/         METHODS.md
```

## Data sources

- PVGIS v5.3, EU Joint Research Centre: hourly PV output and temperature
- NASA POWER: daily rainfall and hourly irradiance (fallback)
- National Bureau of Statistics (NBS): Petrol and Diesel Price Watch
- Nigerian Electricity Regulatory Commission (NERC): tariff band supply hours
- OpenStreetMap Nominatim: town coordinates
- GRID3 Nigeria: schools and markets with LGA names
- Copernicus Emergency Management Service (EU JRC): global river flood hazard maps v2.1

## Limitations

Planning estimates, not engineering design. Outage timing is randomised within each band's hours;
battery capacity fade within a battery's life is not fed back into the hourly simulation; prices change
monthly. See `docs/METHODS.md`.

## Author

Emmanuel Adetooto, Climate Data and Energy Systems Lead, BioBuild Africa.
B.Eng Metallurgical and Materials Engineering (FUTA). MIT licence.

Code was written with AI coding assistance (Anthropic Claude). Every assumption is listed with its
source in `switchnaija/data/defaults.yaml`, and the test suite checks the physics and the sums.
