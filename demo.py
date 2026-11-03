"""Trip Copilot - planning demo (M1 time-dependent ETA + M2 joint optimiser + M4 solver-grounded explanation).
Run:  python demo.py                 (default Pune day, start 10:00)
      python demo.py 8 2 3 11 6 9    (stop indices from sim.POIS, then optional --start HH via env START=9)
Traffic is a SYNTHETIC profile calibrated to TomTom Pune 2025 (see sim.py). No live data is used.
"""
import sys, os
import sim
from sim import POIS, START, leg_td, leg_static, nn_order, plan_best, run_plan

def hhmm(h):
    m = int(round(h * 60)) % (24 * 60)          # round to whole minutes first, then split (avoids 10:60)
    return f"{m // 60:02d}:{m % 60:02d}"

def schedule(order, t0):
    """Deterministic schedule using the model's expected leg times (no noise)."""
    t, pos, rows, inv = t0, START, [], 0.0
    for p in order:
        P = POIS[p]; q = (P[1], P[2]); leg = leg_td(pos, q, t); arr = t + leg / 60
        start = max(arr, P[4]); ok = start + P[3] / 60 <= P[5]
        rows.append(dict(name=P[0], depart=t, leg=leg, arrive=arr, start=start, end=start + P[3] / 60,
                         open=P[4], close=P[5], ok=ok, tag='PREDICTED'))
        inv += leg
        if ok: t = start + P[3] / 60
        else: t = arr
        pos = q
    return rows, inv

def main():
    args = [a for a in sys.argv[1:] if a.isdigit()]
    stops = [int(a) for a in args] if args else [0, 2, 3, 8, 9, 10]
    t0 = float(os.environ.get('START', 10))
    print(f"TRIP COPILOT demo  |  start {hhmm(t0)} at Pune station  |  stops: {', '.join(POIS[i][0] for i in stops)}\n")
    best = plan_best(stops, START, t0, leg_td)                    # M2: exhaustive search (k <= 8)
    base = nn_order(stops, START)                                  # manual nearest-next baseline
    rb, ib = schedule(best, t0); rn, inn = schedule(base, t0)
    print("OPTIMISED PLAN (M2, time-dependent, opening windows respected)")
    print(f"{'#':<3}{'Stop':<22}{'Leave':<7}{'Drive':<9}{'Arrive':<8}{'Visit':<13}{'Window':<13}ETA tag")
    for k, r in enumerate(rb, 1):
        flag = '' if r['ok'] else '  <- CLOSED on arrival, skipped'
        print(f"{k:<3}{r['name']:<22}{hhmm(r['depart']):<7}{r['leg']:>4.0f} min  {hhmm(r['arrive']):<8}{hhmm(r['start'])}-{hhmm(r['end']):<7}{hhmm(r['open'])}-{hhmm(r['close']):<7}{r['tag']}{flag}")
    miss_b = sum(not r['ok'] for r in rb); miss_n = sum(not r['ok'] for r in rn)
    print(f"\nIn-vehicle time: {ib:.0f} min, stops missed: {miss_b}   |   manual nearest-next: {inn:.0f} min, stops missed: {miss_n}")
    print("\nWHY THIS ORDER (M4 - every number below comes from the solver, not from a language model)")
    if best == base:
        print("- Nearest-next is already optimal for this set of stops and start time.")
    else:
        print(f"- Nearest-next would go: {' > '.join(POIS[i][0] for i in base)}")
        for r in rn:
            if not r['ok']:
                print(f"- Rejected: reaching {r['name']} at {hhmm(r['arrive'])} cannot fit its visit before the {hhmm(r['close'])} closing time.")
        d = inn - ib
        if miss_n > miss_b: print(f"- Chosen order visits {miss_n - miss_b} more stop(s) ({'+' if -d > 0 else '-'}{abs(d):.0f} min in vehicle).")
        elif d > 0: print(f"- Chosen order saves {d:.0f} min in vehicle with the same stops visited.")
    print("\nLIVE RE-PLAN (M4) - simulated disruption: first leg runs 25 min late")
    first = best[0]; P = POIS[first]
    t = max(rb[0]['arrive'] + 25 / 60, P[4]) + P[3] / 60
    rest = list(best[1:]); new = plan_best(rest, (P[1], P[2]), t, leg_td) if rest else []
    names = lambda o: ' > '.join(POIS[i][0] for i in o)
    print(f"- Clock {hhmm(t)} after {P[0]}. Remaining plan was: {names(rest)}")
    print(f"- Re-optimised from the actual clock: {names(new)}")
    print("- " + ("Order unchanged; ETAs refreshed." if new == rest else "Order changed; the change is explained to the user."))

if __name__ == '__main__':
    main()
