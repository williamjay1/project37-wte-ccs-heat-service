"""Observed export-shaped monthly necessary cuts, not factory validation.

Each complete operator year supplies a normalized MONTHLY sales shape, not
hourly customer demand. Tested annual means, temperatures, availability,
heat recovery, hydraulic limits and tank sizes are explicit scenarios.
The cut is necessary for every finer schedule satisfying those monthly totals.
It is an optimistic lossless outer bound for the specified steam/direct-recovery
route WITHOUT low-grade heat-pump, booster or external source. It never
certifies service or excludes a different heat-pump configuration.
"""
from pathlib import Path
from datetime import datetime, timezone
import csv, json, hashlib, sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cache/python_packages_r32'))
from iapws import IAPWS97
from physical_service_caseB_check_r32_20261002 import CASES, state, h, hr
from physical_service_caseB_envelope_r32_20261002 import heat_limit
from steam_phase_domain_r33_20261002 import cold_upper_fraction,water_h

DATA=ROOT/'datasets/hagenholz_monthly_clean_r35_20261002.csv'

def block_bound(hours, shape, capacity_MW, buffer_MWh):
 """min_I (capacity*duration+initial usable stock)/(unit-mean heat in I).

 Full-year cut uses ZERO initial-stock allowance because storage is cyclic.
 Shorter circular blocks get at most one full buffer, regardless of power.
 Perfect efficiency/no losses/unlimited charging are optimistic relaxations.
 """
 best=(float('inf'),None)
 for length in range(1,13):
  for start in range(12 if length<12 else 1):
   ids=[(start+i)%12 for i in range(length)]
   duration=float(sum(hours[i] for i in ids)); unit=float(sum(hours[i]*shape[i] for i in ids))
   capacity=np.broadcast_to(np.asarray(capacity_MW,dtype=float),hours.shape)
   numerator=float(sum(capacity[i]*hours[i] for i in ids))+(buffer_MWh if length<12 else 0)
   value=numerator/unit
   if value<best[0]:best=(value,dict(start_month=start+1,months=length,duration_hours=duration,unit_mean_heat_MWh=unit))
 return best

def main():
 with DATA.open(encoding='utf-8',newline='') as handle: raw=list(csv.DictReader(handle))
 years=sorted({int(r['year']) for r in raw if int(r['year'])<=2025})
 rows=[]
 c=CASES[0] #prospective2027 topology, NOT the observed2020-2025 configuration
 for year in years:
  records=[r for r in raw if int(r['year'])==year];assert len(records)==12
  hours=np.array([float(r['calendar_hours']) for r in records])
  sales=np.array([float(r['heat_sales_MWh']) for r in records])
  observed_mean=sales.sum()/hours.sum();shape=sales/hours/observed_mean
  assert abs(float((shape*hours).sum()/hours.sum())-1)<1e-12
  waste=np.array([float(r['waste_t']) for r in records])
  for feed in ['constant_annual_rate','observed_monthly_throughput_shape']:
   #The375kt prospective feed is rescaled using observed monthly fractions;
   #these are NOT2027 observations or actual operating hours. Monthly feed
   #intensity is still fixed within each monthly block, not hourly dispatch.
   equivalent_hours=np.full(12,float(hours.sum())) if feed=='constant_annual_rate' else waste.sum()*hours/waste
   for qi in [0,3.4]:
    for capture in [0,.99]:
     H=np.array([heat_limit(c,float(eh),capture,qi) for eh in equivalent_hours])
     overhead=np.array([.25*state(c,float(eh),capture,0,qi,True)['qCCS_MW'] for eh in equivalent_hours])
     append_contract_rows(rows,c,year,hours,shape,observed_mean,feed,qi,capture,H,overhead)
 save_and_summarize(rows,years)

def append_contract_rows(rows,c,year,hours,shape,observed_mean,feed,qi,capture,H,overhead):
    vap=IAPWS97(P=c['PLP']/10,x=1)
    rho=max(0,h(c['PLP'],c['TLP'])-vap.h/1000)/(h(c['PLP'],c['TLP'])-hr(c['TR']))
    for ts in [95,100]:
     tr=55;theta=vap.T-273.15-5
     fraction=max(0,cold_upper_fraction(ts,tr,theta)) if ts>theta else 0
     for volume in [0,5000]:
      #DEA finite tank coordinate:99C hot/55C return,90% useful volume.
      #97C delivered grade: it cannot supply the upper interval >theta~99.78.
      buffer=.9*1000*volume*(water_h(99)-water_h(tr))/3600
      for phase in [False,True]:
       total,total_block=block_bound(hours,shape,H+overhead,buffer)
       flow=450*(water_h(ts)-water_h(tr))/float(shape.max())
       upper=float('inf');upper_block=None
       if phase and fraction>0:
        upper,upper_block=block_bound(hours,shape,(H*rho+overhead)/fraction,0)
       #Water-side branch splitting and heat recovery cannot exceed total
       #duty; upper heat is bounded additionally. Tank power/loss/availability
       #may tighten further, never improve these necessary ceilings.
       ceiling=min(total,flow,upper)
       active='total_energy' if ceiling==total else ('hydraulic_peak' if ceiling==flow else 'phase_upper_heat')
       rows.append(dict(year=year,feed_timing_SCENARIO=feed,internal_heat_SCENARIO_MW=qi,capture_fraction=capture,
        supply_SCENARIO_C=ts,return_SCENARIO_C=tr,volume_SCENARIO_m3=volume,
        thermal_model='condensation_cut' if phase else 'rectangular_inlet_grade',
        source_hours_SCENARIO=float(hours.sum()),steam_limit_MW=float(np.dot(H,hours)/hours.sum()),recovery_25pct_ASSUMED_MW=float(np.dot(overhead,hours)/hours.sum()),
        monthly_total_source_MW_JSON=json.dumps((H+overhead).tolist()),
        monthly_upper_source_MW_JSON=json.dumps((H*rho+overhead).tolist()),
        saturation_C=vap.T-273.15,steam_superheat_fraction=rho,upper_interval_fraction=fraction,
        LP_pressure_SOURCE_bar=c['PLP'],LP_temperature_SOURCE_C=c['TLP'],approach_SCENARIO_K=5,water_side_pressure_SCENARIO_bar=10,
        tank_usable_energy_MWh=buffer,total_energy_mean_ceiling_MW=total,
        hydraulic_mean_ceiling_MW=flow,phase_mean_ceiling_MW=None if not np.isfinite(upper) else upper,
        necessary_mean_service_ceiling_MW=ceiling,active_cut=active,
        active_total_block_start_month=total_block['start_month'],active_total_block_months=total_block['months'],
        pass_reference_mean64_4_NECESSARY=64.4<=ceiling+1e-8,
        observed_export_mean_MW=observed_mean,observed_peak_month_to_mean=float(shape.max()),
        evidence='Observed2020-2025 normalized monthly SALES shape; prospective2027 steam plus25pct direct-recovery route WITHOUT low-grade HP/booster/external source. Temperature/internal duties SCENARIOS. Necessary upper bound, not sufficiency, hourly demand or net-power validation.'))
def save_and_summarize(rows,years):
 out=ROOT/'results/swiss_monthly_service_cuts_r35_20261002.csv'
 with out.open('w',encoding='utf-8',newline='') as handle:
  w=csv.DictWriter(handle,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 keys=['year','feed_timing_SCENARIO','internal_heat_SCENARIO_MW','capture_fraction','supply_SCENARIO_C','volume_SCENARIO_m3']
 tightening=[]
 for r in rows:
  if r['thermal_model']!='rectangular_inlet_grade':continue
  p=next(x for x in rows if x['thermal_model']=='condensation_cut' and all(x[k]==r[k] for k in keys))
  if p['necessary_mean_service_ceiling_MW']<r['necessary_mean_service_ceiling_MW']-1e-8:
   tightening.append(dict(**{k:r[k] for k in keys},rectangular=r['necessary_mean_service_ceiling_MW'],
                         phase=p['necessary_mean_service_ceiling_MW']))
 storage=[]
 for r in rows:
  if r['volume_SCENARIO_m3']!=5000 or r['thermal_model']!='condensation_cut':continue
  p=next(x for x in rows if x['volume_SCENARIO_m3']==0 and x['thermal_model']==r['thermal_model'] and all(x[k]==r[k] for k in keys if k!='volume_SCENARIO_m3'))
  gain=r['necessary_mean_service_ceiling_MW']-p['necessary_mean_service_ceiling_MW'];assert gain>=-1e-8
  storage.append(gain)
 assert len(rows)==384 and len(years)==6
 #Official2019 separate boundary ledger, Table2 row28, PDFp6. Source LHV
 #method p26 uses fresh-steam energy, so it is NOT an independent steam target.
 official=dict(waste_t=244879,LHV_standard_GJ_t=11.83,boiler_input_MWh=804472,
  boiler_efficiency=.843,heat_exports_MWh=450052,electric_exports_MWh=103211,
  internal_heat_MWh=4265,internal_electric_MWh=23297,generator_MWh=126349,
  imported_electric_MWh=159)
 closure=official['generator_MWh']+official['imported_electric_MWh']-official['internal_electric_MWh']-official['electric_exports_MWh']
 assert closure==0
 #Power/heat target ratios are diagnostic equivalent time bases, NOT observed
 #operating hours or model inputs. No computed target-time ratio enters cuts.
 report=dict(created_utc=datetime.now(timezone.utc).isoformat(),rows=len(rows),shape_year_units=years,
  monthly_raw_sha256='fae845b7ecf2a5fd6e78ef9be453e0b99491e73a925c2b036bf1bdaa67546966',
  processed_sha256=hashlib.sha256(DATA.read_bytes()).hexdigest(),tightening=tightening,
  max_5000m3_necessary_mean_ceiling_gain_MW=max(storage),min_storage_gain_MW=min(storage),
  reference_mean64_4_not_excluded_by_screen={model:{feed:int(sum(r['pass_reference_mean64_4_NECESSARY'] for r in rows if r['thermal_model']==model and r['feed_timing_SCENARIO']==feed)) for feed in ['constant_annual_rate','observed_monthly_throughput_shape']} for model in ['rectangular_inlet_grade','condensation_cut']},
  ceiling_range_MW=[min(r['necessary_mean_service_ceiling_MW'] for r in rows),max(r['necessary_mean_service_ceiling_MW'] for r in rows)],
  official2019=official,official_electric_closure_MWh=closure,
  official2019_method='LHV uses measured fresh-steam energy (PDFp26); boiler/input/steam validation would be circular without separate fuel calorimetry. Operating hours not supplied.',
  official2019_LHV_rounding_residual_MWh=official['waste_t']*official['LHV_standard_GJ_t']/3.6-official['boiler_input_MWh'],
  independent_case_reproduction='Su power-only / Swiss2019 complete input states absent. No full two-case power reproduction; prior authors benchmarks remain distinct.',
  source_state_warning='Nominal1.20bar/108C/5K approach: saturation-minus-approach99.7838C. Pressure1.21bar raises this to100.0234C, removing the100C upper interval. Phase exclusion is conditional, not robust to unspecified source-state rounding.',
  non_claims=['No observed heat demand or temperature','No full process validation','No confidence intervals from scenario counts','No physically guaranteed annual service','No capex optimum or retrospective plant-performance conclusion'],
  status='Executed monthly outer-domain bounds and independent accounting closure; process input completeness gate remains open.')
 (ROOT/'results/swiss_monthly_service_cuts_qc_r35_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='tightening'},indent=2))
 print('Phase tightening rows:',len(tightening))
 for ts in [95,100]:
  for capture in [0,.99]:
   z=[r['necessary_mean_service_ceiling_MW'] for r in rows if r['supply_SCENARIO_C']==ts and r['capture_fraction']==capture and r['thermal_model']=='condensation_cut']
   print('Ts/capture/range:',ts,capture,min(z),max(z))
if __name__=='__main__':main()
