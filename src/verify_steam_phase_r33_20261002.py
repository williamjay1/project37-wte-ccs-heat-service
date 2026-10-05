"""Independent formulas/dense state checks; never compare a model with itself."""
from pathlib import Path
import sys,csv,json,math
from datetime import datetime,timezone
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cache/python_packages_r32'))
from iapws import IAPWS97
def read(name):
    with (ROOT/'results'/name).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def val(r,k):return float(r[k])
def true(r,k):return r[k]=='True'
def compare(a,b):
    err=abs(a-b)/max(1,abs(a),abs(b))
    assert err<1e-9,(a,b,err)
    return err
def main():
    obj=json.loads((ROOT/'results/steam_phase_domain_qc_r33_20261002.json').read_text())
    hp=IAPWS97(P=6,T=673.15);sf=IAPWS97(P=.4,x=0);sg=IAPWS97(P=.4,x=1)
    isentropic=IAPWS97(P=.4,s=hp.s);ret=IAPWS97(P=.4,T=333.15)
    rho=(hp.h-sg.h)/(hp.h-sf.h)
    lower=min((min(ent,sg.h)-sf.h)/(ent-ret.h) for ent in (isentropic.h,hp.h))
    errors=[compare(rho,obj['su_bracket']['superheat_fraction_upper']),
            compare(lower,obj['su_bracket']['latent_fraction_lower'])]
    # Dense state coverage is a numerical check of an analytic monotonic proof,
    # not a Monte Carlo confidence statement. All permitted condensate returns
    # are tested independently of the production solver.
    hs=np.linspace(isentropic.h,hp.h,10001)
    latent_min=1.;super_max=0.;states=0
    for hr in np.linspace(ret.h,sf.h,41):
        latent=np.maximum(0,np.minimum(hs,sg.h)-sf.h)/(hs-hr)
        high=np.maximum(0,hs-sg.h)/(hs-hr)
        latent_min=min(latent_min,float(latent.min()))
        super_max=max(super_max,float(high.max()));states+=len(hs)
    assert latent_min>=lower-1e-12 and super_max<=rho+1e-12
    errors += [compare(latent_min,lower),compare(super_max,rho)]
    su=read('steam_phase_su_matrix_r33_20261002.csv')
    for r in su:
        # The phase cut is exactly inactive in the previous100/120C main screen.
        if r['phase_model']=='bounded_superheat' and val(r,'supply_temperature_C')<=120:
            p=next(x for x in su if x['phase_model']=='rectangular_high_steam' and all(x[k]==r[k] for k in ('demand_MW','supply_temperature_C','volume_m3','capture_on')))
            errors += [compare(val(r,k),val(p,k)) for k in ('unserved_MWh','heatpump_electric_MWh')]
        if r['phase_model']=='bounded_superheat' and val(r,'supply_temperature_C')==160:
            H=18.5 if true(r,'capture_on') else 37.3
            qhigh=H*rho+(1.6 if true(r,'capture_on') else 0)
            top=IAPWS97(P=1,T=433.15).h
            bottom=IAPWS97(P=1,T=333.15).h
            mid=IAPWS97(P=1,T=sg.T-10).h
            maximum=qhigh/( (top-mid)/(top-bottom) )
            D=val(r,'demand_MW')
            # Other cuts can be limiting at very high demand. Restrict exact
            # comparison to the source rows where the phase cut is demonstrably
            # the tightest constraint; do not presume equality for every pass.
            if D>=maximum:
                errors.append(compare(val(r,'unserved_MWh'),168*(D-maximum)))
    swiss=read('steam_phase_swiss_transfer_r33_20261002.csv')
    for r in swiss:
        ts=val(r,'supply_temperature_C');tr=val(r,'return_temperature_C')
        H=val(r,'steam_limit_MW');D=val(r,'demand_MWh')/168
        p=1.2 if r['case']=='Hagenholz_2027' else 3.5
        t=108 if p==1.2 else 139
        approach=val(r,'approach_SCENARIO_K')
        sat=IAPWS97(P=p/10,x=1);hin=IAPWS97(P=p/10,T=t+273.15)
        liquid=IAPWS97(P=.1,T=tr+273.15)
        fraction=max(0,hin.h-sat.h)/(hin.h-liquid.h)
        theta=sat.T-273.15-approach
        maximum=H if t-approach>=ts else 0
        if r['phase_model']=='printed_condensation_curve' and theta<ts:
            top=IAPWS97(P=1,T=ts+273.15).h
            mid=IAPWS97(P=1,T=theta+273.15).h
            bottom=IAPWS97(P=1,T=tr+273.15).h
            maximum=min(maximum,H*fraction*(top-bottom)/(top-mid))
        errors.append(compare(val(r,'unserved_MWh'),168*max(0,D-maximum)))
    cert=read('steam_phase_constructive_certificate_r33_20261002.csv')
    for r in cert:
        D=val(r,'delivered_heat_MW');ts=val(r,'primary_supply_C');tr=val(r,'primary_return_C')
        a=sg.T-273.15-ts;b=sg.T-273.15-tr
        dlm=(b-a)/math.log(b/a)
        # Independent composite integration with10,001 intervals, not the
        # production adaptive quadrature. Numerical quadrature tolerance is
        # distinct from the algebraic identity tolerance.
        grid=np.linspace(tr,ts,10001)
        integral=np.trapezoid([IAPWS97(P=1,T=t+273.15).cp/1000/(sg.T-273.15-t) for t in grid],grid)
        ua=val(r,'water_flow_required_kg_s')*integral
        assert abs(ua-val(r,'exchanger_UA_required_MW_K'))<2e-9
        delta_h=(IAPWS97(P=1,T=ts+273.15).h-IAPWS97(P=1,T=tr+273.15).h)/1000
        errors += [compare(val(r,'constant_cp_UA_comparator_MW_K')*dlm,D),
                   compare(val(r,'water_flow_required_kg_s')*delta_h,D)]
        assert val(r,'minimum_approach_K')>=10
        assert val(r,'guaranteed_latent_available_MW')>=D-1e-10
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS independent steam-phase formulas and dense-state bounds',
        state_grid_evaluations=states,Su_rows=len(su),Swiss_rows=len(swiss),certificate_rows=len(cert),
        maximum_scaled_error=max(errors),comparisons=len(errors),
        actual_dense_minimum_latent_fraction=latent_min,actual_dense_maximum_superheat_fraction=super_max,
        validation_level='Analytic/implementation verification only; not independent operational or proprietary process-simulator validation.')
    (ROOT/'results/steam_phase_verification_r33_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
