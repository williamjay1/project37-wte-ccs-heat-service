"""Re-run prior service matrix with coherent IF97 cold-water properties.

Legacy results remain untouched. Tests whether the main exclusions/ranking
survive the reviewer-identified constant-cp approximation; not plant validation.
"""
from pathlib import Path
from datetime import datetime,timezone
import csv,json,sys,importlib.util
import numpy as np
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cache/python_packages_r32'))
from iapws import IAPWS97
from physical_service_feasibility_r32_20261002 import solve
from physical_service_volume_flow_r32_20261002 import stores

def water(T):return IAPWS97(P=1,T=T+273.15).h/1000
def write_csv(path,rows):
 with path.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
 groups={}
 with (ROOT/'datasets/scaled_heat_proxy_profiles_5regions_20260929.csv').open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):groups.setdefault(r['shape_region'],[]).append(float(r['proxy_heat_mwh']))
 rows=[];templates=[s for s in stores() if s['volume_m3'] in [0,50000]]
 for region,a in groups.items():
  shape=np.asarray(a)/np.mean(a)
  for duty in [.2,.3]:
   demand=37.3*duty*shape
   for ts in [100,120]:
    for s in templates:
     for cascade in [False,True]:
      for capture in [False,True]:
       r=solve(demand,ts,60,capture,cascade,0,tank_hot_C=s['hot_C'],tank_approach_K=s['hot_C']-s['service_C'],
        usable_capacity_MWh=.9*1000*s['volume_m3']*(water(s['hot_C'])-water(60))/3600,
        store_power_MW=s['rate_MW'],flow_limit_kg_s=450,
        weekly_loss=1-(1-s['loss_daily'])**7,charge_efficiency=1,discharge_efficiency=1,
        steam_grade_override_C=390,compressor_grade_override_C=158,auxiliary_fraction=s['aux'],water_property_model='IF97_10bar')
       r.update(proxy=region,mean_duty_ratio_SCENARIO=duty,tank=s['name'],water_property='IF97_10bar')
       rows.append(r)
       if len(rows)%16==0:print(f'exact property {len(rows)}/160',flush=True)
 out=ROOT/'results/exact_water_annual_r35_20261002.csv';write_csv(out,rows)
 old=list(csv.DictReader((ROOT/'results/physical_service_annual_matrix_r32_20261002.csv').open(encoding='utf-8')))
 keys=['proxy','mean_duty_ratio_SCENARIO','supply_temperature_C','tank','model','capture_on']
 changed=[]
 for r in rows:
  z=next(z for z in old if all(str(z[k])==str(r[k]) for k in keys))
  if (z['service_feasible']=='True')!=r['service_feasible']:
   changed.append(dict(**{k:r[k] for k in keys},old_unmet_MWh=float(z['unserved_MWh']),IF97_unmet_MWh=r['unserved_MWh']))
 pairs=[]
 for r in rows:
  if r['capture_on'] or r['model']!='temperature_cascade':continue
  c=next(z for z in rows if z['capture_on'] and z['model']==r['model'] and all(z[k]==r[k] for k in keys[:4]))
  a=next(z for z in rows if z['capture_on'] and z['model']=='aggregate_heat' and all(z[k]==r[k] for k in keys[:4]))
  pairs.append(dict(**{k:r[k] for k in keys[:4]},paired_pass=bool(r['service_feasible'] and c['service_feasible']),
   aggregate_false_pass=bool(r['service_feasible'] and a['service_feasible'] and not c['service_feasible']),
   base_unmet_MWh=r['unserved_MWh'],CCS_unmet_MWh=c['unserved_MWh']))
 write_csv(ROOT/'results/exact_water_paired_r35_20261002.csv',pairs)
 #Exact enthalpy version of the headline two-group necessary window.
 #At the binding77C HP cut, H+overhead+compressor=25.4MW;11.1MW
 #must be supplied below77C.91C is a different, nonbinding grade cut.
 hmax=water(60)+36.5/11.1*(water(77)-water(60))
 Tmax=brentq(lambda T:water(T)-hmax,77,160)
 Tmin=brentq(lambda T:water(T)-water(60)-36.5/150,60,160)
 assert Tmin>Tmax
 HP=9.8*5.5/4.5
 def sources(x):return [('H',37.3-18.8*x,390),('overhead',5.3*x,91),('compressor',1.6*x,158),('HP',HP*x,77)]
 uf=(water(120)-water(77))/(water(120)-water(60))
 x=(37.3-36.5*uf)/(18.8-5.3-1.6)
 designs={}
 scale95=(38-19.9)/(5.3+1.6+HP)
 source95=[('H',19.9,390),('overhead',5.3*scale95,91),('compressor',1.6*scale95,158),('HP',HP*scale95,77)]
 for name,ts,flow,frac,ss in [('bypass',120,150,x,sources(x)),('adapted',100,450,1,sources(1)),('95design',120,150,.95,source95),('full99_original',120,150,1,sources(1))]:
  r=solve(np.full(168,36.5),ts,60,True,True,0,flow_limit_kg_s=flow,sources_override=ss,auxiliary_fraction=0,return_dispatch=True,water_property_model='IF97_10bar')
  dispatch=r.pop('_dispatch');hp=float(np.mean(dispatch['HP']))
  basepower=6.25 if name=='95design' else 8.12-1.95*frac
  r.update(HP_MW=hp,surrogate_power_MW=basepower-hp/5.5,capture_fraction=.95 if name=='95design' else .9972*frac)
  designs[name]=r
 assert all(designs[k]['service_feasible'] for k in ['bypass','adapted','95design'])
 assert not designs['full99_original']['service_feasible']
 central={}
 for comp in ['bypass','95design']:
  old0=designs[comp];new=designs['adapted']
  dc=5.168*3.6*(new['capture_fraction']-old0['capture_fraction']);ret=dc*.99*.995
  dw=old0['surrogate_power_MW']-new['surrogate_power_MW']
  central[comp]=dict(extra_capture_t_y=dc*8000,extra_retained_fossil_t_y=ret*.4*8000,
   extra_electric_MWh_y=dw*8000,fossil_threshold=(dw*179+dc*50)/(1000*ret),
   climate_kg_y=(dw*179+dc*50-1000*ret*.4)*8000,
   pre_capital_adaptation_ceiling_EUR2020_y=(300*ret*.4-70*dw-50*dc)*8000)
 report=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS executed exact-water robustness audit',LPs=len(rows),pairs=len(pairs),
  paired_passes=sum(r['paired_pass'] for r in pairs),aggregate_false_passes=sum(r['aggregate_false_pass'] for r in pairs),
  changed_service_classifications=changed,headline_exact_Tmax_C=Tmax,headline_exact_Tmin_C=Tmin,
  bypass_train_fraction=x,designs=designs,central_exact=central,
  max_eq_error=max(r['max_eq_error'] for r in rows),
  limits='Exact10bar water enthalpy removes constant-cp approximation only. Recovery rectangles, offdesign bypass, hot composites and proportional tank loss remain structural assumptions; passes not hardware certification.')
 (ROOT/'results/exact_water_comparison_qc_r35_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='designs'},indent=2))
if __name__=='__main__':main()
