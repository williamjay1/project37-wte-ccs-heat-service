"""Printed-state reproduction pilot, NOT a fitted or measured plant validation.

Source equations: Otgonbayar & Mazzotti, Energy 290 130087 (2024),
Eqs 6--20 and Appendix A. Su et al., Fuel 332 126004 (2023),
Tables 1--3, Sec 2.1/2.2 and Appendix 2 are independent checks.
Properties: iapws 1.5.5 IAPWS-IF97, GPL-3, separately installed in D cache.
No adjustment of missing source duties to force output agreement.
"""
from pathlib import Path
import sys
import json
import csv
import hashlib
from datetime import datetime, timezone
import math
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'cache/python_packages_r32'))
from iapws import IAPWS97, __version__ as iapws_version

def hs(p_bar, temp=None, quality=None):
    args = {'P':p_bar/10}
    if quality is not None:
        args['x'] = quality
    else:
        args['T'] = temp+273.15
    return IAPWS97(**args).h/1000  # MJ/kg

def liquid(t, p_bar=1):
    # Pressure of extracted condensate is not consistently supplied by paper.
    # Saturated-liquid convention at high T; compressed liquid at 1bar below boil.
    if t >= 100:
        return IAPWS97(T=t+273.15,x=0).h/1000
    return hs(p_bar,t)

def cycle(mhp, hh, hi, hl, hc, hfw, fws, dhret, ccsret,
          qdh, qccs, qind, qinternal, wint, wccs, x, eta=.95):
    # Return exact Eqs 6--20 algebra evaluated from independently recorded states.
    returns = dict(ind=liquid(90), WtE=liquid(90), DH=liquid(dhret), CCS=liquid(ccsret))
    qs = dict(ind=qind, WtE=qinternal, DH=qdh, CCS=qccs)
    supply = {u:(hi if x[u] else hl) for u in qs}
    flows = {u:qs[u]/(supply[u]-returns[u]) for u in qs}
    qfw = (mhp*(hfw-hc)-sum(flows[u]*(returns[u]-hc) for u in flows))*(fws-hfw)/(fws-hc)
    flows['FW'] = qfw/(fws-hfw)
    mip = mhp-sum(flows[u]*x[u] for u in flows)
    mlp = mip-sum(flows[u]*(1-x[u]) for u in flows)
    power = eta*(mhp*(hh-hi)+mip*(hi-hl)+mlp*(hl-hc))-wint-wccs
    # Direct-contact FW heater: condensed extraction returns at hFW but its
    # released duty heats the OTHER return streams. Include that duty once.
    retbalance = sum(flows[u]*returns[u] for u in qs)+flows['FW']*hfw+mlp*hc+qfw
    return dict(mHP=mhp,mIP=mip,mLP=mlp,heat_feedwater_MW=qfw,net_power_MW=power,
                mass_error_kg_s=mhp-sum(flows.values())-mlp,
                feedwater_enthalpy_error_MW=mhp*hfw-retbalance,
                **{f'm_{u}_kg_s':m for u,m in flows.items()})

checks=[]
def check(name, calc, reported, tolerance_pct, kind, note):
    err = 100*(calc-reported)/reported
    checks.append(dict(check=name,calculated=calc,reported=reported,
                       error_percent=err,tolerance_percent=tolerance_pct,
                       pass_printed_precision_or_tolerance=bool(abs(err)<=tolerance_pct),
                       kind=kind,note=note))

# SU independent, printed-state checks. No mixing the 90% thesis output with Fuel.
su=dict(throughput_main_t_day=500,throughput_appendix_t_hour=19.4,
        thermal_input_appendix_MW=55.6,lhv_appendix_MJ_kg=9.3,
        flue_mol_s=1046,flue_kg_s=30.71,co2_mole_fraction=.1111,
        co2_direct_kg_s=5.168,steam_kg_s=18.2,HP_temp_C=400,
        HP_bar_main=60,HP_bar_appendix=40,IP_bar=4,FW_bar=6,
        FW_return_C=137,FW_return_bar=80,reboiler_C=125,
        reboiler_pinch_K=10,dh_supply_C=80,dh_return_C=60,
        compressor_heat_MW=1.6,overhead_heat_MW=5.3,DCC_source_MW=9.8,
        hp_COP=5.5,hp_delivery_limit_C=77,condensing_min_fraction=.15)
check('Su flue CO2 molar reconstruction kg/s',su['flue_mol_s']*.1111*.04401,5.168,2,'independent mass check','Table1 rounded wet molar fractions vs Sec2.2 explicit CO2 rate, not fitted')
check('Su main vs Appendix throughput t/day',19.4*24,500,2,'source inconsistency','Appendix2 is reference calibration, not silently substituted for main generic case')
check('Su Appendix fuel MW from listed LHV and throughput',19.4/3.6*9.3,55.6,2,'source inconsistency','No forced reconciliation of Appendix2 entries')
for p in [40,60]:
    duty=18.2*(hs(p,400)-hs(80,137))
    check(f'Su boiler transfer MW at {p}bar HP',duty,55.6*.88,3,'structural state check','Appendix boiler efficiency88%, feed pressure80bar; main and Appendix HP pressures kept separate')
tsat4 = IAPWS97(P=.4,x=1).T-273.15
hpout=9.8*5.5/(5.5-1)
hpwork=9.8/(5.5-1)
check('Su heat-pump hot delivery MW',hpout,12,3,'independent first-law check','Source DCC9.8MW; COP5.5; expected around12MW')
check('Su heat-pump electricity MW',hpwork,2.2,3,'independent first-law check','Uses Qhot=Qsource+Wel, not a free thermal credit')
su_rows=[]
for capture,qreb,baseline_heat,basic_heat,advanced_heat,bp_power in [(.95,3.59,37.3,19.9,38.0,6.25),(.9972,3.72,37.3,18.5,37.3,6.17)]:
    qccs=5.168*capture*qreb
    hi=hs(4,quality=1); fws=hs(6,quality=1); hc=liquid(60); hcr=hs(4,quality=0)
    mccs=qccs/(hi-hcr)
    # Generalized Eq22 feedwater return credit: replaces steam DH, not raw MW.
    effective_heat_loss=mccs*(fws-hcr)*(hi-hc)/(fws-hc)
    predicted_basic=baseline_heat-effective_heat_loss
    predicted_adv=predicted_basic+1.6+5.3+hpout
    check(f'Su BP basic heat at {100*capture:.2f}% MW',predicted_basic,basic_heat,3,'independent differential heat check','Condensate at 4bar saturated liquid; derives return-credit correction from Otgonbayar balance; no fitting of baseline37.3MW')
    check(f'Su BP advanced heat at {100*capture:.2f}% MW',predicted_adv,advanced_heat,3,'independent differential heat check','Three published recovery duties held constant, approximate published aggregation; pump77C trimmed to80C separately')
    trim=hpout*(80-77)/(77-60)
    su_rows.append(dict(capture=capture,qreboiler_MW=qccs,ccs_steam_kg_s=mccs,heat_loss_MW=effective_heat_loss,
                        heat_basic_MW=predicted_basic,heat_advanced_aggregate_MW=predicted_adv,
                        hp_source_MW=9.8,hp_hot_MW=hpout,hp_electric_MW=hpwork,
                        hp_trim_from77_to80_MW=trim,reboiler_temperature_margin_K=tsat4-125-10,
                        note='Partial energy/temperature replication. Full turbine power not independently reproduced.'))

# OTGONBAYAR printed conditions: missing duties and annual operating hours are
# explicit sensitivity axes, NEVER inferred as a claim of exact reproduction.
cases=[dict(name='Hagenholz_2027_heat',waste_kt_a=375,lhv=11.5,fco2=1.1,THP=400,PHP=40,PIP=3.5,PLP=1.2,Pcond=1.2,chi=.96,minLP=0,qind=4.2,retDH=55,qdh=64.4,reportP=21.7,x=dict(ind=1,WtE=1,DH=0,CCS=1,FW=1)),
       dict(name='Linth_power',waste_kt_a=110,lhv=11.8,fco2=1.2,THP=410,PHP=41,PIP=3.5,PLP=3.5,Pcond=.06,chi=.94,minLP=2.1,qind=0,retDH=57,qdh=2.8,reportP=7.5,x=dict(ind=1,WtE=0,DH=0,CCS=0,FW=0))]
otrows=[]
for c in cases:
    for annual_hours in [8000,8760]:
        mw=c['waste_kt_a']*1000/(annual_hours*3.6)
        hh=hs(c['PHP'],c['THP']);hi=hs(c['PIP'],quality=1);hl=hs(c['PLP'],quality=1)
        hfw=liquid(130);hc=hs(c['Pcond'],quality=c['chi'])
        # Eq11 uses condensate return LIQUID enthalpy, whereas power uses wet-steam
        # outlet. Separate these states; using turbine outlet in Eq11 is wrong.
        hcond_return=hs(c['Pcond'],quality=0)
        mhp=.85*mw*c['lhv']/(hh-hfw) if 'Hagenholz' in c['name'] else .88*mw*c['lhv']/(hh-hfw)
        for missing_q_internal in [0,1.7,3.4]:
            for capture in [0,.6,.9,.99]:
                qreb=capture**3-1.2*capture**2+.39*capture+2.6
                wel=.8*capture**2-1.3*capture+.8
                qccs=mw*c['fco2']*capture*qreb
                wccs=mw*c['fco2']*capture*wel
                # Evaluate printed equations with separate condenser return and
                # turbine exhaust via direct balance (keeps exact mass/FW closure).
                r=cycle(mhp,hh,hi,hl,hcond_return,hfw,hi if c['x']['FW'] else hl,
                        c['retDH'],139,c['qdh'],qccs,c['qind'],missing_q_internal,0,wccs,c['x'])
                r['net_power_MW']+=.95*r['mLP']*(hcond_return-hc)
                r.update(case=c['name'],annual_operating_hours_assumption=annual_hours,
                         missing_internal_heat_scenario_MW=missing_q_internal,missing_internal_electric_assumed_MW=0,
                         capture=capture,qreboiler_MW=qccs,qDH_MW=c['qdh'],minLP=c['minLP'],
                         feasible_steam=r['mLP']>=c['minLP'],reported_noCCS_power_MW=c['reportP'],
                         declared='Uncalibrated sensitivity, not full plant replication')
                otrows.append(r)

report=dict(created_utc=datetime.now(timezone.utc).isoformat(),iapws_version=iapws_version,
            property_formulation='IAPWS-IF97; saturation convention for rounded extraction states',
            su_inputs=su,su_partial_replication=su_rows,checks=checks,
            otgonbayar_status='Printed boiler/turbine states exist; qWtE, wWtE, operating hours and complete recovery stream curves not numerically supplied. Do NOT claim full reproduction or fit unknowns to results.',
            otgonbayar_LHV_unit='Table2 printed kJ/kg with values11.5/11.8; modeled as MJ/kg with explicit 1000x interpretation and energy consistency audit.',
            full_two_case_gate='CONDITIONAL: partial source replication only',
            full_factory_validation=False)
out=ROOT/'results/physical_service_pilot_r32_20261002.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
csvpath=ROOT/'results/physical_service_otgon_sensitivity_r32_20261002.csv'
with csvpath.open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=list(otrows[0]));writer.writeheader();writer.writerows(otrows)
print(json.dumps(report,indent=2))
print('Uncalibrated Otgonbayar cases:',len(otrows),'max mass/FW errors:',max(abs(r['mass_error_kg_s']) for r in otrows),max(abs(r['feedwater_enthalpy_error_MW']) for r in otrows))
