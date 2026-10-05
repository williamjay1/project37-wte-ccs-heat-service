"""Exact-water small-tank/feed and complete adaptation-ledger consistency."""
from pathlib import Path
from datetime import datetime,timezone
import csv,json,numpy as np
from exact_water_comparison_r35_20261002 import water,write_csv
from physical_service_feasibility_r32_20261002 import solve
ROOT=Path(__file__).resolve().parents[1]

def ceiling(ss,ts,flow):
 vals=[sum(q for k,q,t in ss),flow*(water(ts)-water(60))]
 for theta in {t for k,q,t in ss if t<ts}:
  a=max(0,(water(theta)-water(60))/(water(ts)-water(60)))
  vals.append(sum(q for k,q,t in ss if t>theta)/(1-a))
 return min(vals)

def main():
 groups={}
 with (ROOT/'datasets/scaled_heat_proxy_profiles_5regions_20260929.csv').open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):groups.setdefault(r['shape_region'],[]).append(float(r['proxy_heat_mwh']))
 small=[]
 for name in ['Oberland','Porto metropolitan area']:
  d=np.array(groups[name]);d=d/d.mean()*37.3*.3
  for capture,cascade in [(False,True),(True,False),(True,True)]:
   r=solve(d,120,60,capture,cascade,0,usable_capacity_MWh=.9*1000*5000*(water(99)-water(60))/3600,
    store_power_MW=29,tank_hot_C=99,tank_approach_K=2,charge_efficiency=1,discharge_efficiency=1,
    weekly_loss=1-(1-.0015)**7,auxiliary_fraction=.004,flow_limit_kg_s=450,
    steam_grade_override_C=390,compressor_grade_override_C=158,water_property_model='IF97_10bar')
   r.update(proxy=name,volume_m3=5000,followup='Coherent IF97 correction of prior exploratory case')
   small.append(r)
 write_csv(ROOT/'results/exact_water_smallstore_r35_20261002.csv',small)
 feed=[]
 with (ROOT/'datasets/joint_feed_transition_properties_20260930.csv').open(encoding='utf-8') as f:data=[r for r in csv.DictReader(f) if r['feed_mode']=='bulk_extensive_interpolation']
 first=data[0]
 for r in data:
  yM=float(r['inc_flow_over_initial']);yE=yM*float(r['lhv_gj_per_t'])/float(first['lhv_gj_per_t']);yC=yM*float(r['gross_co2_t_per_t'])/float(first['gross_co2_t_per_t'])
  for D in [30,36.5]:
   for ts in [100,120]:
    for flow in [150,450]:
     ss0=[('H',37.3*yE,390)];ss1=[('H',max(0,37.3*yE-18.8*yC),390),('OH',5.3*yC,91),('comp',1.6*yC,158),('HP',9.8*5.5/4.5*yC,77)]
     q0=ceiling(ss0,ts,flow);q1=ceiling(ss1,ts,flow)
     feed.append(dict(alpha_SCENARIO=float(r['transition_coordinate']),load_MW_SCENARIO=D,primary_Ts_C=ts,flow_limit_kg_s_SCENARIO=flow,
      noCCS_max_MW_NECESSARY=q0,CCS_max_MW_NECESSARY=q1,paired_gate_pass=bool(D<=min(q0,q1)+1e-9)))
 write_csv(ROOT/'results/exact_water_feed_r35_20261002.csv',feed)
 qc=json.loads((ROOT/'results/exact_water_comparison_qc_r35_20261002.json').read_text())
 designs=qc['designs'];rows=[]
 for label,oldname in [('same99_train_bypass','bypass'),('published95_design','95design')]:
  old,new=designs[oldname],designs['adapted']
  dc=5.168*3.6*(new['capture_fraction']-old['capture_fraction']);ret=dc*.99*.995
  base_dw=old['surrogate_power_MW']-new['surrogate_power_MW']
  for hours in [8000,8760]:
   for ef in [179,429,700]:
    for b in [0,50,100]:
     for pumping in [0,.1,.5]:
      dw=base_dw+pumping;fstar=(dw*ef+dc*b)/(1000*ret)
      for fossil in [.4,.4679]:
       for pe in [40,70,120]:
        for Vf in [0,100,300,500]:
         rows.append(dict(comparator=label,hours_SCENARIO=hours,electricity_EF_kg_MWh_SCENARIO=ef,incremental_chain_burden_kg_t_SCENARIO=b,
          incremental_network_pumping_MW_SCENARIO=pumping,fossil_share_SCENARIO=fossil,electricity_price_EUR_MWh_SCENARIO=pe,effective_fossil_value_EUR_t_SCENARIO=Vf,
          marginal_climate_fossil_share_threshold=fstar,incremental_GWP_kg_y=(dw*ef+dc*b-1000*ret*fossil)*hours,
          maximum_included_annual_adaptation_cost_EUR_y=(Vf*ret*fossil-pe*dw-50*dc)*hours,
          extra_capture_t_y=dc*hours,extra_retained_fossil_t_y=ret*fossil*hours,
          boundary='IF9710bar service ledger; same unvalidated offdesign/power/price assumptions; no project profit or hardware certificate.'))
 assert len(rows)==2592
 write_csv(ROOT/'results/exact_water_adaptation_r35_20261002.csv',rows)
 #Separate numerical reconstruction of all cost and climate rows, including
 #dimensional retained/captured relationships; no nominal probability.
 error=0
 for r in rows:
  c=r['extra_capture_t_y'];rf=r['extra_retained_fossil_t_y'];hours=r['hours_SCENARIO'];ret_total=c*.99*.995
  e=(r['marginal_climate_fossil_share_threshold']*1000*ret_total-c*r['incremental_chain_burden_kg_t_SCENARIO'])/r['electricity_EF_kg_MWh_SCENARIO']
  g=e*r['electricity_EF_kg_MWh_SCENARIO']+c*r['incremental_chain_burden_kg_t_SCENARIO']-1000*rf
  k=r['effective_fossil_value_EUR_t_SCENARIO']*rf-r['electricity_price_EUR_MWh_SCENARIO']*e-50*c
  error=max(error,abs(g-r['incremental_GWP_kg_y'])/max(1,abs(g)),abs(k-r['maximum_included_annual_adaptation_cost_EUR_y'])/max(1,abs(k)))
 assert error<1e-10
 #Rebuild matched annual climate ledger directly from the exact-water runs.
 with (ROOT/'results/exact_water_annual_r35_20261002.csv').open(encoding='utf-8') as f: annual=list(csv.DictReader(f))
 keys=['proxy','mean_duty_ratio_SCENARIO','supply_temperature_C','tank'];annualledger=[]
 for r in annual:
  if r['capture_on']!='False' or r['model']!='temperature_cascade':continue
  c=next(x for x in annual if all(x[k]==r[k] for k in keys) and x['capture_on']=='True' and x['model']=='temperature_cascade')
  paired=r['service_feasible']=='True' and c['service_feasible']=='True';C=5.168*3.6*.9972*8784;retC=C*.99*.995
  W=1.95*8784+float(c['heatpump_electric_MWh'])+float(c['store_auxiliary_electric_MWh'])-float(r['store_auxiliary_electric_MWh'])
  annualledger.append(dict(**{k:r[k] for k in keys},both_NECESSARY_pass=paired,fossil_threshold_IF_ADMISSIBLE=(W*179+C*50)/(1000*retC) if paired else None,
   included_GWP_kg_y_at_f04=W*179+C*50-1000*retC*.4 if paired else None,included_delta_electric_MWh=W if paired else None))
 write_csv(ROOT/'results/exact_water_annual_ledger_r35_20261002.csv',annualledger)
 vals=[r['fossil_threshold_IF_ADMISSIBLE'] for r in annualledger if r['both_NECESSARY_pass']]
 assert len(vals)==27 and len(annualledger)==40
 report=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS exact-water followups and complete ledger algebra',smallstore_LPs=len(small),smallstore=small,
  feed_rows=len(feed),endpoint_rows=[r for r in feed if r['alpha_SCENARIO'] in [0,1]],adaptation_rows=len(rows),max_ledger_relative_error=error,
  exact_annual_threshold_range=[min(vals),max(vals)],exact_annual_undefined_pairs=13,
  limits='Same source rectangles and bypass surrogate. Neither exact water properties nor source-year evidence certifies factory operation or full LCA/TEA.')
 (ROOT/'results/exact_water_followup_qc_r35_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in ['smallstore','endpoint_rows']},indent=2))
 print('Smallstore:',[(r['proxy'],r['capture_on'],r['unserved_MWh']) for r in small])
if __name__=='__main__':main()
