"""Analytical bypass/adaptation ceilings, checked against the service LP.

The Su BP Table3 OUTPUT anchors are a calibrated differential surrogate,
not a reconstructed turbine. Linear flue-gas bypass holds the on-line train
at its99.72% design capture/SRD and scales recoverable duties. Fixed train
CAPEX is unchanged: these are operating-margin ceilings for adaptation,
NOT bankable costs, an investment ranking or field heat-service validation.
"""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,csv
import numpy as np
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('lp',ROOT/'src/physical_service_feasibility_r32_20261002.py')
lp=importlib.util.module_from_spec(spec);spec.loader.exec_module(lp)
CP=.00418;TR=60;D=36.5;H0=37.3;DHLOSS=18.8;OH=5.3;COMP=1.6;HP=9.8*5.5/4.5
CO2_KG_S=5.168;CAPTURE=.9972;RET=.99*.995

def sources(x,oh_fraction=1):
    return [('H',H0-DHLOSS*x,390),('overhead',OH*x*oh_fraction,91),
            ('compressor',COMP*x,158),('HP',HP*x,77)]

def upper(ts,x,flow,oh_fraction=1):
    ss=sources(x,oh_fraction);out=[sum(q for n,q,t in ss),flow*CP*(ts-TR)]
    for theta in sorted({t for n,q,t in ss}):
        if theta>=ts:continue
        fraction=np.clip((theta-TR)/(ts-TR),0,1)
        if fraction<1:out.append(sum(q for n,q,t in ss if t>theta)/(1-fraction))
    return min(out)

def bypass_limit(ts,flow,oh_fraction=1):
    if upper(ts,0,flow,oh_fraction)<D-1e-9:return None
    if upper(ts,1,flow,oh_fraction)>=D:return 1.
    return brentq(lambda x:upper(ts,x,flow,oh_fraction)-D,0,1,xtol=1e-13)

def main():
    x=bypass_limit(120,150)
    analytical=(H0-D*(1-(77-TR)/(120-TR)))/(DHLOSS-OH-COMP)
    assert abs(x-analytical)<1e-11
    q=[]
    for ts,flow,frac in [(120,150,x),(100,450,1),(100,150,1),(120,450,1)]:
        r=lp.solve(np.full(168,D),ts,TR,frac>0,True,0,flow_limit_kg_s=flow,
                   sources_override=sources(frac),auxiliary_fraction=0,return_dispatch=True)
        dispatch=r.pop('_dispatch')
        r.update(bypass_train_fraction=frac,capture_fraction_total=CAPTURE*frac,
                 heatpump_mean_MW=float(np.mean(dispatch['HP'])),
                 surrogate_electric_output_MW=8.12-1.95*frac-float(np.mean(dispatch['HP']))/5.5)
        q.append(r)
    assert q[0]['service_feasible'] and q[1]['service_feasible']
    assert not q[2]['service_feasible'] and not q[3]['service_feasible']
    # Strong competing source configuration: full95% design capture, not just
    # the constrained99.72% train. Table3 gives19.9MW basic heat and6.25MWe.
    # Detailed branch duties are anchored to the ultra-high-capture case.
    # Do not silently transfer their whole18.8778MW to the95% design, whose
    # published recovery increment is38.0-19.9=18.1MW. Preserve that independent
    # total with a proportional branch-shape CALIBRATION (not source-grade
    # validation). A structural alternative branch split must still be tested.
    recovery_scale95=(38.0-19.9)/(OH+COMP+HP)
    source95=[('H',19.9,390),('overhead',OH*recovery_scale95,91),
              ('compressor',COMP*recovery_scale95,158),('HP',HP*recovery_scale95,77)]
    r95=lp.solve(np.full(168,D),120,TR,True,True,0,flow_limit_kg_s=150,
                 sources_override=source95,auxiliary_fraction=0,return_dispatch=True)
    z95=r95.pop('_dispatch')
    r95.update(heatpump_mean_MW=float(np.mean(z95['HP'])),
                surrogate_electric_output_MW=6.25-float(np.mean(z95['HP']))/5.5,
                capture_fraction_total=.95,
                proportional_recovery_scale_CALIBRATION=recovery_scale95,
                comparison='Published95% basic/advanced total heat anchor with proportionally calibrated recovery grades. Not independently validated branch duties, equal-CAPEX train or validated retrofit.')
    assert r95['service_feasible']
    old,new=q[0],q[1]
    d_capture_t_h=CO2_KG_S*3.6*CAPTURE*(1-x)
    d_retained_t_h=d_capture_t_h*RET
    d_elec_MW=old['surrogate_electric_output_MW']-new['surrogate_electric_output_MW']
    rows=[]
    for comparator in ['same99_train_bypass','published95_design']:
      old0=old if comparator=='same99_train_bypass' else r95
      captured0=CAPTURE*x if comparator=='same99_train_bypass' else .95
      d_capture_t_h0=CO2_KG_S*3.6*(CAPTURE-captured0)
      d_retained_t_h0=d_capture_t_h0*RET
      d_elec_MW0=old0['surrogate_electric_output_MW']-new['surrogate_electric_output_MW']
      for hours in [8000,8760]:
        for ef in [179,429,700]:
            for burden in [0,50,100]:
                for pumping in [0,.1,.5]:
                    extra_power=d_elec_MW0+pumping
                    fstar=(extra_power*ef+d_capture_t_h0*burden)/(1000*d_retained_t_h0)
                    for f in [.4,.4679]:
                        for pe in [40,70,120]:
                            for value in [0,100,300,500]:
                                # Same installed capture train. Extra capture-chain
                                # expenditure is a50EUR/t scenario, not a quote;
                                # field adaptation capital/fixed O&M are unknown.
                                chain=50
                                climate=(extra_power*ef+d_capture_t_h0*burden-1000*d_retained_t_h0*f)*hours
                                ceiling=(value*d_retained_t_h0*f-pe*extra_power-chain*d_capture_t_h0)*hours
                                rows.append(dict(comparator=comparator,monetary_basis='constant_EUR2020_SCENARIOS',hours_SCENARIO=hours,electricity_EF_kg_MWh_SCENARIO=ef,
                                                 incremental_chain_burden_kg_t_SCENARIO=burden,
                                                 incremental_network_pumping_MW_SCENARIO=pumping,
                                                 fossil_share_SCENARIO=f,electricity_price_EUR_MWh_SCENARIO=pe,
                                                 effective_fossil_value_EUR_t_SCENARIO=value,
                                                 marginal_climate_fossil_share_threshold=fstar,
                                                 incremental_GWP_kg_y=climate,
                                                 maximum_included_annual_adaptation_cost_EUR_y=ceiling,
                                                 extra_capture_t_y=d_capture_t_h0*hours,
                                                 extra_retained_fossil_t_y=d_retained_t_h0*f*hours,
                                                 chain_cost_EUR_t_SCENARIO=chain,
                                                 decision_boundary='Operating-margin ceiling. Same99 train has fixed capital;95design comparison additionally requires extra99design capital/O&M. No bankable investment ranking.'))
    with (ROOT/'results/physical_service_adaptation_boundary_r32_20261002.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    sensitivities=[]
    for frac in [0,.5,.8,1]:
        for ts in [85,100,120]:
            for flow in [150,450]:
                limit=bypass_limit(ts,flow,frac)
                sensitivities.append(dict(overhead_usable_fraction_SCENARIO=frac,ts=ts,flow=flow,
                                           bypass_train_fraction_max_NECESSARY=limit,
                                           overall_capture_max_NECESSARY=None if limit is None else CAPTURE*limit))
    annuity=.08/(1-(1+.08)**(-25))
    d_capacity95=CO2_KG_S*3.6*(CAPTURE-.95)
    extra_fixed95=d_capacity95*(5.9e6*annuity+.18e6)
    central95=next(r for r in rows if r['comparator']=='published95_design' and r['hours_SCENARIO']==8000 and r['electricity_EF_kg_MWh_SCENARIO']==179 and r['incremental_chain_burden_kg_t_SCENARIO']==50 and r['incremental_network_pumping_MW_SCENARIO']==0 and r['fossil_share_SCENARIO']==.4 and r['electricity_price_EUR_MWh_SCENARIO']==70 and r['effective_fossil_value_EUR_t_SCENARIO']==300)
    fixed_stress=dict(source='DEA401a2024,2025investment coordinate;5.9millionEUR2020/(t/h),.18millionEUR2020/(t/h)/y; generic90%design',
        additional_capacity_t_h=d_capacity95,CRF_ASSUMED=annuity,additional_fixed_cost_EUR2020_y_SCENARIO=extra_fixed95,
        adaptation_budget_after_fixed_at_value300_EUR2020_y=central95['maximum_included_annual_adaptation_cost_EUR_y']-extra_fixed95,
        adaptation_budget_after_fixed_at_value500_EUR2020_y=central95['maximum_included_annual_adaptation_cost_EUR_y']+200*central95['extra_retained_fossil_t_y']-extra_fixed95,
        effective_value_for_zero_budget_EUR2020_t=300+(extra_fixed95-central95['maximum_included_annual_adaptation_cost_EUR_y'])/central95['extra_retained_fossil_t_y'],
        interpretation='Capacity-proportional CAPITAL STRUCTURAL STRESS, not actual95vs99 equipment or quotation. Strong baseline capital does not cancel. Not a fresh fixed-utilization novelty claim.')
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS algebra/LP checks; bounded differential operating-margin model',
                full_two_case_physical_validation=False,
                critical_bypass_train_fraction_upper=x,total_capture_fraction_upper=CAPTURE*x,
                bypass_min_fraction=1-x,analytical_vs_numeric_error=abs(x-analytical),
                same_secondary_heat_contract='36.5MW at80/50C; primary120/60 to100/60C, minimum HX approach5K; all flows/UA limits require separate checks.',
                LP_checks=q,strong95_design_baseline=r95,capital_stress_against95_design=fixed_stress,extra_capture_t_h=d_capture_t_h,extra_retained_t_h=d_retained_t_h,
                extra_electricity_MW_surrogate=d_elec_MW,financial_rows=len(rows),
                marginal_threshold_range=[min(r['marginal_climate_fossil_share_threshold'] for r in rows),max(r['marginal_climate_fossil_share_threshold'] for r in rows)],
                adaptation_cost_ceiling_range_EUR_y=[min(r['maximum_included_annual_adaptation_cost_EUR_y'] for r in rows),max(r['maximum_included_annual_adaptation_cost_EUR_y'] for r in rows)],
                central_rows=[r for r in rows if r['hours_SCENARIO']==8000 and r['electricity_EF_kg_MWh_SCENARIO']==179 and r['incremental_chain_burden_kg_t_SCENARIO']==50 and r['incremental_network_pumping_MW_SCENARIO']==0 and r['fossil_share_SCENARIO']==.4 and r['electricity_price_EUR_MWh_SCENARIO']==70 and r['effective_fossil_value_EUR_t_SCENARIO']==300],
                overhead_temperature_flow_structural_sensitivity=sensitivities,
                boundary='SourceA BP heat/power anchors; optimistic high-grade heat box, no certified HEX/hardware or full turbine reconstruction. Constraints reject full capture at120C; passes at100C remain necessary. Annual extrapolations constant load and perfect process availability, not measured SLA.',
                never_claim=['Universal EU threshold','Observed capture or network performance','Actual profits or ETS eligibility','Economic optimum first investment','90-point gate completed'])
    (ROOT/'results/physical_service_adaptation_boundary_qc_r32_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['LP_checks','overhead_temperature_flow_structural_sensitivity']},indent=2))

if __name__=='__main__':main()
