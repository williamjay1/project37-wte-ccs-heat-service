"""Independent finite transportation LP and cut checks of continuous certificate.

Shared property/source curves are inputs, not frozen scientific outputs. This
does not call the greedy allocator or read its allocations. A 64-case coarse
grid diagnostic checks the nested-cut sufficiency against a general LP solver;
all12 fine-grid lower/upper brackets are checked by independently assembled
cumulative inequalities. These checks supplement, not replace, the proof.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import json
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from certify_continuous_service_domain_r45_20261011 import (
    grid,curves,LOW_HO,HIGH_HO,LOW_HR,HIGH_HR,h,HP99,RECOVERY_SCALE95)

ROOT=Path(__file__).resolve().parents[1]


def inputs(duty,rec,nodes,water_h,source):
    water=duty/(h(100)-h(60))
    hp=min(water,HP99*rec/(h(77)-h(60)))
    load=np.array([(water-hp if top<=77+1e-10 else water)*(b-a)
                   for top,a,b in zip(nodes[1:],water_h[:-1],water_h[1:])])
    hot=[]
    for curve in source.values():
        hot.extend((float(grade),float(q)) for grade,q in zip(nodes[:-1],curve[:-1]-curve[1:]) if q>1e-12)
        if curve[-1]>1e-12:hot.append((100.,float(curve[-1])))
    return load,hot


def independent_cut(load,hot,nodes):
    vals=[sum(load[i:])-sum(q for grade,q in hot if grade>=top-1e-10)
          for i,top in enumerate(nodes[1:])]
    return max(vals)


def transportation_lp(load,hot,nodes):
    edges=[(j,k) for j,(grade,q) in enumerate(hot) for k,top in enumerate(nodes[1:])
           if grade>=top-1e-10]
    assert edges
    columns=np.arange(len(edges));ones=np.ones(len(edges))
    ah=coo_matrix((ones,([j for j,k in edges],columns)),shape=(len(hot),len(edges))).tocsr()
    ac=coo_matrix((ones,([k for j,k in edges],columns)),shape=(len(load),len(edges))).tocsr()
    solved=linprog(np.zeros(len(edges)),A_ub=ah,b_ub=[q for grade,q in hot],
                   A_eq=ac,b_eq=load,bounds=(0,None),method='highs')
    if solved.success:
        residual=float(np.max(np.abs(ac@solved.x-load)))
        assert np.max(ah@solved.x-np.array([q for grade,q in hot]))<1e-7
        return True,residual
    assert solved.status==2, f'Unresolved solver outcome {solved.status}: {solved.message}'
    return False,None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=ROOT)
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args();source=args.data_root.resolve()
    out=args.output_dir.resolve() if args.output_dir else source/'results'
    out.mkdir(parents=True,exist_ok=True)
    dest=out/'continuous_domain_transport_QA_r45_20261011.json'
    if dest.exists():raise FileExistsError('Preserve earlier diagnostics; use a fresh output directory.')
    start=time.monotonic();rng=np.random.default_rng(37046);records=[]
    nodes,steam_cut,water_h=grid(2.)
    for k in range(64):
        capture='99.72' if k%2==0 else '95'
        H=18.5 if capture=='99.72' else 19.9
        rec=1. if capture=='99.72' else RECOVERY_SCALE95
        retained=1. if k%4<2 else .95
        u=rng.random(4)
        H*=retained;rec*=retained;duty=25+17*rng.random()
        branch=curves(nodes,steam_cut,H,rec,LOW_HO+u[0]*(HIGH_HO-LOW_HO),
            LOW_HR+u[1]*(HIGH_HR-LOW_HR),u[2],136+37*u[3])
        load,hot=inputs(duty,rec,nodes,water_h,branch)
        violation=independent_cut(load,hot,nodes)
        feasible,residual=transportation_lp(load,hot,nodes)
        assert feasible==(violation<=1e-7)
        records.append(dict(case=k,capture_percent=capture,retained_duty=retained,
            tested_duty_MW=duty,cut_violation_MW=violation,lp_feasible=feasible,lp_residual_MW=residual))
    fine=[]
    with (source/'results/continuous_service_capacity_r45_20261011.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    for row in rows:
        nodes,steam_cut,water_h=grid(float(row['common_grid_step_K']))
        capture=row['capture_percent'];retained=float(row['retained_duty_DECLARED'])
        H=(18.5 if capture=='99.72' else 19.9)*retained
        rec=(1. if capture=='99.72' else RECOVERY_SCALE95)*retained
        branch=curves(nodes,steam_cut,H,rec,LOW_HO,LOW_HR,0.,136.)
        for which,field in [('lower','continuous_domain_constructed_lower_MW'),
                             ('upper','common_grid_method_failure_upper_MW')]:
            load,hot=inputs(float(row[field]),rec,nodes,water_h,branch)
            v=independent_cut(load,hot,nodes)
            assert (v<=1e-7)==(which=='lower')
            reference=float(row['lower_max_cut_violation_MW' if which=='lower' else 'upper_max_cut_violation_MW'])
            assert abs(v-reference)<1e-8
            fine.append(dict(capture_percent=capture,retained_duty=retained,
                step_K=float(row['common_grid_step_K']),bracket=which,
                violation_MW=v,stored_cut_residual_MW=abs(v-reference)))
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        status='PASS independent transport LP and every fine-grid bracket',
        elapsed_s=time.monotonic()-start,coarse_lp_cases=len(records),
        coarse_lp_feasible=sum(x['lp_feasible'] for x in records),
        coarse_lp_infeasible=sum(not x['lp_feasible'] for x in records),
        max_lp_equality_residual_MW=max(x['lp_residual_MW'] for x in records if x['lp_feasible']),
        fine_brackets_checked=len(fine),max_stored_cut_difference_MW=max(x['stored_cut_residual_MW'] for x in fine),
        lp_cases=records,fine_bracket_checks=fine,
        scope='Independent of greedy allocator; shared property/curve inputs. Not process validation, continuous-coverage proof by sampling, installed HEN or confidence interval.')
    dest.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['lp_cases','fine_bracket_checks']},indent=2))


if __name__=='__main__':main()
