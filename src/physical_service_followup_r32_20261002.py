"""Exploratory small-store and joint-feed transfer checks after base matrix.
Not pre-registered, not a modeled EU retrofit fleet or observed feed dynamics.
"""
from pathlib import Path
from datetime import datetime,timezone
import csv,json,importlib.util
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('lp',ROOT/'src/physical_service_feasibility_r32_20261002.py')
lp=importlib.util.module_from_spec(s);s.loader.exec_module(lp)
def ceiling(ss,ts,flow,tr=60):
    vals=[sum(q for k,q,t in ss),flow*.00418*(ts-tr)]
    for theta in {t for k,q,t in ss if t<ts}:
        a=np.clip((theta-tr)/(ts-tr),0,1)
        vals.append(sum(q for k,q,t in ss if t>theta)/(1-a))
    return min(vals)
def main():
    groups={}
    with (ROOT/'datasets/scaled_heat_proxy_profiles_5regions_20260929.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):groups.setdefault(r['shape_region'],[]).append(float(r['proxy_heat_mwh']))
    small=[]
    for name in ['Oberland','Porto metropolitan area']:
      a=np.asarray(groups[name]);a=a/a.mean()*37.3*.3
      for ts in [100,120]:
       for cascade in [False,True]:
        for capture in [False,True]:
          r=lp.solve(a,ts,60,capture,cascade,0,usable_capacity_MWh=203.775,
            store_power_MW=29,tank_hot_C=99,tank_approach_K=2,charge_efficiency=1,discharge_efficiency=1,
            weekly_loss=1-(1-.0015)**7,auxiliary_fraction=.004,flow_limit_kg_s=450,
            steam_grade_override_C=390,compressor_grade_override_C=158)
          r.update(proxy=name,followup='Exploratory5000m3after160LPbase matrix; same.3mean duty')
          small.append(r)
    with (ROOT/'results/physical_service_followup_smallstore_r32_20261002.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(small[0]));w.writeheader();w.writerows(small)
    source=ROOT/'datasets/joint_feed_transition_properties_20260930.csv'
    if not source.exists():source=ROOT/'results/joint_feed_transition_properties_20260930.csv'
    data=list(csv.DictReader(source.open(encoding='utf-8')))
    data=[r for r in data if r['feed_mode']=='bulk_extensive_interpolation']
    first=data[0];feed=[]
    for r in data:
        yM=float(r['inc_flow_over_initial'])
        yE=yM*float(r['lhv_gj_per_t'])/float(first['lhv_gj_per_t'])
        yC=yM*float(r['gross_co2_t_per_t'])/float(first['gross_co2_t_per_t'])
        for d in [30,36.5]:
          for ts in [100,120]:
            for flow in [150,450]:
              ss0=[('H',37.3*yE,390)]
              ss1=[('H',max(0,37.3*yE-18.8*yC),390),('OH',5.3*yC,91),('comp',1.6*yC,158),('HP',9.8*5.5/4.5*yC,77)]
              q0=ceiling(ss0,ts,flow);q1=ceiling(ss1,ts,flow)
              ok=bool(d<=min(q0,q1)+1e-9)
              feed.append(dict(alpha_SCENARIO=float(r['transition_coordinate']),energy_input_ratio_SCENARIO=yE,
                carbon_input_ratio_SCENARIO=yC,fossil_share_INPUT=float(r['fossil_share']),load_MW_SCENARIO=d,
                primary_Ts_C=ts,flow_limit_kg_s_SCENARIO=flow,noCCS_max_MW_NECESSARY=q0,CCS_max_MW_NECESSARY=q1,
                paired_gate_pass=ok,
                interpretation='Joint UBA feed/flow transferred to sourceA via energy/carbon proportional scaling, held pressures/temperatures. Unvalidated off-design source transfer, not EU-fleet emissions or process forecast.'))
    with (ROOT/'results/physical_service_followup_feed_r32_20261002.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(feed[0]));w.writeheader();w.writerows(feed)
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),smallstore_LPs=len(small),smallstore_rows=small,
      feed_scenarios=len(feed),endpoint_rows=[r for r in feed if r['alpha_SCENARIO'] in [0,1]],
      classification='Exploratory follow-up; proportional energy/carbon transfer is a structural scenario, not a validated plant feed response.')
    (ROOT/'results/physical_service_followup_qc_r32_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['smallstore_rows','endpoint_rows']},indent=2))
    print('Small-store120C:',[(r['proxy'],r['capture_on'],r['model'],r['unserved_MWh']) for r in small if r['supply_temperature_C']==120])
    print('Endpoint ratios:',feed[-1])
if __name__=='__main__':main()
