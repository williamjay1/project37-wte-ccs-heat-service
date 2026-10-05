"""A source-anchored temperature/service LP prototype, no backup combustion.

This is NOT a full steam turbine replication or bankable investment model.
Published Su Fuel Table3 backpressure heat/power anchor (99.72% capture).
Heat grades use source Fig6 and text; compressor grade and tank conditions
are EXPLICIT engineering scenarios. Atmospheric water tank maximum 90C
is an analyst constraint pending DEA-specific confirmation, not a DEA quote.
"""
from pathlib import Path
import csv
import json
import sys
from datetime import datetime, timezone
from time import perf_counter
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cache/python_packages_r32'))
from iapws import IAPWS97

def solve(demand, ts, tr, capture_on, cascade, store_hours, *,
          tank_hot_C=90,tank_approach_K=5,usable_capacity_MWh=None,
          store_power_MW=None,flow_limit_kg_s=None,weekly_loss=None,
          charge_efficiency=.9,discharge_efficiency=.9,
          steam_grade_override_C=None,compressor_grade_override_C=None,
          auxiliary_fraction=.02,sources_override=None,return_dispatch=False,
          heatpump_COP=5.5,source_electric_costs=None,availability=None,
          maintained_hot_loss_MW=0,steam_phase_cuts=None,
          water_property_model='constant_cp'):
    n=len(demand); names=['H','overhead','compressor','HP','discharge','chargeH','chargeOH','chargeC','state','unmet']
    if water_property_model not in ['constant_cp','IF97_10bar']:
        raise ValueError('Unknown cold-water property model')
    # Legacy default retained so previous frozen computations remain traceable.
    # The r35 exact-property audit explicitly requests IF97_10bar.
    def cold_fraction(theta):
        if theta<=tr:return 0.
        if theta>=ts:return 1.
        if water_property_model=='constant_cp':return (theta-tr)/(ts-tr)
        h0=IAPWS97(P=1,T=tr+273.15).h;h1=IAPWS97(P=1,T=ts+273.15).h
        return (IAPWS97(P=1,T=theta+273.15).h-h0)/(h1-h0)
    cold_fractions={theta:cold_fraction(theta) for theta in [77,91,97,99,106,121,133.61,158]}
    water_delta=(IAPWS97(P=1,T=ts+273.15).h-IAPWS97(P=1,T=tr+273.15).h)/1000 if water_property_model=='IF97_10bar' else .00418*(ts-tr)
    idx={k:i*n+np.arange(n) for i,k in enumerate(names)}
    H=18.5 if capture_on else 37.3
    grade_H=IAPWS97(P=.4,x=1).T-273.15-10
    if steam_grade_override_C is not None:grade_H=steam_grade_override_C
    compressor_grade=136-15 if compressor_grade_override_C is None else compressor_grade_override_C
    sources=[('H',H,grade_H),('overhead',5.3 if capture_on else 0,106-15),
             ('compressor',1.6 if capture_on else 0,compressor_grade),
             ('HP',9.8*5.5/(5.5-1) if capture_on else 0,77)]
    if sources_override is not None:
        if [s[0] for s in sources_override]!=['H','overhead','compressor','HP']:
            raise ValueError('Explicit heat sources must follow the named physical branches.')
        sources=sources_override
    if heatpump_COP<=1:raise ValueError('Heat-pump COP must exceed one.')
    available=np.ones(n) if availability is None else np.asarray(availability,dtype=float)
    if available.shape!=(n,) or np.any((available<0)|(available>1)):
        raise ValueError('Availability must be a length-n fraction in[0,1].')
    tank_service_C=tank_hot_C-tank_approach_K
    retain=(1-.0018)**(1/24) if weekly_loss is None else (1-weekly_loss)**(1/168)
    rate=37.3 if store_power_MW is None else store_power_MW
    capacity=store_hours*37.3 if usable_capacity_MWh is None else usable_capacity_MWh
    store_active=capacity>0 and rate>0
    if maintained_hot_loss_MW<0 or (maintained_hot_loss_MW>0 and not store_active):
        raise ValueError('A maintained-hot loss requires an active store and nonnegative duty.')
    # All quantities per 1 h time step: MW treated as MWh across the interval.
    bounds=[(0,None)]*(len(names)*n)
    for name,q,temp in sources:
        allow=q if (not cascade or temp>tr) else 0
        for t,j in enumerate(idx[name]): bounds[j]=(0,allow*available[t])
    for name in ['discharge','chargeH','chargeOH','chargeC']:
        for j in idx[name]:bounds[j]=(0,rate if store_active else 0)
    if cascade:
        for source,charge in [('H','chargeH'),('overhead','chargeOH'),('compressor','chargeC')]:
            temp=next(t for a,q,t in sources if a==source)
            if temp<tank_hot_C:
                for j in idx[charge]:bounds[j]=(0,0)
    for j in idx['state']:bounds[j]=(0,capacity)
    for t,j in enumerate(idx['unmet']):bounds[j]=(0,float(demand[t]))
    eqrows=[];eqcols=[];eqval=[];beq=[]
    ubrows=[];ubcols=[];ubval=[];bub=[]
    def row(entries,b,eq=False):
        rr,cc,vv,bb=(eqrows,eqcols,eqval,beq) if eq else (ubrows,ubcols,ubval,bub)
        r=len(bb)
        for col,val in entries:rr.append(r);cc.append(int(col));vv.append(val)
        bb.append(b)
    for t in range(n):
        row([(idx[k][t],1) for k in ['H','overhead','compressor','HP','discharge','unmet']],float(demand[t]),True)
        row([(idx['state'][(t+1)%n],1),(idx['state'][t],-retain),
             (idx['chargeH'][t],-charge_efficiency),(idx['chargeOH'][t],-charge_efficiency),(idx['chargeC'][t],-charge_efficiency),
             (idx['discharge'][t],1/discharge_efficiency)],-maintained_hot_loss_MW,True)
        for name,charge in [('H','chargeH'),('overhead','chargeOH'),('compressor','chargeC')]:
            q=next(q for k,q,temp in sources if k==name)
            row([(idx[name][t],1),(idx[charge][t],1)],q*available[t])
        row([(idx[k][t],1) for k in ['chargeH','chargeOH','chargeC']],rate)
        if flow_limit_kg_s is not None:
            # DEA water heat-capacity approximation4.18kJ/kg/K, exact units:
            # kg/s * MJ/kg/K * K = MJ/s = MW. No free network flow upgrade.
            row([(idx['unmet'][t],-1)],float(flow_limit_kg_s*water_delta-demand[t]))
        if cascade:
            grades={k:temp for k,q,temp in sources}; grades['discharge']=tank_service_C
            # Composite cold-stream cascade: heat below theta cannot cover the
            # upper-temperature fraction of the service. Guarantees no 77C
            # heat is silently counted as full 120C heat. Intermediate preheat
            # is allowed (not simply discarding all lower-temperature heat).
            for theta in sorted(set(grades.values())):
                if theta<ts:
                    if theta not in cold_fractions:cold_fractions[theta]=cold_fraction(theta)
                    fraction=cold_fractions[theta]
                    entries=[(idx[k][t],1) for k in grades if grades[k]<=theta]
                    entries.append((idx['unmet'][t],float(fraction)))
                    row(entries,float(demand[t]*fraction))
            # Optional thermodynamic OUTER cuts. A steam branch may have a high
            # inlet temperature but only a limited superheat duty above its
            # condensation plateau. cap is the maximum available steam duty
            # above theta, NOT an assumed fraction of delivered steam duty.
            # Other high-grade branches remain optimistic rectangles; storage
            # charging may consume low-grade steam heat, so no arbitrary
            # superheat subtraction is imposed on charging.
            for cut in (steam_phase_cuts or []):
                theta,cap=cut[:2]
                if tr < theta < ts:
                    upper_fraction=cut[2] if len(cut)>2 else (ts-theta)/(ts-tr)
                    if not 0<upper_fraction<1:raise ValueError('Invalid cold-stream upper enthalpy fraction')
                    entries=[(idx['unmet'][t],-upper_fraction)]
                    entries += [(idx[k][t],-1) for k in grades
                                if k!='H' and grades[k]>theta]
                    row(entries,float(cap*available[t]-demand[t]*upper_fraction))
    N=n*len(names)
    Aeq=sparse.coo_matrix((eqval,(eqrows,eqcols)),shape=(len(beq),N)).tocsr()
    Aub=sparse.coo_matrix((ubval,(ubrows,ubcols)),shape=(len(bub),N)).tocsr()
    objective=np.zeros(N);objective[idx['unmet']]=1e4
    objective[idx['HP']]=1/heatpump_COP
    if source_electric_costs:
        for name,cost in source_electric_costs.items():
            objective[idx[name]]+=float(cost)
            charging={'H':'chargeH','overhead':'chargeOH','compressor':'chargeC'}.get(name)
            if charging:objective[idx[charging]]+=float(cost)
    # Workbook auxiliary energy is a fraction of heat OUTPUT. Do not charge
    # it twice on charging and discharging. A vanishing charge regularizer
    # only breaks degenerate cycles; it is not an energy or monetary cost.
    objective[idx['discharge']]=auxiliary_fraction
    for k in ['chargeH','chargeOH','chargeC']:objective[idx[k]]=1e-8
    start=perf_counter()
    sol=linprog(objective,Aub,bub,Aeq,beq,bounds=bounds,method='highs')
    elapsed=perf_counter()-start
    if not sol.success:raise RuntimeError(sol.message)
    z={k:sol.x[ii] for k,ii in idx.items()}
    residual_eq=float(np.max(np.abs(Aeq@sol.x-beq)))
    residual_ub=float(np.max(np.maximum(Aub@sol.x-bub,0)))
    assert max(residual_eq,residual_ub)<1e-6
    result=dict(capture_on=capture_on,model='temperature_cascade' if cascade else 'aggregate_heat',
                supply_temperature_C=ts,return_temperature_C=tr,store_hours=store_hours,
                demand_MWh=float(np.sum(demand)),unserved_MWh=float(np.sum(z['unmet'])),
                unserved_peak_MW=float(np.max(z['unmet'])),unserved_hours=int(np.count_nonzero(z['unmet']>1e-6)),
                service_feasible=bool(np.max(z['unmet'])<1e-6),
                heatpump_electric_MWh=float(np.sum(z['HP'])/heatpump_COP),
                store_discharge_MWh=float(np.sum(z['discharge'])),
                store_auxiliary_electric_MWh=float(auxiliary_fraction*np.sum(z['discharge'])),
                max_eq_error=residual_eq,max_ub_violation=residual_ub,solver_seconds=elapsed,
                storage_hot_C=tank_hot_C,storage_approach_K=tank_approach_K,
                storage_usable_capacity_MWh=capacity,storage_power_limit_MW=rate,
                hydraulic_flow_limit_kg_s=flow_limit_kg_s,
                assumed_heatpump_COP=heatpump_COP,
                maintained_hot_loss_MW_SCENARIO=maintained_hot_loss_MW,
                unavailable_hours=int(np.count_nonzero(available==0)),
                bounds_layer='Source-anchored differential heat prototype. Tank/grades structural scenarios, not factory validation.')
    if return_dispatch:result['_dispatch']=z
    if steam_phase_cuts is not None:
        result['steam_phase_cut_count']=sum(tr<cut[0]<ts for cut in steam_phase_cuts)
    return result

def main():
    rows=[]
    # Pilot deliberately avoids claiming 8,784 independent observations.
    # Full public-year matrices follow only after case-B source gate closes.
    for profile,demand in [('constant_service',np.full(168,36.5)),
                           ('synthetic_week',36.5*(1+.22*np.cos(np.arange(168)/168*2*np.pi)))]:
        for ts in [80,100,120]:
            for store_hours in [0,24,168]:
                for cascade in [False,True]:
                    for capture in [False,True]:
                        r=solve(demand,ts,60,capture,cascade,store_hours)
                        r['profile']=profile;rows.append(r)
    path=ROOT/'results/physical_service_feasibility_pilot_r32_20261002.csv'
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    paired=[]
    for r in rows:
        if not r['capture_on']:continue
        other=next(v for v in rows if not v['capture_on'] and all(v[k]==r[k] for k in ['profile','model','supply_temperature_C','store_hours']))
        paired.append(dict(profile=r['profile'],model=r['model'],temperature=r['supply_temperature_C'],store_hours=r['store_hours'],
                           both_service_feasible=bool(r['service_feasible'] and other['service_feasible']),
                           noCCS_service_feasible=other['service_feasible'],CCS_service_feasible=r['service_feasible'],
                           CCS_unserved_MWh=r['unserved_MWh'],noCCS_unserved_MWh=other['unserved_MWh']))
    flags=[]
    for p in paired:
        if p['model']!='aggregate_heat':continue
        q=next(v for v in paired if v['model']=='temperature_cascade' and all(v[k]==p[k] for k in ['profile','temperature','store_hours']))
        if p['both_service_feasible'] and not q['both_service_feasible']:flags.append(q)
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),LPs=len(rows),pairs=len(paired),
                false_service_feasibility_count=len(flags),false_service_feasibility_cases=flags,
                max_eq_error=max(r['max_eq_error'] for r in rows),max_ub_violation=max(r['max_ub_violation'] for r in rows),
                total_solver_seconds=sum(r['solver_seconds'] for r in rows),
                status='PROTOTYPE PASS, not two-source full process-validation gate',
                main_boundary='Feasibility first: do not calculate matched-service carbon thresholds or investment ranks for infeasible pairs. No backup fuel allowed.',
                novel_claim_status='Candidate wrong-order/service mechanism demonstrated in declared scenarios; full independent-case and cost ranking pending.',
                matrix_scope='Published Su BP anchor only; 168h constant/synthetic week, NOT full public demand years; tanks/temperature grades are scenarios.')
    (ROOT/'results/physical_service_feasibility_qc_r32_20261002.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
