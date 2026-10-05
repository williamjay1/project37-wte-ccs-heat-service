"""Independent necessary-cut proof/QC, also exposes secondary-HX adaptation.

All hydraulic/customer choices are declared design contracts, not plant data.
No investment ordering is inferred merely by lowering service temperature.
"""
from pathlib import Path
import csv,json,math
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((ROOT/'results/physical_service_volume_flow_r32_20261002.csv').open(encoding='utf-8')))
H=18.5;OH=5.3;COMP=1.6;HP=9.8*5.5/4.5;TR=60;THP=77;CP=.00418;D=36.5

def max_service(ts,flow):
    high_sources=[(H,390),(OH,91),(COMP,158),(HP,77)]
    candidates=[sum(q for q,t in high_sources),flow*CP*(ts-TR)]
    for theta in sorted({t for q,t in high_sources}):
        if theta>=ts:continue
        f=max(0,min(1,(theta-TR)/(ts-TR)))
        if f<1:candidates.append(sum(q for q,t in high_sources if t>theta)/(1-f))
    return min(candidates)

checks=[]
for r in rows:
    if r['profile']!='constant' or r['model']!='temperature_cascade' or r['capture_on']!='True':continue
    bound=max_service(float(r['supply_temperature_C']),float(r['hydraulic_flow_limit_kg_s']))
    predicted=max(0,D-bound)*168
    err=abs(float(r['unserved_MWh'])-predicted)
    assert err<1e-8
    checks.append(dict(ts=float(r['supply_temperature_C']),flow=float(r['hydraulic_flow_limit_kg_s']),tank=r['tank_type'],
                       analytical_upper_MW=bound,expected_unserved_MWh=predicted,LP_difference_MWh=err))

# Low-temperature HP heat cannot exceed the preheat fraction of cold composite.
# If required low-grade duty is L = D-H-Qdirect >0, L <= m*c*(THP-TR).
L=D-H-OH-COMP
ts_max=TR+(THP-TR)*D/L
flow_min=L/(CP*(THP-TR))
assert abs(ts_max-(TR+D/(CP*flow_min)))<1e-10
min_overhead_fraction=(D-H-COMP-HP)/OH

def lmtd(a,b):
    if min(a,b)<=0:return None
    return a if abs(a-b)<1e-10 else (a-b)/math.log(a/b)
secondary_supply=80;secondary_return=50;pinch=5
adaptation=[]
for ts in [80,85,100,ts_max,120]:
    a=ts-secondary_supply;b=TR-secondary_return
    dt=lmtd(a,b)
    good=min(a,b)>=pinch
    adaptation.append(dict(primary_Tsup_C=ts,primary_Tret_C=TR,
                           secondary_Tsup_C=secondary_supply,secondary_Tret_C=secondary_return,
                           minimum_approach_K_SCENARIO=pinch,secondary_HX_gate_pass=good,
                           required_primary_flow_kg_s=D/(CP*(ts-TR)),
                           required_UA_MW_K=None if dt is None else D/dt,
                           optimistic_CCS_thermal_gate_pass=max_service(ts,450)>=D,
                           allowed_interpretation='Separate consumer-side80/50C scenario. Passing heat/flow/HX cuts remains necessary, not sufficient. No free emitter/pipe/HX adaptation.'))
result=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS independent necessary cut checks, not physical validation',
            independent_constant_tests=len(checks),max_LP_difference_MWh=max(c['LP_difference_MWh'] for c in checks),tests=checks,
            derived_Tsup_max_HP_cut_C=ts_max,derived_required_flow_lower_bound_kg_s=flow_min,
            service_demand_SCENARIO_MW=D,original_flow_contract_SCENARIO_kg_s=150,
            hydraulic_Tsup_min_at_original_flow_C=TR+D/(CP*150),
            feasible_temperature_interval_at_150kg_s='EMPTY even in optimistic heat envelope',
            required_overhead_usable_fraction_energy_lower_bound=min_overhead_fraction,
            overhead_fraction_interpretation='Necessary gross-energy condition only; must not assert83pct heat recovery is physically available.',
            secondary_service_adaptation_scenarios=adaptation,
            generalized_conditions=['D <= sum source useful heat','D <= m_max*c*(Tsup-Tret)',
                                    'For every theta<Tsup: D*(1-(theta-Tret)/(Tsup-Tret)) <= available heat above theta',
                                    'Tsup >= consumer_supply + minimum_approach; Tret >= consumer_return + minimum_approach',
                                    'UA >= D/LMTD at matched consumer supply/return; finite pump/pipe capacity must be checked',
                                    'Every compared plant must meet the same contract before assigning climate/economic benefits'],
            claims_not_supported=['Exact hot-stream heat-exchanger network attainability','Measured operating reliability','Financially optimal first investment','EU27 prevalence or likelihood','Two full independently validated process cases'])
(ROOT/'results/physical_service_contract_independent_qc_r32_20261002.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='tests'},indent=2))
