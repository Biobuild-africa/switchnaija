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
| **FloodSafe** | Which schools and markets are most exposed to flooding, and is heavy rain getting more frequent? | In progress |

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
  battery/    chemistries, rainflow counting, ageing model
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

## Limitations

Planning estimates, not engineering design. Outage timing is randomised within each band's hours;
battery capacity fade within a battery's life is not fed back into the hourly simulation; prices change
monthly. See `docs/METHODS.md`.

## Author

Emmanuel Adetooto, Climate Data and Energy Systems Lead, BioBuild Africa.
B.Eng Metallurgical and Materials Engineering (FUTA). MIT licence.

Code was written with AI coding assistance (Anthropic Claude). Every assumption is listed with its
source in `switchnaija/data/defaults.yaml`, and the test suite checks the physics and the sums.
