"""Climate thresholds only inside the paired necessary admissible domain.
Outage tests diagnose reliability boundaries; no disguised backup service.
"""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,csv,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'src'/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
lp=module('lp','physical_service_feasibility_r32_20261002.py')
def main():
    with (ROOT/'results/physical_service_annual_matrix_r32_20261002.csv').open(encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f))
    keys=['proxy','mean_duty_ratio_SCENARIO','supply_temperature_C','tank']
    out=[]
    for r in rows:
        if r['capture_on']!='False' or r['model']!='temperature_cascade':continue
        c=next(x for x in rows if all(x[k]==r[k] for k in keys) and x['capture_on']=='True' and x['model']=='temperature_cascade')
        both=r['service_feasible']=='True' and c['service_feasible']=='True'
        n=8784;gross=5.168*3.6*.9972*n;ret=gross*.99*.995
        dep=1.95*n+float(c['heatpump_electric_MWh'])+float(c['store_auxiliary_electric_MWh'])-float(r['store_auxiliary_electric_MWh'])
        fstar=(dep*179+gross*50)/(1000*ret) if both else None
        out.append({**{k:r[k] for k in keys},'both_NECESSARY_pass':both,
                    'fossil_threshold_IF_ADMISSIBLE':fstar,
                    'included_GWP_kg_y_at_f04':dep*179+gross*50-1000*ret*.4 if both else None,
                    'included_delta_electric_MWh':dep if both else None,
                    'capture_chain_burden_SCENARIO_kg_t':50,'electricity_EF_SCENARIO_kg_MWh':179,
                    'status':'Conditional within sourceA power-anchor surrogate; not full LCA. Infeasible thresholds undefined, not zero.'})
    with (ROOT/'results/physical_service_annual_ledger_r32_20261002.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    groups={}
    with (ROOT/'datasets/scaled_heat_proxy_profiles_5regions_20260929.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):groups.setdefault(r['shape_region'],[]).append(float(r['proxy_heat_mwh']))
    outages=[]
    for region,shape in groups.items():
        d=np.asarray(shape);d=d/d.mean()*37.3*.2
        start=int(np.argmax(np.convolve(d,np.ones(168),'valid')))
        avail=np.ones(len(d));avail[start:start+168]=0
        for capture in [False,True]:
            r=lp.solve(d,100,60,capture,True,0,availability=avail,
                usable_capacity_MWh=2037.75,store_power_MW=288,tank_hot_C=99,tank_approach_K=2,
                charge_efficiency=1,discharge_efficiency=1,weekly_loss=1-(1-.0006)**7,
                auxiliary_fraction=.002,flow_limit_kg_s=450,steam_grade_override_C=390,compressor_grade_override_C=158)
            r.update(proxy=region,outage_start_hour_SCENARIO=start,
                     outage_heat_demand_MWh=float(d[start:start+168].sum()),
                     interpretation='Common incinerator/capture heat outage at highest-load168h;97C tank cannot deliver100C primary without an independent available booster. No claim of observed outage timing.')
            outages.append(r)
    vals=[r['fossil_threshold_IF_ADMISSIBLE'] for r in out if r['both_NECESSARY_pass']]
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),admissible_pairs=len(vals),
      threshold_range= [min(vals),max(vals)],undefined_infeasible_pairs=sum(not r['both_NECESSARY_pass'] for r in out),
      outage_LPs=len(outages),outage_tests=outages,
      max_outage_eq_error=max(r['max_eq_error'] for r in outages),
      positive_knowledge='Finite storage supports some load-shape pairs; climate thresholds exist only after service admission. Planned outage/grade tests identify need for an independent certified booster or alternative firm source, not invisible backup.',
      ledger_boundary='SourceA8.12/6.17MWe differential anchors, constant per operating hour, actual selected HP/store pumping. Not reconstructed steam off-design power and not annual firm performance.')
    (ROOT/'results/physical_service_annual_ledger_qc_r32_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='outage_tests'},indent=2))
if __name__=='__main__':main()
