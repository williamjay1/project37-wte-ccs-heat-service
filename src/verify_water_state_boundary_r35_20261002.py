"""Reviewer-found hydraulic counterexample and analytic pressure boundary."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,csv
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cache/python_packages_r32'))
from iapws import IAPWS97

def main():
 with (ROOT/'datasets/hagenholz_monthly_clean_r35_20261002.csv').open() as f:data=list(csv.DictReader(f))
 z=[r for r in data if r['year']=='2020']
 mean=sum(float(r['heat_sales_MWh']) for r in z)/sum(float(r['calendar_hours']) for r in z)
 peak=max(float(r['heat_sales_MWh'])/float(r['calendar_hours'])/mean for r in z)
 dH=(IAPWS97(P=1,T=368.15).h-IAPWS97(P=1,T=328.15).h)/1000
 constant=450*.00418*40/peak;exact=450*dH/peak
 flow=57.9*peak/dH
 assert constant<57.9<exact and flow<450
 theta120=IAPWS97(P=.12,x=1).T-273.15-5
 theta121=IAPWS97(P=.121,x=1).T-273.15-5
 critical=IAPWS97(T=378.15,x=1).P*10
 assert theta120<100<theta121 and 1.2<critical<1.21
 with (ROOT/'results/swiss_monthly_service_cuts_r35_20261002.csv').open() as f: cuts=list(csv.DictReader(f))
 match=next(r for r in cuts if r['year']=='2020' and r['capture_fraction']=='0' and r['supply_SCENARIO_C']=='95' and r['volume_SCENARIO_m3']=='0' and r['thermal_model']=='condensation_cut' and r['internal_heat_SCENARIO_MW']=='0' and r['feed_timing_SCENARIO']=='constant_annual_rate')
 assert float(match['necessary_mean_service_ceiling_MW'])>57.9
 result=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS reviewer counterexample repaired and analytic pressure boundary checked',
  old_constant_cp_ceiling_MW=constant,IF97_ceiling_MW=exact,reference57_9MW_peak_flow_kg_s=flow,
  production_new_ceiling_MW=float(match['necessary_mean_service_ceiling_MW']),
  nominal1_20bar_plateau_minus5K_C=theta120,alternative1_21bar_plateau_minus5K_C=theta121,
  critical_pressure_for100C_plus5K_bar=critical,
  interpretation='Nominal source-state phase exclusion conditional. This two-state diagnostic is not a pressure probability distribution, independent source measurement or complete shifted-cycle reoptimization.')
 (ROOT/'results/verify_water_state_boundary_r35_20261002.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
