"""Continuous declared-domain certificate on a COMMON finite temperature grid.

Analytical monotonicity, not random sampling, establishes coverage. At fixed
total branch duties, source heat above a cold-side grade is minimized at the
lowest steam inlet/return enthalpies, zero overhead plateau and lowest
compressor inlet. Clip functions retain equality at phase/plateau boundaries.
For primary100/60C all steam thresholds are liquid below4bar saturation.

Global shifted-grade bins preserve cumulative dominance. A positive nested
cut/finite allocation at the dominating worst profile supports adaptive
thermal constructions for every profile within the rectangular domain, not
one installed exchanger network or annual reliability. This is not a new
pinch algorithm, measured probability, process validation or bankable TEA.
"""
from pathlib import Path
from datetime import datetime, timezone
import csv
import argparse
import heapq
import json
import time

import numpy as np
from construct_finite_heat_path_20261011 import (
    h, HP99, RECOVERY_SCALE95, ISENTROPIC, INLET, RETURN_COLD, SAT_LIQUID)
from iapws import IAPWS97

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'
TS, TR, HP_OUT=100., 60., 77.
LOW_HO, HIGH_HO=ISENTROPIC.h/1000, INLET.h/1000
LOW_HR, HIGH_HR=RETURN_COLD, SAT_LIQUID.h/1000


def grid(step):
    # Explicit common fixed nodes, not state-dependent linspace subdivision.
    nodes=np.concatenate([np.linspace(TR,HP_OUT,round((HP_OUT-TR)/step)+1),
                          np.linspace(HP_OUT,TS,round((TS-HP_OUT)/step)+1)[1:]])
    steam_cut=np.array([IAPWS97(P=.4,T=float(c)+10+273.15).h/1000 for c in nodes])
    assert max(nodes)+10<IAPWS97(P=.4,x=0).T-273.15
    water_h=np.array([h(float(c)) for c in nodes])
    return nodes,steam_cut,water_h


def curves(nodes,steam_cut,H,rec,ho,hr,fraction,comp):
    # Derivatives in the unclipped interior: dQsteam/dho>=0, dQsteam/dhr>=0.
    steam=H*np.clip((ho-np.maximum(hr,steam_cut))/(ho-hr),0,1)
    sensible=np.clip((106-(nodes+15))/36,0,1)
    plateau=(nodes+15<=106+1e-10).astype(float)
    overhead=rec*5.3*((1-fraction)*sensible+fraction*plateau)
    compression=rec*1.6*np.clip((comp-(nodes+15))/(comp-70),0,1)
    return dict(steam=steam,overhead=overhead,compression=compression)


def hot_chunks(nodes,by_branch):
    chunks=[]
    for name,curve in by_branch.items():
        delta=10. if name=='steam' else 15.
        for i,q in enumerate(curve[:-1]-curve[1:]):
            assert q>=-1e-9
            if q>1e-12:
                chunks.append(dict(branch=name,shifted_low_C=float(nodes[i]),
                                   approach_K=delta,available_MW=float(q)))
        if curve[-1]>1e-12:
            chunks.append(dict(branch=name,shifted_low_C=TS,approach_K=delta,
                               available_MW=float(curve[-1])))
    return chunks


def cold_required(duty,rec,nodes,water_h):
    mass=duty/(h(TS)-h(TR))
    hp_module_mass=HP99*rec/(h(HP_OUT)-h(TR))
    hp_mass=min(mass,hp_module_mass)
    masses=np.where(nodes[1:]<=HP_OUT+1e-10,mass-hp_mass,mass)
    cold=masses*np.diff(water_h)
    assert abs(cold.sum()+hp_mass*(h(HP_OUT)-h(TR))-duty)<1e-8
    return cold,mass,hp_mass


def cut(duty,rec,nodes,water_h,by_branch):
    # Independent nested cuts; does not call or read the allocator.
    required,_,_=cold_required(duty,rec,nodes,water_h)
    cumulative_required=np.cumsum(required[::-1])[::-1]
    available=sum(by_branch.values())[1:]
    violations=cumulative_required-available
    index=int(np.argmax(violations))
    return float(violations[index]),float(nodes[index+1])


def allocate(duty,rec,nodes,water_h,chunks,rec_nominal):
    required,mass,hp_mass=cold_required(duty,rec,nodes,water_h)
    ranked=sorted(enumerate(chunks),key=lambda z:z[1]['shifted_low_C'],reverse=True)
    remain=[c['available_MW'] for c in chunks]
    active=[];pos=0;unmet=0.;alloc=[]
    for i in reversed(range(len(required))):
        top=float(nodes[i+1]);need=float(required[i])
        while pos<len(ranked) and ranked[pos][1]['shifted_low_C']>=top-1e-10:
            j,c=ranked[pos];heapq.heappush(active,(c['shifted_low_C'],j));pos+=1
        while need>1e-10 and active:
            _,j=heapq.heappop(active);c=chunks[j]
            q=min(need,remain[j]);dT=c['shifted_low_C']+c['approach_K']-top
            assert dT>=c['approach_K']-1e-8
            alloc.append(dict(branch=c['branch'],source_chunk=j,cold_low_C=float(nodes[i]),
                cold_high_C=top,shifted_hot_low_C=c['shifted_low_C'],exchanged_MW=q,
                minimum_dT_K=dT,sufficient_UA_MW_K=q/dT))
            need-=q;remain[j]-=q
            if remain[j]>1e-10:heapq.heappush(active,(c['shifted_low_C'],j))
        unmet+=max(0.,need)
    delivered=sum(r['exchanged_MW'] for r in alloc)
    hp=hp_mass*(h(HP_OUT)-h(TR))
    assert abs(hp+delivered+unmet-duty)<1e-7
    assert min(remain)>-1e-9
    return dict(unmet_MW=unmet,primary_flow_kg_s=mass,hp_delivered_MW=hp,
        hp_nominal_module_duty_MW=HP99*rec_nominal,
        hp_unavailable_or_rejected_MW=HP99*rec_nominal-hp,
        hp_full_power_MW=HP99*rec_nominal/5.5,sufficient_UA_MW_K=sum(r['sufficient_UA_MW_K'] for r in alloc),
        constructed=unmet<1e-7),alloc


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=OUT)
    args=parser.parse_args();OUT=args.output_dir.resolve()
    start=time.monotonic();OUT.mkdir(exist_ok=True)
    names=['continuous_service_domain_r45_20261011.json',
           'continuous_service_capacity_r45_20261011.csv',
           'continuous_service_allocation_r45_20261011.csv']
    if any((OUT/n).exists() for n in names):
        raise FileExistsError('Preserve existing outputs; recompute in a fresh checkout.')
    tables={s:grid(s) for s in [.2,.1,.05]}
    rows=[];detail=[]
    for retained in [1.,.95]:
        for design,H,rec in [('99.72',18.5,1.),('95',19.9,RECOVERY_SCALE95)]:
            rec_nominal=rec
            H*=retained;rec*=retained
            for step,(nodes,steam_cut,water_h) in tables.items():
                worst=curves(nodes,steam_cut,H,rec,LOW_HO,LOW_HR,0.,136.)
                chunks=hot_chunks(nodes,worst)
                lo,hi=20.,41.
                assert cut(lo,rec,nodes,water_h,worst)[0]<=1e-7
                assert cut(hi,rec,nodes,water_h,worst)[0]>1e-7
                while hi-lo>.001:
                    mid=(lo+hi)/2
                    if cut(mid,rec,nodes,water_h,worst)[0]<=1e-7:lo=mid
                    else:hi=mid
                low,a=allocate(lo,rec,nodes,water_h,chunks,rec_nominal)
                high,_=allocate(hi,rec,nodes,water_h,chunks,rec_nominal)
                nominal,_=allocate(36.5,rec,nodes,water_h,chunks,rec_nominal)
                lv,lt=cut(lo,rec,nodes,water_h,worst)
                uv,ut=cut(hi,rec,nodes,water_h,worst)
                assert low['constructed'] and not high['constructed']
                assert abs(high['unmet_MW']-uv)<1e-7
                row=dict(capture_percent=design,retained_duty_DECLARED=retained,
                    common_grid_step_K=step,continuous_domain_constructed_lower_MW=lo,
                    common_grid_method_failure_upper_MW=hi,width_MW=hi-lo,
                    lower_max_cut_violation_MW=lv,upper_max_cut_violation_MW=uv,
                    upper_controlling_cold_grade_C=ut,
                    nominal_contract_constructed=nominal['constructed'],
                    nominal_contract_unmet_MW=nominal['unmet_MW'],**low)
                rows.append(row)
                if step==.1:
                    detail.extend([dict(capture_percent=design,retained_duty_DECLARED=retained,
                                        certified_service_MW=lo,**r) for r in a])
    # These finite diagnostics are not the proof of continuous coverage.
    nodes,steam_cut,_=tables[.1]
    rng=np.random.default_rng(37045)
    smallest={name:float('inf') for name in ['steam','overhead','compression']}
    worst=curves(nodes,steam_cut,18.5,1.,LOW_HO,LOW_HR,0.,136.)
    for _ in range(512):
        u=rng.random(4)
        candidate=curves(nodes,steam_cut,18.5,1.,
            LOW_HO+u[0]*(HIGH_HO-LOW_HO),LOW_HR+u[1]*(HIGH_HR-LOW_HR),
            u[2],136+u[3]*37)
        for name in smallest:
            margin=float(np.min(candidate[name]-worst[name]))
            smallest[name]=min(smallest[name],margin)
            assert margin>=-1e-9
    for name,values in [(names[1],rows),(names[2],detail)]:
        with (OUT/name).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        status='PASS common-grid finite constructions and analytical worst-profile dominance',
        elapsed_s=time.monotonic()-start,primary_C=[100,60],customer_C=[80,50],
        domain=dict(steam_inlet_MJ_kg=[LOW_HO,HIGH_HO],steam_return_MJ_kg=[LOW_HR,HIGH_HR],
                    overhead_plateau_fraction=[0,1],compressor_inlet_C=[136,173]),
        derivative_signs=dict(steam_inlet='nonnegative',steam_return='nonnegative',
                              overhead_fraction='nonnegative',compressor_inlet='nonnegative'),
        analytical_scope='Clipped cumulative branch heat on cold-side grades60..100C; steam thresholds below saturation. Common-grid dominance and nested matching imply adaptive finite thermal existence at the lower bracket.',
        finite_sampling_check=dict(samples=512,seed=37045,grades=len(nodes),
                                   minimum_branch_cumulative_margin_MW=smallest,
                                   role='Falsification diagnostic, not coverage proof or probability'),
        capacity_brackets=rows,
        limits=['Declared rectangular thermal family, not an empirically complete uncertainty set.',
                'Different adaptive allocations may be needed; not one installed HEN or annual firm service.',
                '95% recovery remains proportional calibration. Useful-heat derating retains nominal module electricity; unavailable/unused hot output is rejected, not credited. No validated part-load curve.',
                'Upper failure is common-grid-method failure, not a global physical upper bound.',
                'Capacity tests do not rescale the36.5MW financial ledger or validate joint steam/electric operation.'])
    (OUT/names[0]).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=report['status'],elapsed_s=report['elapsed_s'],
                          capacity_brackets=rows,diagnostic=report['finite_sampling_check']),indent=2))


if __name__=='__main__':main()
