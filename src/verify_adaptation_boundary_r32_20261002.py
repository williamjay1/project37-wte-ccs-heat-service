"""Rebuild every adaptation ledger without importing the production model."""
from pathlib import Path
from datetime import datetime,timezone
import csv,json
ROOT=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((ROOT/'results/physical_service_adaptation_boundary_r32_20261002.csv').open(encoding='utf-8')))
ret=.99*.995;max_error=0
for r in rows:
    # Reconstruct binding sourceA heat-temperature cut analytically.
    x=(37.3-36.5*(120-77)/(120-60))/(18.8-5.3-1.6)
    wnew=6.17-(36.5-18.5-5.3-1.6)/5.5
    if r['comparator']=='same99_train_bypass':
        cold= .9972*x
        wold=8.12-1.95*x-(36.5-(37.3-18.8*x)-6.9*x)/5.5
    else:
        cold=.95
        scale95=(38.0-19.9)/(5.3+1.6+9.8*5.5/4.5)
        wold=6.25-(36.5-19.9-(5.3+1.6)*scale95)/5.5
    cc=5.168*3.6*(.9972-cold)
    h=float(r['hours_SCENARIO']);f=float(r['fossil_share_SCENARIO'])
    ef=float(r['electricity_EF_kg_MWh_SCENARIO']);b=float(r['incremental_chain_burden_kg_t_SCENARIO'])
    power=wold-wnew+float(r['incremental_network_pumping_MW_SCENARIO'])
    expected={'extra_capture_t_y':cc*h,'extra_retained_fossil_t_y':cc*ret*f*h,
              'marginal_climate_fossil_share_threshold':(power*ef+cc*b)/(1000*cc*ret),
              'incremental_GWP_kg_y':(power*ef+cc*b-1000*cc*ret*f)*h,
              'maximum_included_annual_adaptation_cost_EUR_y':(float(r['effective_fossil_value_EUR_t_SCENARIO'])*cc*ret*f-float(r['electricity_price_EUR_MWh_SCENARIO'])*power-50*cc)*h}
    for k,v in expected.items():
        error=abs(float(r[k])-v)/max(1,abs(v));max_error=max(max_error,error)
        assert error<1e-10,(k,r,error)
assert len(rows)==2592
report=json.loads((ROOT/'results/physical_service_adaptation_boundary_qc_r32_20261002.json').read_text())
central=next(r for r in rows if r['comparator']=='published95_design' and
             all(float(r[k])==v for k,v in {'hours_SCENARIO':8000,
             'electricity_EF_kg_MWh_SCENARIO':179,'incremental_chain_burden_kg_t_SCENARIO':50,
             'incremental_network_pumping_MW_SCENARIO':0,'fossil_share_SCENARIO':.4,
             'electricity_price_EUR_MWh_SCENARIO':70,'effective_fossil_value_EUR_t_SCENARIO':300}.items()))
capital=report['capital_stress_against95_design']
capacity=5.168*3.6*(.9972-.95)
crf=.08*(1.08**25)/(1.08**25-1)
annual=capacity*(5.9e6*crf+180000)
margin=float(central['maximum_included_annual_adaptation_cost_EUR_y'])
fossil=float(central['extra_retained_fossil_t_y'])
capital_expected={'additional_capacity_t_h':capacity,'CRF_ASSUMED':crf,
    'additional_fixed_cost_EUR2020_y_SCENARIO':annual,
    'adaptation_budget_after_fixed_at_value300_EUR2020_y':margin-annual,
    'adaptation_budget_after_fixed_at_value500_EUR2020_y':margin+200*fossil-annual,
    'effective_value_for_zero_budget_EUR2020_t':300+(annual-margin)/fossil}
for key,value in capital_expected.items():
    err=abs(capital[key]-value)/max(1,abs(value))
    assert err<1e-10,(key,err)
    max_error=max(max_error,err)
result=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS',rows=len(rows),
            checked_numbers=len(rows)*5+len(capital_expected),max_relative_error=max_error,
            scope='Independent algebra/units/all-row ledger check, not empirical validation or certified heat-service attainability.')
(ROOT/'results/physical_service_adaptation_independent_qc_r32_20261002.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
