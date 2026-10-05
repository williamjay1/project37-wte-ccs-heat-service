"""Independent differential check of Otgonbayar2024 printed steam equations.

Missing operating hours are STRUCTURAL SCENARIOS, not recovered observations.
Do not fit internal duties or annual hours to the published power values.
Absolute net power is not validated. Differential power cancels unchanged
internal electricity and heat use. Temperature uses printed T/P, unlike the
saturation approximation in the first pilot, exposing that structure.
"""
from pathlib import Path
import sys,csv,json
from datetime import datetime,timezone
import numpy as np
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cache/python_packages_r32'))
from iapws import IAPWS97

def h(pbar,T=None,x=None):
    kw={'P':pbar/10}
    kw.update({'x':x} if x is not None else {'T':T+273.15})
    return IAPWS97(**kw).h/1000
def hr(T):
    return IAPWS97(T=T+273.15,x=0).h/1000 if T>=100 else h(1,T)

def state(c,hours,capture,qdh,qinternal=0,exact_T=True):
    mw=c['waste_kt_a']*1e6/(hours*3600)
    hh=h(c['PHP'],c['THP'])
    hi=h(c['PIP'],c['TIP']) if exact_T else h(c['PIP'],x=1)
    hl=h(c['PLP'],c['TLP']) if exact_T else h(c['PLP'],x=1)
    hcond=h(c['PC'],x=0); hexhaust=h(c['PC'],x=c['chi'])
    hfw=hr(130); fws=hi if c['x']['FW'] else hl
    mhp=c['eta_b']*mw*c['LHV']/(hh-hfw)
    qreb=capture**3-1.2*capture**2+.39*capture+2.6
    wel=.8*capture**2-1.3*capture+.8
    qccs=mw*c['fCO2']*capture*qreb
    we=mw*c['fCO2']*capture*wel
    qs={'CCS':qccs,'DH':qdh,'ind':c['qind'],'WtE':qinternal}
    rets={'CCS':hr(139),'DH':hr(c['TR']),'ind':hr(90),'WtE':hr(90)}
    flows={k:qs[k]/((hi if c['x'][k] else hl)-rets[k]) for k in qs}
    qfw=(mhp*(hfw-hcond)-sum(flows[k]*(rets[k]-hcond) for k in flows))*(fws-hfw)/(fws-hcond)
    flows['FW']=qfw/(fws-hfw)
    mip=mhp-sum(flows[k]*c['x'][k] for k in flows)
    mlp=mip-sum(flows[k]*(1-c['x'][k]) for k in flows)
    w=.95*(mhp*(hh-hi)+mip*(hi-hl)+mlp*(hl-hexhaust))-we
    return {'mHP':mhp,'mIP':mip,'mLP':mlp,'W_before_missing_internal_electric_MW':w,
            'qCCS_MW':qccs,'capture_electric_MW':we,'qFW_MW':qfw,
            'mass_error':mhp-mlp-sum(flows.values()),'CCS_steam_T_C':c['TIP'] if c['x']['CCS'] else c['TLP']}

CASES=[dict(case='Hagenholz_2027',waste_kt_a=375,LHV=11.5,fCO2=1.1,PHP=40,THP=400,PIP=3.5,TIP=139,PLP=1.2,TLP=108,PC=1.2,chi=.96,eta_b=.85,qind=4.2,TR=55,qdh=64.4,minLP=0,Pbase=21.7,
            x=dict(ind=1,WtE=1,CCS=1,DH=0,FW=1)),
       dict(case='Linth',waste_kt_a=110,LHV=11.8,fCO2=1.2,PHP=41,THP=410,PIP=3.5,TIP=139,PLP=3.5,TLP=139,PC=.06,chi=.94,eta_b=.88,qind=0,TR=57,qdh=2.8,minLP=2.1,Pbase=7.5,
            x=dict(ind=1,WtE=0,CCS=0,DH=0,FW=0))]

def main():
    rows=[]
    for c in CASES:
        for hours in [8000,8245,8760]:
            for exact in [False,True]:
                for qi in [0,1.7,3.4]:
                    s0=state(c,hours,0,c['qdh'],qi,exact)
                    s1=state(c,hours,.99,c['qdh'],qi,exact)
                    delta=s0['W_before_missing_internal_electric_MW']-s1['W_before_missing_internal_electric_MW']
                    # Heat limit comes from the printed minimum low-pressure flow,
                    # not a fitted heat-penalty factor. Recovery fraction25% is
                    # a source scenario, not a measured plant heat-recovery curve.
                    qlimit=brentq(lambda q:state(c,hours,.99,q,qi,exact)['mLP']-c['minLP'],0,200)
                    qdr=.25*s1['qCCS_MW']
                    sdr=state(c,hours,.99,qlimit,qi,exact)
                    rows.append(dict(case=c['case'],hours_ASSUMED=hours,internal_heat_ASSUMED_MW=qi,
                                     extraction_state='printed_T_P' if exact else 'saturated_steam',
                                     differential_power_loss_MW=delta,reported_baseline_power_INPUT_MW=c['Pbase'],
                                     differential_loss_relative_to_reported_baseline_percent=100*delta/c['Pbase'],
                                     same_steam_DH_full99_feasible=s1['mLP']>=c['minLP'],
                                     mLP_noCCS=s0['mLP'],mLP_CCS=s1['mLP'],qDH_steam_limit_MW=qlimit,
                                     qDH_with_25pct_direct_RECOVERY_UPPER_MW=qlimit+qdr,
                                     reported_Hagenholz_Table4_DR_ANNUAL_MEAN_MW=53.7 if c['case']=='Hagenholz_2027' else None,
                                     delta_power_at_DR_boundary_MW=s0['W_before_missing_internal_electric_MW']-sdr['W_before_missing_internal_electric_MW'],
                                     max_mass_error=max(abs(s0['mass_error']),abs(s1['mass_error'])),
                                     case_validation='Differential source equation check only. Unknown hours/duties; no full plant reproduction.'))
    with (ROOT/'results/physical_service_caseB_check_r32_20261002.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    lin=[r for r in rows if r['case']=='Linth']
    hag=[r for r in rows if r['case']=='Hagenholz_2027']
    # Differences must cancel the unchanged internal heat duty exactly, not
    # merely happen to agree with a target source output.
    cancellations=[]
    for c in CASES:
        for hour in [8000,8245,8760]:
            for exact in ['saturated_steam','printed_T_P']:
                vals=[r['differential_power_loss_MW'] for r in rows if r['case']==c['case'] and r['hours_ASSUMED']==hour and r['extraction_state']==exact]
                cancellations.append(float(np.ptp(vals)))
    assert max(cancellations)<1e-10
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),cases=len(CASES),rows=len(rows),
                max_internal_heat_cancellation_MW=max(cancellations),max_mass_error=max(r['max_mass_error'] for r in rows),
                linth_penalty_percent_scenario_range=[min(r['differential_loss_relative_to_reported_baseline_percent'] for r in lin),max(r['differential_loss_relative_to_reported_baseline_percent'] for r in lin)],
                linth_published_penalty_percent=37,
                hagenholz_DR_heat_upper_scenario_range_MW=[min(r['qDH_with_25pct_direct_RECOVERY_UPPER_MW'] for r in hag),max(r['qDH_with_25pct_direct_RECOVERY_UPPER_MW'] for r in hag)],
                hagenholz_published_DR_ANNUAL_MEAN_MW=53.7,
                comparison_boundary='Table4 53.7MW is the annual mean of a clipped monthly demand, NOT the instantaneous steam ceiling. Do not compare it with the calculated ceiling as a reproduction error.',
                table4_HP_ledger_check=dict(heat_deficit_MW=64.4-53.7,COP_INPUT=5.5,predicted_net_power_MW=15.3-(64.4-53.7)/5.5,reported_net_power_MW=13.3,
                                            difference_MW=15.3-(64.4-53.7)/5.5-13.3,level='Source output arithmetic consistency, NOT independent steam-cycle validation'),
                hagenholz_unmatched99_count=sum(not r['same_steam_DH_full99_feasible'] for r in hag),
                status='CONDITIONAL: exact differential algebra checks passed; source-range overlap is NOT independent validation.',
                hours_status='8000,8245,8760 are explicit scenarios; 8245 is illustrative, not independently observed operating time.',
                temperature_gate='Zanco2021 permits optimized reboiler temperatures up to150C. The actual10m-packing/99pct solution temperature is not yet supplied:139C steam alone cannot establish a feasible reboiler pinch.')
    (ROOT/'results/physical_service_caseB_check_qc_r32_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
