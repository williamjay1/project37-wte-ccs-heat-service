"""Thermodynamic bracket on published steam heat; no fitted plant validation.

Upper exclusion: superheat above the condensation plateau is bounded rather
than promoting the whole steam duty to the inlet temperature. Lower positive
certificate: an adiabatic, non-reheated Su steam route must contain at least a
specified latent-duty fraction under declared condensation/return assumptions.
Rounded source-state stresses are NOT sampling errors or confidence intervals.
"""
from pathlib import Path
import sys,json,csv
from datetime import datetime,timezone
import numpy as np
from scipy.integrate import quad
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cache/python_packages_r32'))
from iapws import IAPWS97
from physical_service_feasibility_r32_20261002 import solve
from physical_service_caseB_check_r32_20261002 import CASES,h,hr
from physical_service_caseB_envelope_r32_20261002 import heat_limit

def save(name,rows):
    with (ROOT/'results'/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def lm(a,b):
    if min(a,b)<=0:raise ValueError('Nonpositive exchanger terminal approach')
    return a if abs(a-b)<1e-10 else (a-b)/np.log(a/b)

def water_h(T):
    # Declared10bar primary-water pressure, not an observed network pressure.
    # All tested temperatures<=160C are liquid. Exact IF97 enthalpy, MJ/kg.
    return IAPWS97(P=1,T=T+273.15).h/1000

def cold_upper_fraction(ts,tr,theta):
    return (water_h(ts)-water_h(theta))/(water_h(ts)-water_h(tr))

def su_bracket():
    inlet=IAPWS97(P=6,T=673.15)
    isentropic=IAPWS97(P=.4,s=inlet.s)
    vap=IAPWS97(P=.4,x=1);liq=IAPWS97(P=.4,x=0)
    ret=IAPWS97(P=.4,T=333.15)
    # No external reheater, adiabatic turbine, nonnegative work and entropy
    # production give h_is <= h_out <= h_HP. Steam fully condenses, with its
    # condensate not cooled below DH return. These are declared route conditions.
    assert isentropic.h>liq.h and inlet.h>vap.h
    latent_endpoints=[(min(v.h,vap.h)-liq.h)/(v.h-ret.h)
                      for v in (isentropic,inlet)]
    latent_lower=min(latent_endpoints)
    superheat_upper=(inlet.h-vap.h)/(inlet.h-liq.h)
    return dict(HP_h_MJ_kg=inlet.h/1000,HP_s_kJ_kgK=inlet.s,
                isentropic_exhaust_h_MJ_kg=isentropic.h/1000,
                isentropic_exhaust_quality=isentropic.x,
                saturation_C=vap.T-273.15,saturated_vapor_h_MJ_kg=vap.h/1000,
                saturated_liquid_h_MJ_kg=liq.h/1000,return60_h_MJ_kg=ret.h/1000,
                latent_fraction_lower=latent_lower,
                superheat_fraction_upper=superheat_upper,
                route_conditions='Adiabatic non-reheated 60bar/400C ->4bar route; nonnegative work/entropy production; full condensation; condensate return >=60C. Source heat anchors, not fitted off-design output.')

def main():
    b=su_bracket();rows=[];su_flags=[]
    theta=b['saturation_C']-10
    for d in (15,20,25,30,36.5):
      for ts in (100,120,140,160):
       for volume in (0,50000):
        for capture in (False,True):
         H=18.5 if capture else 37.3
         sources=[('H',H,390),('overhead',5.3 if capture else 0,91),
                  ('compressor',1.6 if capture else 0,158),
                  ('HP',9.8*5.5/4.5 if capture else 0,77)]
         for phase in (False,True):
          r=solve(np.full(168,d),ts,60,capture,True,0,sources_override=sources,
              steam_phase_cuts=[(theta,H*b['superheat_fraction_upper'],cold_upper_fraction(ts,60,theta))] if phase and ts>theta else ([] if phase else None),
              usable_capacity_MWh=.9*1000*volume*.00418*39/3600,
              store_power_MW=288 if volume else 0,tank_hot_C=99,tank_approach_K=2,
              charge_efficiency=1,discharge_efficiency=1,
              weekly_loss=1-(1-.0006)**7,auxiliary_fraction=.002 if volume else 0,
              flow_limit_kg_s=450)
          # Fixed schema makes optional diagnostic metadata explicit.
          r['steam_phase_cut_count']=int(phase and 60<theta<ts)
          r.update(case='Su_backpressure',demand_MW=d,volume_m3=volume,
                   phase_model='bounded_superheat' if phase else 'rectangular_high_steam')
          rows.append(r)
    keys=('demand_MW','supply_temperature_C','volume_m3','capture_on')
    for r in rows:
        if r['phase_model']!='rectangular_high_steam' or not r['service_feasible']:continue
        p=next(x for x in rows if x['phase_model']=='bounded_superheat' and all(x[k]==r[k] for k in keys))
        if not p['service_feasible']:
            su_flags.append({k:p[k] for k in keys}|{'unserved_MWh':p['unserved_MWh']})
    save('steam_phase_su_matrix_r33_20261002.csv',rows)

    # Transfer check: printed Swiss state has only 3.216K superheat at1.2bar.
    # The source does not specify exchanger minimum approaches. They are
    # engineering design coordinates, never reported measured assumptions.
    br=[];bf=[]
    for c in CASES:
     for hours in (8000,8760):
      for qi in (0,3.4):
       for capture in (0,.99):
        H=heat_limit(c,hours,capture,qi)
        vap=IAPWS97(P=c['PLP']/10,x=1);hin=h(c['PLP'],c['TLP']);ret=hr(c['TR'])
        superheat=max(0,hin-vap.h/1000)/(hin-ret)
        latent=(min(hin,vap.h/1000)-IAPWS97(P=c['PLP']/10,x=0).h/1000)/(hin-ret)
        for approach in (3,5,8):
         for ts in (95,100):
          for phase in (False,True):
           r=solve(np.full(168,c['qdh']),ts,c['TR'],capture>0,True,0,
                sources_override=[('H',H,c['TLP']-approach),('overhead',0,100),('compressor',0,100),('HP',0,100)],
                steam_phase_cuts=[(vap.T-273.15-approach,H*superheat,cold_upper_fraction(ts,c['TR'],vap.T-273.15-approach))] if phase and ts>vap.T-273.15-approach else ([] if phase else None),
                flow_limit_kg_s=450,usable_capacity_MWh=0,store_power_MW=0)
           r['steam_phase_cut_count']=int(phase and c['TR']<vap.T-273.15-approach<ts)
           r.update(case=c['case'],hours_SCENARIO=hours,internal_heat_SCENARIO_MW=qi,
                capture_fraction=capture,approach_SCENARIO_K=approach,
                phase_model='printed_condensation_curve' if phase else 'rectangular_inlet_grade',
                steam_limit_MW=H,saturation_SOURCE_PRESSURE_C=vap.T-273.15,
                steam_superheat_fraction=superheat,steam_latent_fraction=latent,
                recovery_case='Steam-only diagnostic; zero capture heat recovery, not reproduction of advanced recovery case')
           br.append(r)
    bk=('case','hours_SCENARIO','internal_heat_SCENARIO_MW','capture_fraction','approach_SCENARIO_K','supply_temperature_C')
    for r in br:
        if r['phase_model']!='rectangular_inlet_grade' or not r['service_feasible']:continue
        p=next(x for x in br if x['phase_model']=='printed_condensation_curve' and all(x[k]==r[k] for k in bk))
        if not p['service_feasible']:
            bf.append({k:p[k] for k in bk}|{'unserved_MWh':p['unserved_MWh']})
    save('steam_phase_swiss_transfer_r33_20261002.csv',br)

    rounding=[];c=CASES[0]
    for hours in (8000,8760):
     for qi in (0,3.4):
      H=heat_limit(c,hours,0,qi)
      for p in (1.15,1.2,1.25):
       for temp in (107.5,108,108.5):
        vap=IAPWS97(P=p/10,x=1);hin=h(p,temp);ret=hr(c['TR'])
        rho=max(0,hin-vap.h/1000)/(hin-ret)
        from scipy.optimize import brentq
        critical=brentq(lambda delta:cold_upper_fraction(100,c['TR'],vap.T-273.15-delta)-H*rho/c['qdh'],
                        vap.T-273.15-100,vap.T-273.15-c['TR']-1e-6)
        rounding.append(dict(hours_SCENARIO=hours,internal_heat_SCENARIO_MW=qi,
               LP_pressure_SCENARIO_bar=p,LP_temperature_SCENARIO_C=temp,
               steam_capacity_held_nominal_MW=H,max_approach_for100C_service_K=critical,
               approach5_excluded=5>critical,approach8_excluded=8>critical,
               scope='State-rounding structural stress only; steam capacity held at nominal balance; not a statistical interval or complete process uncertainty.'))
    save('steam_phase_rounding_stress_r33_20261002.csv',rounding)

    # Constructive lower certificate uses ONLY the conservative latent duty.
    # It discards all recovery and all steam superheat/sensible heat. A separate
    # service-water exchanger at the saturation plateau meets the temperature
    # contract without claiming that an outer-domain pass is sufficient.
    certified=18.5*b['latent_fraction_lower'];certs=[]
    for ts,tr in ((100,60),(120,60)):
      mass_water=certified/(water_h(ts)-water_h(tr))
      UA=mass_water*quad(lambda T:IAPWS97(P=1,T=T+273.15).cp/1000/(b['saturation_C']-T),tr,ts,epsabs=1e-12)[0]
      assert b['saturation_C']-ts>=10
      for capture in (False,True):
        H=18.5 if capture else 37.3
        available=H*b['latent_fraction_lower']
        mass=certified/((b['saturated_vapor_h_MJ_kg']-b['saturated_liquid_h_MJ_kg'])*b['isentropic_exhaust_quality'])
        certs.append(dict(case='Su_backpressure',capture_on=capture,delivered_heat_MW=certified,
                  primary_supply_C=ts,primary_return_C=tr,
                  guaranteed_latent_available_MW=available,
                  steam_condensing_temperature_C=b['saturation_C'],
                  minimum_approach_K=b['saturation_C']-ts,exchanger_UA_required_MW_K=UA,
                  water_flow_required_kg_s=mass_water,
                  primary_pressure_SCENARIO_bar=10,
                  constant_cp_UA_comparator_MW_K=certified/lm(b['saturation_C']-ts,b['saturation_C']-tr),
                  constant_cp_flow_comparator_kg_s=certified/(.00418*(ts-tr)),
                  condensing_steam_mass_at_lower_quality_kg_s=mass,
                  unused_basic_heat_rejection_required_MW=H-certified,
                  output_level='Constructive steady thermal certificate under stated steam-route, available heat and ideal exchanger assumptions. Not reliability/off-design/net-power/hardware validation.'))
    save('steam_phase_constructive_certificate_r33_20261002.csv',certs)
    # Fixed published steam points retain the source power difference, NOT a
    # bound on off-design electricity. Recovery/HP are unused, not free credits.
    C=5.168*.9972*3.6;dW=8.12-6.17
    fstar=(179*dW+50*C)/(1000*.99*.995*C)
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),su_bracket=b,
        Su_LPs=len(rows),Swiss_LPs=len(br),Su_outer_tightening_exclusions=su_flags,
        Swiss_rectangular_false_admissions=bf,
        state_rounding_stresses=len(rounding),approach5_rounding_excluded=int(sum(x['approach5_excluded'] for x in rounding)),
        approach8_rounding_excluded=int(sum(x['approach8_excluded'] for x in rounding)),
        critical_approach_range_K=[min(x['max_approach_for100C_service_K'] for x in rounding),max(x['max_approach_for100C_service_K'] for x in rounding)],
        constructive_same_thermal_service_MW=certified,
        constructive_fossil_threshold_fixed_point_foreground=fstar,
        source_capture_t_per_h=C,full_basic_power_penalty_MW=dW,
        constructive_fossil40_delta_kgCO2e_per_h=179*dW+50*C-1000*.99*.995*C*.4,
        fixed_point_climate_condition='Only if published basic steam points remain fixed, unused heat can be rejected and all incremental cooling/other burdens are included. Printed power difference is not a verified bound on off-design electricity.',
        cold_stream_properties='Steam-phase cuts and constructive certificate use IAPWS liquid-water enthalpy/cp at a declared10bar pressure. Existing non-phase grade/flow screens retain the stated4.18kJ/kg/K approximation.',
        max_constraint_residual=max(max(x['max_eq_error'],x['max_ub_violation']) for x in rows+br),
        status='Computed thermodynamic exclusion and conditional constructive thermal bracket; no new plant validation or perfect-reliability claim.',
        effect_on_existing_r32_main_matrix='Su phase cut is inactive at100/120C with10K approach; earlier annual counts unchanged. Swiss near100C boundary is source-rounding sensitive at5K, consistently excluded at8K in declared state stresses.',
        non_claims=['No fully reproduced source turbine power','No actual factory service verification','No full LCA or confidence interval','No demonstrated optimal investment timing'])
    (ROOT/'results/steam_phase_domain_qc_r33_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('Su_outer_tightening_exclusions','Swiss_rectangular_false_admissions')},indent=2))
    print('Exclusions:',len(su_flags),len(bf))
if __name__=='__main__':main()
