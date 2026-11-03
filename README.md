# Trip Copilot - prototype (simulation + demo planner)

Preliminary software model of **Trip Copilot**, a real-time, preference-aware route and itinerary optimiser.
Team Rocket, Seva First Innovation Challenge 2026, Screening Round 2.

## What this is (and is not)
- `sim.py` compares four planning strategies on 300 random 6-stop days in Pune and writes `sim_results.json`.
- `demo.py` plans one day: time-dependent travel times (M1 model), exhaustive-search optimiser with opening windows (M2),
  a solver-grounded explanation with rejected alternatives and a simulated live re-plan (M4). See `demo_output.txt`.
- Traffic is a **synthetic profile calibrated to TomTom Traffic Index 2025 (Pune)**. Coordinates are approximate and opening
  hours are illustrative. **No live or field data is used.** Production uses Valhalla/OSRM, Google OR-Tools and live traffic.

## Run
```
python3 demo.py                 # default Pune day, start 10:00
START=8 python3 demo.py 0 1 3 6 8 11   # start 08:00, chosen stops (indices from sim.POIS)
python3 sim.py                  # re-runs the 300-trip simulation (writes sim_results.json)
```
Python 3.8+, standard library only.

## Results (300 trips, same trips for every strategy)
| Strategy | In-vehicle min/day | Stops missed (of 6) | Median ETA error |
|---|---|---|---|
| A Manual nearest-next | 124.4 | 0.64 | 12.9% |
| B Static-ETA optimiser | 99.9 | 0.40 | 12.8% |
| C Trip Copilot, time-aware | 99.7 | 0.40 | 11.2% |
| D Trip Copilot + live re-plan | 100.2 | 0.37 | 11.2% |

A to D: -19% in-vehicle time, -42% missed stops. Under these mild disruptions the gain comes mainly from joint optimisation.
Targets for the field trial (not yet validated): ETA error at least 25% lower, at least 15% less travel time.
