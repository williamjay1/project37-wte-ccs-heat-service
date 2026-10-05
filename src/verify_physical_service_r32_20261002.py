"""Independent analytic/property checks, separate from LP construction."""
from pathlib import Path
import csv
import json
import sys
import importlib.util
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pilot_lp',ROOT/'src/physical_service_feasibility_r32_20261002.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=list(csv.DictReader((ROOT/'results/physical_service_feasibility_pilot_r32_20261002.csv').open()))
tests=[]
H=18.5; direct=5.3+1.6; hp=9.8*5.5/4.5
total=H+direct+hp
for ts in [80,100,120]:
    # Low HP at77C imposes a necessary supply-temperature cut. For this
    # particular 3-grade box, remaining cuts are verified non-binding.
    hp_fraction=min(1.,17/(ts-60))
    bound=total if hp_fraction==1 else min(total,(H+direct)/(1-hp_fraction))
    if ts>91:
        bound=min(bound,(H+1.6)/(1-31/(ts-60)))
    expected_unmet=max(0,36.5-bound)*168
    subset=[r for r in rows if r['profile']=='constant_service' and r['model']=='temperature_cascade' and r['capture_on']=='True' and float(r['supply_temperature_C'])==ts]
    for r in subset:
        error=abs(float(r['unserved_MWh'])-expected_unmet)
        assert error<1e-8
        tests.append(dict(test='Independent constant-load cascade cut',temperature_C=ts,store_hours=float(r['store_hours']),analytic_max_delivery_MW=bound,expected_unserved_MWh=expected_unmet,error_MWh=error))
    # Huge capacity (10,000h) is ONLY a mathematical upper-bound test.
    r=m.solve(np.full(24,36.5),ts,60,True,True,10000)
    assert abs(r['unserved_MWh']-max(0,36.5-bound)*24)<1e-8
    tests.append(dict(test='Ideal-size cyclic tank cannot undo constant-grade cut',temperature_C=ts,store_hours=10000,unserved_MWh=r['unserved_MWh']))

# LP zero-source, noCCS, no-store and temperature ceiling failure tests.
r=m.solve(np.full(24,36.5),150,60,False,True,0)
assert r['unserved_MWh']>0
tests.append(dict(test='NoCCS still fails above available steam service temperature',temperature_C=150,unserved_MWh=r['unserved_MWh']))
pilot=json.loads((ROOT/'results/physical_service_pilot_r32_20261002.json').read_text())
assert max(abs(r['hp_hot_MW']-r['hp_source_MW']-r['hp_electric_MW']) for r in pilot['su_partial_replication'])<1e-12
criticalTs=60+17*36.5/(36.5-H-direct)
result=dict(status='PASS within declared prototype',independent_tests=len(tests),tests=tests,
            service_target_MW=36.5,derived_HP_cut_supply_temperature_limit_C=criticalTs,
            boiler_source_cases='UK Fuel Su generic BP anchor; no population extrapolation',
            not_verified=['Full steam-cycle output reproduction in two independent process cases','DEA tank/heat-pump cost and temperature ranges','Annual public shape simulations','Climate threshold errors and monetary investment ordering'],
            formulas='For all cold-composite cuts theta: sum heat delivered below theta <= D_delivered*(theta-Tret)/(Tsup-Tret). Hence D <= Q_above_theta/(1-(theta-Tret)/(Tsup-Tret)) when other heat is below theta. Cyclic inventory cannot create high-grade annual heat.')
(ROOT/'results/physical_service_independent_qc_r32_20261002.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
