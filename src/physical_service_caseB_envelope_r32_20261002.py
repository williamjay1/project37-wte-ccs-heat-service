"""Otgonbayar printed steam model + conditional heat-temperature envelopes.

SourceB=independent published steam topology, Switzerland(non-EU). Unknown
hours/internal duties/heat grades are structural scenarios. PZ actual reboiler
temperature is absent: feasible envelopes are CONDITIONAL on its pinch.
Net-power differences do not fit or reproduce absolute published net power.
"""
from pathlib import Path
from datetime import datetime,timezone
import csv,json,importlib.util
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'src'/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
steam=module('steam','physical_service_caseB_check_r32_20261002.py')
lp=module('lp','physical_service_feasibility_r32_20261002.py')
def heat_limit(c,hours,cap,qi):
    s0=steam.state(c,hours,cap,0,qi,True)
    s1=steam.state(c,hours,cap,1,qi,True)
    caps=[]
    for k,floor in [('mLP',c['minLP']),('mIP',0),('qFW_MW',0)]:
        slope=s1[k]-s0[k]
        if slope<0:caps.append((s0[k]-floor)/(-slope))
        elif s0[k]<floor:raise ValueError('Cycle infeasible even without DH')
    return max(0,min(caps))
def main():
    rows=[];steam_cases=[];pinch=[]
    for c in steam.CASES:
      for hours in [8000,8760]:
       for qi in [0,3.4]:
        for cap in [0,.99]:
          lim=heat_limit(c,hours,cap,qi)
          s0=steam.state(c,hours,cap,0,qi,True)
          sx=steam.state(c,hours,cap,lim,qi,True)
          assert sx['mLP']>=c['minLP']-1e-8 and sx['mIP']>=-1e-8 and sx['qFW_MW']>=-1e-8
          assert abs(sx['mass_error'])<1e-10
          slope=steam.state(c,hours,cap,1,qi,True)['W_before_missing_internal_electric_MW']-s0['W_before_missing_internal_electric_MW']
          assert slope<=1e-8
          steam_cases.append(dict(case=c['case'],hours_SCENARIO=hours,internal_heat_SCENARIO=qi,capture=cap,
              steam_DH_limit_MW=lim,mLP_at_limit=sx['mLP'],minimum_mLP_SOURCE=c['minLP'],
              steam_power_cost_MW_per_MWheat=-slope,mass_error=sx['mass_error']))
          for treboiler in [125,135,145]:
           for approach in [5,10]:
            pinch.append(dict(case=c['case'],capture=cap,Treb_SCENARIO_C=treboiler,pinch_SCENARIO_K=approach,
              steam_SOURCE_C=s0['CCS_steam_T_C'],reboiler_gate_pass=cap==0 or s0['CCS_steam_T_C']-treboiler>=approach,
              interpretation='Conditional temperature test: optimized PZ temperature is not published; not measured operating rejection.'))
          for eta_low in [0,.25,.5]:
           for ts in [100,120]:
            for volume in [0,5000]:
             for cascade in [False,True]:
              cop=5.5
              #25% direct recovery is SOURCE assumption at about100C.
              # eta_low is a separate explicit fraction of qCCS recoverable at
              #40-60C; no overlap:eta_low+0.25<=1. Optimistic hot output100C.
              qhot=eta_low*s0['qCCS_MW']*cop/(cop-1)
              ss=[('H',lim,c['TLP']-5),('overhead',.25*s0['qCCS_MW'],100),
                  ('compressor',0,100),('HP',qhot,100)]
              d=np.full(168,c['qdh'])
              r=lp.solve(d,ts,c['TR'],cap>0,cascade,0,sources_override=ss,heatpump_COP=cop,
                  source_electric_costs={'H':-slope},return_dispatch=True,
                  usable_capacity_MWh=.9*1000*volume*.00418*(99-c['TR'])/3600,
                  store_power_MW=29 if volume else 0,tank_hot_C=99,tank_approach_K=2,
                  charge_efficiency=1,discharge_efficiency=1,weekly_loss=1-(1-.0015)**7,
                  auxiliary_fraction=.004 if volume else 0,flow_limit_kg_s=450)
              z=r.pop('_dispatch');qsteam=z['H']+z['chargeH']
              w=s0['W_before_missing_internal_electric_MW']+slope*qsteam-z['HP']/cop
              r.update(case=c['case'],hours_SCENARIO=hours,internal_heat_SCENARIO_MW=qi,
                  low_grade_fraction_SCENARIO=eta_low,volume_m3=volume,capture_fraction=cap,
                  steam_DH_limit_MW=lim,steam_thermal_output_mean_MW=float(qsteam.mean()),
                  net_power_before_missing_internal_electric_mean_MW=float(w.mean()),
                  steam_power_cost_MW_per_MWheat=-slope,
                  boundary='Conditional on unknown reboiler pinch, low-grade recovery and hourly availability. Printed steam equations; no absolute field-power validation.')
              rows.append(r)
    out=ROOT/'results/physical_service_caseB_envelope_r32_20261002.csv'
    with out.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    flags=[];keys=['case','hours_SCENARIO','internal_heat_SCENARIO_MW','low_grade_fraction_SCENARIO','volume_m3','supply_temperature_C']
    for r in rows:
        if r['capture_fraction']==0 or r['model']!='aggregate_heat':continue
        same=lambda x:all(x[k]==r[k] for k in keys)
        ca=next(x for x in rows if same(x) and x['capture_fraction']==.99 and x['model']=='temperature_cascade')
        base=next(x for x in rows if same(x) and x['capture_fraction']==0 and x['model']=='temperature_cascade')
        if base['service_feasible'] and r['service_feasible'] and not ca['service_feasible']:
            flags.append({**{k:r[k] for k in keys},'CCS_unmet_MWh':ca['unserved_MWh']})
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),LPs=len(rows),steam_cases=steam_cases,
      conditional_reboiler_checks=pinch,aggregate_false_passes_with_base_pass=flags,
      sourceB_120C_base_failures=sum(not r['service_feasible'] for r in rows if r['case']=='Hagenholz_2027' and r['capture_fraction']==0 and r['supply_temperature_C']==120 and r['model']=='temperature_cascade'),
      max_mass_error=max(abs(x['mass_error']) for x in steam_cases),max_eq_error=max(r['max_eq_error'] for r in rows),
      solver_seconds=sum(r['solver_seconds'] for r in rows),
      interpretation='Second-source steam-domain transfer checks, not independent full plant reproduction or certified hardware. H120C failure also affects noCCS: exclude BOTH, do not attribute its topology limit to CCS.',
      status='Computed and checked conditional sourceB envelope; full two-case reproduction gate remains open.')
    (ROOT/'results/physical_service_caseB_envelope_qc_r32_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['conditional_reboiler_checks','steam_cases','aggregate_false_passes_with_base_pass']},indent=2))
    print('Steam limits:',steam_cases)
if __name__=='__main__':main()
