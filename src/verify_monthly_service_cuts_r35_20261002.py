"""Independent 12-period LP and raw-to-clean checks for necessary monthly cuts.

No imports from the production cut algorithm. This checks the relaxed total
energy bound, not thermodynamic sufficiency or observed customer service.
"""
from pathlib import Path
from datetime import datetime, timezone
import csv, json, hashlib, calendar
import numpy as np
from scipy.optimize import linprog
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cache/python_packages_r32'))
from iapws import IAPWS97

ROOT=Path(__file__).resolve().parents[1]

def energy_lp(hours, shape, source, buffer):
    # [annual-mean service R, 12 generation duties, 12 circular stocks]
    A=np.zeros((12,25))
    for k in range(12):
        A[k,0]=-shape[k]*hours[k]
        A[k,1+k]=hours[k]
        A[k,13+k]=1
        A[k,13+(k+1)%12]-=1
    objective=np.zeros(25);objective[0]=-1
    res=linprog(objective,A_eq=A,b_eq=np.zeros(12),
       bounds=[(0,None)]+[(0,float(q)) for q in np.broadcast_to(np.asarray(source),hours.shape)]+[(0,buffer)]*12,method='highs')
    assert res.success,res.message
    residual=float(np.max(np.abs(A@res.x)))
    assert residual<1e-7
    return float(res.x[0]),residual

def main():
    clean=ROOT/'datasets/hagenholz_monthly_clean_r35_20261002.csv'
    with clean.open(encoding='utf-8',newline='') as f: data=list(csv.DictReader(f))
    with (ROOT/'results/swiss_monthly_service_cuts_r35_20261002.csv').open(encoding='utf-8',newline='') as f: cuts=list(csv.DictReader(f))
    assert len(cuts)==384
    years=sorted({int(r['year']) for r in cuts})
    errors=[];balance=[];count=0;phase_monotone=0;storage_monotone=0
    for year in years:
        z=sorted((r for r in data if int(r['year'])==year),key=lambda r:int(r['month']))
        assert [int(r['month']) for r in z]==list(range(1,13))
        hours=np.array([24*calendar.monthrange(year,k)[1] for k in range(1,13)],dtype=float)
        assert all(float(r['calendar_hours'])==hours[k] for k,r in enumerate(z))
        MWh=np.array([float(r['heat_sales_MWh']) for r in z])
        shape=MWh/hours/(sum(MWh)/sum(hours))
        for row in (r for r in cuts if int(r['year'])==year):
            Q=np.array(json.loads(row['monthly_total_source_MW_JSON']))
            B=float(row['tank_usable_energy_MWh'])
            predicted,residual=energy_lp(hours,shape,Q,B)
            e=abs(predicted-float(row['total_energy_mean_ceiling_MW']))
            assert e<1e-8,(row,e)
            errors.append(e);balance.append(residual);count+=1
            delta_h=(IAPWS97(P=1,T=float(row['supply_SCENARIO_C'])+273.15).h-IAPWS97(P=1,T=328.15).h)/1000
            expectedflow=450*delta_h/max(shape)
            assert abs(expectedflow-float(row['hydraulic_mean_ceiling_MW']))<1e-10
            candidates=[predicted,expectedflow]
            if row['phase_mean_ceiling_MW']:
                fraction=float(row['upper_interval_fraction'])
                upper=min(np.array(json.loads(row['monthly_upper_source_MW_JSON']))/(fraction*shape))
                assert abs(upper-float(row['phase_mean_ceiling_MW']))<1e-8
                candidates.append(upper)
            assert abs(min(candidates)-float(row['necessary_mean_service_ceiling_MW']))<1e-8
            assert (row['pass_reference_mean64_4_NECESSARY']=='True')==(64.4<=min(candidates)+1e-8)
    keys=['year','feed_timing_SCENARIO','internal_heat_SCENARIO_MW','capture_fraction','supply_SCENARIO_C','volume_SCENARIO_m3']
    for row in cuts:
        if row['thermal_model']=='condensation_cut':
            old=next(x for x in cuts if x['thermal_model']=='rectangular_inlet_grade' and all(x[k]==row[k] for k in keys))
            assert float(row['necessary_mean_service_ceiling_MW'])<=float(old['necessary_mean_service_ceiling_MW'])+1e-9
            phase_monotone+=1
        if row['volume_SCENARIO_m3']=='5000':
            empty=next(x for x in cuts if x['volume_SCENARIO_m3']=='0' and x['thermal_model']==row['thermal_model'] and all(x[k]==row[k] for k in keys if k!='volume_SCENARIO_m3'))
            assert float(row['necessary_mean_service_ceiling_MW'])>=float(empty['necessary_mean_service_ceiling_MW'])-1e-9
            storage_monotone+=1
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS independent 12-period energy LP and necessary-cut algebra',
      energy_lp_cases=count,max_energy_LP_vs_circular_cut_MW=max(errors),max_LP_balance_MWh=max(balance),
      phase_monotonicity_checks=phase_monotone,storage_monotonicity_checks=storage_monotone,
      calendar_years=years,processed_sha256=hashlib.sha256(clean.read_bytes()).hexdigest(),
      limits='Monthly total-energy relaxation only. Infinite charge/discharge power, no loss/outage, normalized sales NOT demand. Not independent validation of steam/temperature inputs or annual physical service.')
    (ROOT/'results/verify_monthly_service_cuts_r35_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
