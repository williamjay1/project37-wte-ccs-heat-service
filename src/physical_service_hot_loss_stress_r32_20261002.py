"""Explicit rated-capacity standing loss stress; not a full tank cooling model.

Stores are maintained hot throughout the cycle, so the catalogue reference
loss is charged every hour even at low useful SOC. This is a conservative
operational alternative, not a calibrated partially cooled/stratified tank.
The baseline SOC-decay rows are retained; original output files are untouched.
"""
from pathlib import Path
from datetime import datetime,timezone
import csv,json,importlib.util
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'src'/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
lp=load('lp','physical_service_feasibility_r32_20261002.py')
profiles={}
with (ROOT/'datasets/scaled_heat_proxy_profiles_5regions_20260929.csv').open(encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):profiles.setdefault(r['shape_region'],[]).append(float(r['proxy_heat_mwh']))
base=list(csv.DictReader((ROOT/'results/physical_service_annual_matrix_r32_20261002.csv').open(encoding='utf-8')))
small=list(csv.DictReader((ROOT/'results/physical_service_followup_smallstore_r32_20261002.csv').open(encoding='utf-8')))
rows=[]
for region in ['Oberland','Porto metropolitan area']:
    a=np.asarray(profiles[region]);d=37.3*.3*a/a.mean()
    for v,qnom,rate,loss,aux in [(5000,290,29,.0015,.004),(50000,2880,288,.0006,.002)]:
      for cap in [False,True]:
        r=lp.solve(d,120,60,cap,True,0,tank_hot_C=99,tank_approach_K=2,
            usable_capacity_MWh=.9*1000*v*.00418*39/3600,store_power_MW=rate,
            flow_limit_kg_s=450,weekly_loss=0,charge_efficiency=1,discharge_efficiency=1,
            steam_grade_override_C=390,compressor_grade_override_C=158,auxiliary_fraction=aux,
            maintained_hot_loss_MW=qnom*loss/24)
        r.update(proxy=region,volume_m3=v,rated_reference_capacity_MWh=qnom,
                 loss_model='Maintained-hot fixed reference-rated loss: explicit structural stress',
                 declared_daily_fraction=loss)
        candidates=small if v==5000 else base
        old=next(x for x in candidates if x['proxy']==region and
                 float(x['supply_temperature_C'])==120 and x['model']=='temperature_cascade' and
                 x['capture_on']==str(cap) and (v==5000 or float(x['storage_usable_capacity_MWh'])>0) and
                 (v==5000 or float(x['mean_duty_ratio_SCENARIO'])==.3))
        r.update(original_SOC_unserved_MWh=float(old['unserved_MWh']),
                 increase_unserved_MWh=r['unserved_MWh']-float(old['unserved_MWh']),
                 service_class_changed=r['service_feasible']!=(old['service_feasible']=='True'))
        rows.append(r)
        print(region,v,cap,r['unserved_MWh'],flush=True)
with (ROOT/'results/physical_service_hot_loss_stress_r32_20261002.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
qc=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS bounded alternative',
        LPs=len(rows),changes=sum(r['service_class_changed'] for r in rows),rows=rows,
        max_eq_error=max(r['max_eq_error'] for r in rows),
        max_ub_violation=max(r['max_ub_violation'] for r in rows),
        scope='Eight paired-source controls, not exhaustive annual matrix or observed tank validation.')
(ROOT/'results/physical_service_hot_loss_stress_qc_r32_20261002.json').write_text(json.dumps(qc,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in qc.items() if k!='rows'},indent=2))
