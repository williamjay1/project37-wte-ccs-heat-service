"""Bracket declared-route service with finite inner and continuum outer cuts.

This is not a field rating or a globally optimal installed heat-exchanger
network.  The HP module, its 60 -> 77 C carrier, and the declared independent
thermal-source family are fixed. A single continuum cut is a valid necessary
upper bound even if no global minimizer has been certified. Point searching
selects tighter witnesses, not proof of global continuous optimization.

The earlier finite-grid failure upper is recorded separately: it is NOT used
as the physical outer bound. Frozen finite lower outputs are inputs only to
the reported bracket, not to the independently calculated continuum cut.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import json
import time

import numpy as np
from certify_continuous_service_domain_r45_20261011 import (
    curves, LOW_HO, LOW_HR, h, HP99, RECOVERY_SCALE95)
from iapws import IAPWS97

ROOT = Path(__file__).resolve().parents[1]


def upper_cut(theta, H, rec):
    """Independent cold-side cumulative enthalpy balance at one exact grade."""
    a = (h(100.) - h(theta)) / (h(100.) - h(60.))
    b = max(0., (h(77.) - h(theta)) / (h(77.) - h(60.)))
    liquid_cut = IAPWS97(P=.4, T=theta + 10 + 273.15).h / 1000
    by_branch = curves(np.array([theta]), np.array([liquid_cut]),
                       H, rec, LOW_HO, LOW_HR, 0., 136.)
    c = sum(float(v[0]) for v in by_branch.values())
    hp = HP99 * rec
    return dict(cold_grade_C=theta, cold_above_fraction=a,
                hp_above_fraction=b, eligible_non_hp_MW=c,
                hp_delivered_module_MW=hp,
                continuum_necessary_upper_MW=(c + hp * b) / a,
                nominal_contract_cut_deficit_MW=36.5 * a - hp * b - c)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lower-csv', type=Path, default=ROOT/'results'/
        'continuous_service_capacity_r45_20261011.csv')
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.exists():
        raise FileExistsError('Use a new output directory; retain prior receipts.')
    out.mkdir(parents=True)
    start = time.monotonic()
    with args.lower_csv.open(newline='', encoding='utf-8') as f:
        inner = list(csv.DictReader(f))
    # Exact module and source breakpoints are included, not displaced by an
    # interval width. Any one of these evaluated cuts is a valid upper.
    grades = np.unique(np.concatenate([np.arange(60., 100., .1), [60., 77., 91.]]))
    rows, witnesses = [], []
    for retained in [1., .95]:
        for capture, base_H, base_rec in [('99.72', 18.5, 1.),
                                        ('95', 19.9, RECOVERY_SCALE95)]:
            H, rec = base_H * retained, base_rec * retained
            cuts = [upper_cut(float(t), H, rec) for t in grades]
            best = min(cuts, key=lambda z:z['continuum_necessary_upper_MW'])
            hp_carrier_min = HP99 * rec * (h(100.) - h(60.)) / (h(77.) - h(60.))
            assert best['continuum_necessary_upper_MW'] > hp_carrier_min
            # Explicit fixed witnesses make the bound independently reviewable.
            for theta in [60., 77., 91.]:
                witnesses.append(dict(capture_percent=capture,
                    retained_duty_DECLARED=retained, **upper_cut(theta, H, rec)))
            selected = [z for z in inner if z['capture_percent']==capture and
                        float(z['retained_duty_DECLARED'])==retained]
            assert len(selected)==3
            for lower in selected:
                duty = float(lower['continuous_domain_constructed_lower_MW'])
                grid_upper = float(lower['common_grid_method_failure_upper_MW'])
                gap = best['continuum_necessary_upper_MW'] - duty
                assert gap >= 0
                # Scale covariance follows from proportional heat derating,
                # not a new module power/steam-cycle performance claim.
                row = dict(capture_percent=capture, retained_duty_DECLARED=retained,
                    common_grid_step_K=float(lower['common_grid_step_K']),
                    finite_constructed_lower_MW=duty,
                    finite_grid_failure_upper_NOT_physical_MW=grid_upper,
                    continuum_witness_grade_C=best['cold_grade_C'],
                    continuum_necessary_upper_MW=best['continuum_necessary_upper_MW'],
                    inner_outer_gap_MW=gap,
                    gap_fraction_of_outer=gap/best['continuum_necessary_upper_MW'],
                    target_retained_fraction_sufficient=36.5/duty*retained,
                    target_retained_fraction_necessary=36.5/best['continuum_necessary_upper_MW']*retained,
                    nominal_contract_cut_deficit_MW=best['nominal_contract_cut_deficit_MW'],
                    nominal_contract_excluded_for_worst_profile=
                        bool(best['nominal_contract_cut_deficit_MW']>1e-9),
                    hp_carrier_minimum_service_MW=hp_carrier_min)
                rows.append(row)
    for name, values in [('continuum_inner_outer_brackets_r46_20261011.csv',rows),
                         ('continuum_cut_witnesses_r46_20261011.csv',witnesses)]:
        with (out/name).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(values[0]))
            writer.writeheader();writer.writerows(values)
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        status='PASS finite inner constructions below independent continuum necessary cuts',
        elapsed_s=time.monotonic()-start, exact_fixed_witnesses_C=[60.,77.,91.],
        search_points=len(grades), capacity_brackets=rows,
        derivation='For fixed60->77C HP direct carrier, heat above theta is D*A(theta)-Qhp*B(theta), where A=(h100-h(theta))/(h100-h60), B=max((h77-h(theta))/(h77-h60),0). It cannot exceed eligible non-HP cumulative source heat C(theta).',
        homogeneous_thermal_derating='Scaling every hot duty and water flow by retained fraction scales the constructed service and every point-cut upper linearly; nominal HP electricity is not scaled. Necessary and sufficient retained fractions are D/outer and D/inner respectively, not a measured outage or uncertainty probability.',
        proof_scope='Each evaluated cut is independently necessary. No claim of global minimizer or finite hardware at the outer equality. The common source-domain guarantee is bounded above by one admissible worst thermal profile.',
        limits=['Applies to the declared fixed HP routing and source family, not all conceivable HP integration technologies.',
                'Rectangular thermal state family and95% proportional calibration are not a validated joint turbine/power/capture feasible set.',
                'A worst-profile exclusion refutes a family-wide36.5MW guarantee, not the feasible central99.72% case or every factory.',
                'The finite-grid failure upper is kept separate from the continuum necessary upper.',
                'Useful thermal derating does not confer a power-efficiency credit or recompute capture/economic ledgers.'])
    (out/'continuum_outer_cut_certificate_r46_20261011.json').write_text(
        json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
