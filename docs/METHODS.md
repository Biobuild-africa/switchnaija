# Methods

## 1. Solar resource

PVGIS v5.3 `seriescalc` returns hourly AC output of a 1 kWp crystalline-silicon system at the optimal
tilt and azimuth, using SARAH3 satellite irradiance, ERA5 temperature and 14% system losses
(cables, inverter, soiling). Timestamps (UTC) are shifted to West Africa Time (UTC+1). Output scales
linearly with installed kWp. If PVGIS is unavailable, NASA POWER hourly irradiance is converted with
a simple model: `P = GHI/1000 x PR x (1 - 0.004 (T_cell - 25))`, `T_cell = T_air + 25 GHI/800`.

## 2. Demand

Each appliance has a power rating, quantity, hours per day, a usage window (which may cross midnight)
and a duty factor (fridges and freezers cycle, about 0.4 to 0.5). Its daily energy is spread evenly over
the window. The daily profile is repeated over the year.

**Calibration.** If the user knows their daily fuel purchase, the generator fuel curve is scaled so that the
modelled generator-only scenario uses exactly that amount.

## 3. Grid availability

NERC bands commit a minimum number of supply hours per day (A 20, B 16, C 12, D 8, E 4).
Each day, the outage hours are split into one to three blocks at random, non-overlapping times
(seeded, so results are reproducible). "No grid" means 24 h without supply.

## 4. Generator

Fuel use per hour: `L = F0 x P_rated + F1 x P_out` (HOMER form). Diesel: F0 = 0.08145 L/h/kW,
F1 = 0.246 L/kWh (the HOMER defaults widely cited in the literature). Petrol: F0 = 0.15, F1 = 0.50,
fitted to datasheets (Sumec Firman SPG3000, 2.5 kVA: about 1.07 L/h at half load; model 1.0 L/h, tested).
Rated kW = kVA x power factor (1.0 for small petrol sets, 0.8 for diesel).
CO2: 2.31 kg/L petrol, 2.68 kg/L diesel (US EPA 2025: 2.32 and 2.70).

**When the generator runs.** Many households only run the generator in the evening. The user can limit
the generator to certain hours (default in the app: 6pm to midnight); outage demand outside those hours
goes unserved in both scenarios, and the tool reports the hours without power avoided by solar.

## 5. Hourly dispatch ("solar first")

For each hour:
1. Solar (limited by inverter size) serves the load.
2. Surplus charges the battery (limited by C-rate: 0.2C lead-acid, 0.5C lithium), the rest is curtailed.
3. Grid on: remaining load from the grid; the battery is held full for the next outage.
4. Grid off: battery discharges down to its minimum state of charge (1 - max DoD), then the generator
   runs; anything beyond the generator rating is unserved.

Charge and discharge efficiencies are each the square root of round-trip efficiency.
The test suite checks that energy balances to within 1e-9 kWh in every hour.

## 6. Battery ageing

Linear damage accumulation (Palmgren-Miner), as in HOMER and NREL SAM:

- **Cycling.** The hourly state-of-charge series is decomposed into cycles by ASTM E1049 rainflow counting.
  Each cycle of depth d and count n adds `n / N(d)`, with `N(d) = N_ref (d_ref / d)^k`.
- **Calendar.** Each year adds `1 / L_cal(T)`, with `L_cal(T) = L_25 / 2^((T - 25)/T_double)`.
  T is the mean ambient temperature at the site plus 3 C for the battery room.
- **Life** = 1 / (annual cycling damage + annual calendar damage), to 80% remaining capacity.

| | Lead-acid (tubular / AGM) | LFP |
|---|---|---|
| Cycles at reference DoD | 1,200 at 50% | 4,000 at 80% |
| Max DoD | 50% | 90% |
| Round-trip efficiency | 80% | 95% |
| Calendar life at 25 C | 6 years | 15 years |
| Ageing doubles every | +10 C | +15 C |

Sources: tubular 900 to 1,100 cycles and AGM about 450 cycles at 80% DoD (Eastman EM200, PCE datasheets);
Trojan (reaction rate doubles per 10 C); LFP 6,000+ cycles at 80% DoD and 25 C (Felicity, Pylontech), so
4,000 is a conservative hot-climate value; LFP round-trip efficiency 95% (BYD). NMC parameters are in the
code but excluded by default: NMC home batteries are not commonly sold in Nigeria and its values are not
datasheet-sourced.

## 7. Economics and optimiser

- Upfront cost = PV + inverter + battery + 10% installation. Inverter = max(1.3 x peak load, 0.8 x PV kWp),
  rounded up to 0.5 kW.
- Yearly cost = fuel (escalating 5% a year in real terms) + generator servicing per running hour
  + grid electricity + 1% PV/inverter maintenance.
- Batteries are replaced at multiples of their estimated life; unused life at year 10 is credited back.
- 10-year net present value at a 12% real discount rate.
- Search grid: PV = {0.5 to 2.0} x the size that would cover daily demand; battery = {0.25 to 1.5} x the
  daily outage-hour demand divided by usable DoD; two chemistries (72 options). The lowest-NPV option
  meeting the minimum solar share is recommended.
- Fuel price sensitivity: payback at 70%, 100% and 130% of the input price.

## 8. Known limitations

- Outage timing is synthetic; real outages cluster and vary by feeder.
- One weather year (2023).
- Capacity fade is not fed back into the hourly dispatch.
- Equipment prices come from Nigerian retailer listings (Oct to Nov 2026) and vary by brand and city.
- Fuel defaults use November 2026 market prices because the latest NBS Price Watch (May 2026) reflects a price spike.
