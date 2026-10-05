"""Full public proxy-cycle admissibility, not observed annual firm service.

Each proxy is one deterministic demand shape. All hours of availability are
optimistic unless an explicit common outage is inserted. No backup heat.
SourceA optimistic grade boxes and DEA fixed-volume tanks as in prior pilot.
"""
from pathlib import Path
from datetime import datetime,timezone
import csv,json,importlib.util,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'src'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
lp=module('lp','physical_service_feasibility_r32_20261002.py')
vf=module('vf','physical_service_volume_flow_r32_20261002.py')
def main():
    source=ROOT/'datasets/scaled_heat_proxy_profiles_5regions_20260929.csv'
    groups={}
    with source.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):groups.setdefault(r['shape_region'],[]).append(float(r['proxy_heat_mwh']))
    templates=[s for s in vf.stores() if s['volume_m3'] in [0,50000]]
    rows=[];out=ROOT/'results/physical_service_annual_matrix_r32_20261002.csv'
    # Predeclared paired matrix:5proxies x2mean-duty ratios x2temperatures
    # x2stores x2models x2capture states=160LPs. Flow450kg/s common.
    for region,shape in groups.items():
      a=np.asarray(shape);a=a/a.mean();n=len(a)
      for duty in [.2,.3]:
       d=37.3*duty*a
       for ts in [100,120]:
        for s in templates:
         for cascade in [False,True]:
          for capture in [False,True]:
            r=lp.solve(d,ts,60,capture,cascade,0,tank_hot_C=s['hot_C'],
                tank_approach_K=s['hot_C']-s['service_C'],
                usable_capacity_MWh=.9*1000*s['volume_m3']*.00418*(s['hot_C']-60)/3600,
                store_power_MW=s['rate_MW'],flow_limit_kg_s=450,
                weekly_loss=1-(1-s['loss_daily'])**7,charge_efficiency=1,discharge_efficiency=1,
                steam_grade_override_C=390,compressor_grade_override_C=158,auxiliary_fraction=s['aux'])
            r.update(proxy=region,mean_duty_ratio_SCENARIO=duty,tank=s['name'],
                     availability='All8784h available: optimistic screen, NOT annual reliability validation',
                     proxy_kind='Public weather/demand-modeled composite, not metered heat year')
            rows.append(r)
            # Work output checkpoint, never modifies readonly raw data.
            with out.open('w',encoding='utf-8',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            print(f"{len(rows)}/160 {region} duty={duty} Ts={ts} store={s['volume_m3']} cascade={cascade} capture={capture} unmet={r['unserved_MWh']:.3f} solver={r['solver_seconds']:.2f}s",flush=True)
    pairs=[]
    keys=['proxy','mean_duty_ratio_SCENARIO','supply_temperature_C','tank']
    def get(r,model,capture):return next(x for x in rows if all(x[k]==r[k] for k in keys) and x['model']==model and x['capture_on']==capture)
    for r in rows:
        if r['capture_on'] or r['model']!='temperature_cascade':continue
        c=get(r,'temperature_cascade',True);agg=get(r,'aggregate_heat',True)
        pairs.append({**{k:r[k] for k in keys},'base_pass':r['service_feasible'],'CCS_pass':c['service_feasible'],
                      'aggregate_CCS_pass':agg['service_feasible'],
                      'false_pass':r['service_feasible'] and agg['service_feasible'] and not c['service_feasible'],
                      'CCS_unmet_MWh':c['unserved_MWh'],'base_unmet_MWh':r['unserved_MWh'],
                      'CCS_heatpump_MWh':c['heatpump_electric_MWh']})
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),LPs=len(rows),pairs=len(pairs),
                false_passes=sum(p['false_pass'] for p in pairs),paired_passes=sum(p['base_pass'] and p['CCS_pass'] for p in pairs),
                comparisons=pairs,max_eq_error=max(r['max_eq_error'] for r in rows),
                max_ub_violation=max(r['max_ub_violation'] for r in rows),total_solver_seconds=sum(r['solver_seconds'] for r in rows),
                unit='Five deterministic proxy cycles, not8784independent observations or observed demand years',
                interpretation='Necessary optimistic finite-storage/hydraulic grade screen. No backup and no sufficient hot-composite/hardware certification.')
    (ROOT/'results/physical_service_annual_matrix_qc_r32_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='comparisons'},indent=2),flush=True)
if __name__=='__main__':main()
