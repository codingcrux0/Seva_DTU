"""Preliminary simulation for Trip Copilot (synthetic traffic profile calibrated to TomTom Pune 2025).
Compares four planning strategies on random 6-stop Pune days. No field data is used."""
import math, random, json, itertools, statistics as st

# (name, lat, lon, dwell_min, open_h, close_h)  coordinates approximate, windows illustrative
POIS = [
 ("Shaniwar Wada",18.5195,73.8553,60, 8.0,18.0),
 ("Dagdusheth Ganpati",18.5164,73.8561,30, 6.0,22.0),
 ("Aga Khan Palace",18.5524,73.9016,60, 9.0,17.5),
 ("Kelkar Museum",18.5113,73.8553,75, 9.5,17.5),
 ("Parvati Hill",18.4881,73.8429,60, 5.0,20.0),
 ("Pataleshwar Cave",18.5287,73.8478,30, 8.0,18.0),
 ("Sinhagad Fort",18.3664,73.7558,120,5.0,18.0),
 ("Phule Mandai",18.5102,73.8621,45, 7.0,20.0),
 ("Tulshibaug",18.5112,73.8562,30, 7.0,21.0),
 ("Bund Garden",18.5370,73.8845,45, 6.0,20.0),
 ("Katraj Zoo",18.4545,73.8625,120,9.5,17.5),
 ("Empress Garden",18.5017,73.8885,45, 6.0,18.0),
]
START = (18.5289,73.8744)          # Pune railway station (approx.)
# TomTom Pune 2025: avg 33.33, morning 38.22, evening 41.67 min / 10 km; congestion level 71.1 %
FREE = 33.333/1.711                 # free-flow min per 10 km  (= 19.5)
PROFILE = [(0,1.10),(5,1.10),(7,1.30),(8.5,1.96),(10,1.70),(12,1.55),(15,1.60),(17,2.14),(19,2.14),(20.5,1.50),(22,1.15),(24,1.10)]
AVG_MULT = 1.711
CIRC = 1.35
def mult(h):
    h = min(max(h,0),24)
    for (h0,m0),(h1,m1) in zip(PROFILE,PROFILE[1:]):
        if h0<=h<=h1: return m0+(m1-m0)*(h-h0)/(h1-h0)
def km(a,b):
    R=6371; p1,p2=math.radians(a[0]),math.radians(b[0]); dl=math.radians(b[1]-a[1]); dp=p2-p1
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))*CIRC
def leg_td(a,b,h):   # hours -> minutes, time-dependent
    return km(a,b)*FREE/10*mult(h)
def leg_static(a,b,h=None):
    return km(a,b)*FREE/10*AVG_MULT

def run_plan(order,pos,t,legfn,noise=None,drop_infeasible=False):
    """Walk an order. Returns (t,pos,visited,missed,invehicle_min,eta_err list)."""
    vis=[];mis=[];inv=0;errs=[]
    for p in order:
        P=POIS[p]; q=(P[1],P[2])
        if drop_infeasible:   # planner knowledge: skip stops that cannot be done
            est=legfn(pos,q,t)
            arr=t+est/60
            s=max(arr,P[4])
            if s+P[3]/60>P[5]: mis.append(p); continue
        plan_min=legfn(pos,q,t)
        true_min=leg_td(pos,q,t)*(noise() if noise else 1)
        inv+=true_min; errs.append(abs(plan_min-true_min)/true_min)
        arr=t+true_min/60; pos=q
        s=max(arr,P[4])
        if s+P[3]/60>P[5]: mis.append(p); t=arr; continue
        t=s+P[3]/60; vis.append(p)
    return t,pos,vis,mis,inv,errs

def plan_best(stops,pos,t,legfn):
    """exhaustive search: maximise visited, then minimise finish time (planner uses legfn, no noise)"""
    best=None
    for perm in itertools.permutations(stops):
        tt,_,vis,mis,_,_=run_plan(perm,pos,t,legfn,None,True)
        key=(-len(vis),tt)
        if best is None or key<best[0]: best=(key,perm)
    return list(best[1])
def nn_order(stops,pos):
    rem=list(stops);o=[]
    while rem:
        n=min(rem,key=lambda p:km(pos,(POIS[p][1],POIS[p][2])))
        o.append(n);rem.remove(n);pos=(POIS[n][1],POIS[n][2])
    return o

def one_trip(rng,k=6):
    stops=rng.sample(range(len(POIS)),k); t0=rng.choice([8.0,9.0,10.0,11.0,12.0])
    nz_seed=rng.random()
    def mk():
        r=random.Random(nz_seed)
        def noise():
            n=math.exp(r.gauss(0,0.15))
            if r.random()<0.10: n*=1.0+r.uniform(0.3,0.8)    # incident / blockage on 10 % of legs
            return n
        return noise
    res={}
    # A manual nearest-neighbour by distance, static
    o=nn_order(stops,START); t,_,v,m,inv,e=run_plan(o,START,t0,leg_static,mk()); res['A']=(t,len(v),inv,e)
    # B static-ETA optimiser (order optimised with average ETAs), no re-plan
    o=plan_best(stops,START,t0,leg_static); t,_,v,m,inv,e=run_plan(o,START,t0,leg_static,mk(),True); res['B']=(t,len(v),inv,e)
    # C Trip Copilot: time-dependent optimiser, no re-plan
    o=plan_best(stops,START,t0,leg_td); t,_,v,m,inv,e=run_plan(o,START,t0,leg_td,mk(),True); res['C']=(t,len(v),inv,e)
    # D Trip Copilot + live re-planning at every stop (re-optimise remaining with actual clock)
    noise=mk(); pos=START; t=t0; rem=list(stops); vis=[]; inv=0; errs=[]
    while rem:
        o=plan_best(rem,pos,t,leg_td)
        if not o: break
        nxt=o[0]; rem.remove(nxt)
        # drop stops the planner already knows are infeasible
        P=POIS[nxt]; q=(P[1],P[2]); est=leg_td(pos,q,t)
        s=max(t+est/60,P[4])
        if s+P[3]/60>P[5]: continue
        tt,pos,v,m,i2,e=run_plan([nxt],pos,t,leg_td,noise,False); t=tt; vis+=v; inv+=i2; errs+=e
        rem=[x for x in rem if x!=nxt]
        # (if planner order had dropped stops they remain in rem until infeasible check above)
    res['D']=(t,len(vis),inv,errs)
    return stops,t0,res

if __name__=="__main__":
    N=300; rng=random.Random(2026); rows=[]
    for i in range(N):
        stops,t0,res=one_trip(rng); rows.append((stops,t0,res))
    out={}
    for key,label in zip("ABCD",["Manual nearest-next (static)","Static-ETA optimiser","Trip Copilot (time-aware)","Trip Copilot + live re-plan"]):
        inv=[r[2][key][2] for r in rows]; vis=[r[2][key][1] for r in rows]
        fin=[r[2][key][0]-r[1] for r in rows]; err=[statistics for statistics in []]
        errs=[x for r in rows for x in r[2][key][3]]
        def ci(xs):
            m=st.mean(xs); b=[st.mean(random.Random(i).choices(xs,k=len(xs))) for i in range(300)]; b.sort(); return m,b[7],b[292]
        out[key]=dict(label=label,invehicle=ci(inv),visited=ci(vis),duration=ci(fin),eta_err=100*st.mean(errs),eta_err_med=100*st.median(errs))
    json.dump(out,open('sim_results.json','w'),indent=1)
    for k,v in out.items(): print(k,v['label'],{a:(round(b,2) if not isinstance(b,tuple) else tuple(round(x,2) for x in b)) for a,b in v.items() if a!='label'})
    # representative instance for map
    json.dump(dict(N=N),open('sim_meta.json','w'))
