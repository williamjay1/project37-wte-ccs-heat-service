"""Conditional sensible/condensing recovery families, NOT measured composites.

Su 2023 prints the overhead endpoints 106 -> 70 C, compressor inlet
temperatures 136/164/173 C -> 70 C and total recovered duties. It does not
give the segment heat allocation needed here. A declared constant heat
capacity sensible profile and a declared overhead condensation fraction
therefore test structure; neither is inferred from source data or given
an empirical probability. The other assumptions follow the steam audit.

Outputs: source-documented structural flow frontier, with infeasible rows
retained. No new climate/cost, plant validation, UA hardware or hourly
reliability is claimed. This extension is an ideal composite cut screen.
"""
from pathlib import Path
from datetime import datetime, timezone
from functools import lru_cache
import csv
import json
import sys

import numpy as np
from scipy.optimize import brentq, minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cache/python_packages_r32'))
from audit_primary_margin_20261011 import h, ua_for_same_secondary
from audit_steam_composite_margin_20261011 import (
    D, TR, Q_STEAM, APPROACH, ISENTROPIC, INLET, RETURN_COLD,
    SAT_LIQUID, PHASE_GRADE, threshold_h)

Q_HP = 9.8 * 5.5 / 4.5
Q_OH, OH_IN, HOT_RETURN, OH_APPROACH = 5.3, 106.0, 70.0, 15.0
Q_COMP, COMP_APPROACH = 1.6, 15.0


def sensible_fraction(theta, t_in, approach):
    return float(np.clip((t_in - max(HOT_RETURN, theta + approach))
                         / (t_in - HOT_RETURN), 0, 1))


def q_above(theta, ho, hr, fraction, comp_in):
    steam = Q_STEAM * np.clip((ho - max(hr, threshold_h(theta)))
                              / (ho - hr), 0, 1)
    # fraction is a DECLARED duty fraction at the 106 C upper plateau.
    # It is not inferred as an actual overhead latent fraction.
    overhead = Q_OH * (fraction * (OH_IN - OH_APPROACH > theta)
                       + (1 - fraction) * sensible_fraction(theta, OH_IN, OH_APPROACH))
    compressor = Q_COMP * sensible_fraction(theta, comp_in, COMP_APPROACH)
    return float(steam + overhead + compressor + Q_HP * (77.0 > theta))


def critical_flow(ho, hr, fraction, comp_in):
    if q_above(TR, ho, hr, fraction, comp_in) < D - 1e-10:
        return None, None
    knots = sorted(set([TR + 1e-7, 77.0, 91.0, PHASE_GRADE,
                        comp_in - COMP_APPROACH, 160.0]))
    def cut(t):
        return max(0.0, D - q_above(t, ho, hr, fraction, comp_in)) / (h(t) - h(TR))
    candidates = [(cut(t), t) for t in knots]
    for lower, upper in zip(knots[:-1], knots[1:]):
        r = minimize_scalar(lambda t: -cut(t), bounds=(lower + 1e-6, upper - 1e-6),
                            method='bounded', options={'xatol': 1e-9})
        candidates.append((-float(r.fun), float(r.x)))
    return max(candidates)


def main():
    rows, summary = [], []
    for ho_name, ho in [('isentropic', ISENTROPIC.h / 1000),
                         ('inlet_enthalpy_upper', INLET.h / 1000)]:
        for hr_name, hr in [('60C_lower', RETURN_COLD),
                             ('saturated_liquid_upper', SAT_LIQUID.h / 1000)]:
            for comp_in in [136.0, 173.0]:
                low = q_above(TR, ho, hr, 0.0, comp_in)
                high = q_above(TR, ho, hr, 1.0, comp_in)
                fraction_min = max(0.0, (D - low) / (high - low))
                summary.append(dict(steam_domain=ho_name, return_domain=hr_name,
                                    compressor_inlet_C=comp_in,
                                    aggregate_at_fraction0_MW=low,
                                    aggregate_at_fraction1_MW=high,
                                    minimum_overhead_plateau_fraction_aggregate=fraction_min))
                for fraction in np.linspace(0.0, 1.0, 41):
                    flow, cut = critical_flow(ho, hr, float(fraction), comp_in)
                    ts = (brentq(lambda t: h(t) - h(TR) - D / flow, 65, 140, xtol=1e-10)
                          if flow is not None else None)
                    interface_ok = ts is not None and ts >= 85.0
                    rows.append(dict(
                        steam_domain=ho_name, return_domain=hr_name,
                        compressor_inlet_C=comp_in,
                        overhead_plateau_fraction_DECLARED=float(fraction),
                        usable_aggregate_above60_MW=q_above(TR, ho, hr, float(fraction), comp_in),
                        heat_above77_MW=q_above(77.0, ho, hr, float(fraction), comp_in),
                        minimum_flow_NECESSARY_kg_s=flow,
                        controlling_threshold_C=cut,
                        maximum_supply_NECESSARY_C=ts,
                        same_secondary_interface_possible=interface_ok,
                        ideal_secondary_UA_MW_K=ua_for_same_secondary(ts) if interface_ok else None,
                        status=('candidate_not_sufficient' if interface_ok else
                                'aggregate_exclusion' if flow is None else 'interface_exclusion'),
                        evidence='Declared recovery family, no empirical probability or measured recovery partition'))
    # Analytic validation: cold endpoint loss is affine in the overhead fraction.
    for s in summary:
        x = s['minimum_overhead_plateau_fraction_aggregate']
        if 0 < x < 1:
            lo, hi = s['aggregate_at_fraction0_MW'], s['aggregate_at_fraction1_MW']
            assert abs(lo + x * (hi - lo) - D) < 1e-10
    worst = max(summary, key=lambda s: s['minimum_overhead_plateau_fraction_aggregate'])
    best = min(summary, key=lambda s: s['minimum_overhead_plateau_fraction_aggregate'])
    out = ROOT / 'results'
    with (out / 'recovery_composite_frontier_20261011.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                  status='PASS structural diagnostic; NOT published composite reproduction or hardware certification',
                  source={'publication': 'Su et al. Fuel 332 (2023) 126004',
                          'printed_endpoints': 'Fig.6/text overhead 106->70 C; compressor 136/164/173->70 C',
                          'duties_MW': {'overhead': Q_OH, 'compressor': Q_COMP},
                          'declared_not_printed': ['Constant heat capacity sensible cooling curves',
                                                  'Overhead plateau fraction in [0,1]',
                                                  'All compression duty placed at either endpoint inlet',
                                                  '15 K approach on compressor as in prior screen']},
                  condition='Q_above(60 C)>=36.5 MW precedes all flow/UA repair choices',
                  structural_summaries=summary,
                  worst_aggregate_partition=worst, best_aggregate_partition=best,
                  coordinate_count=len(rows),
                  excluded_coordinates=sum(r['status']!='candidate_not_sufficient' for r in rows),
                  warnings=['The grid has no empirical distribution; fractions of rows are not probabilities.',
                            'An actual overhead condensing profile need not belong to this illustrative family.',
                            'A pass is only necessary; finite branch UA, joint power and reliability remain unclosed.',
                            'Heat pump outlet and COP remain the source 77 C/5.5 anchor, not a boosted device.',
                            'No new LCA, TEA or investment ordering has been computed.'])
    (out / 'recovery_composite_audit_20261011.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
