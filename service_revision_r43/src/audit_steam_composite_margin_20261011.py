"""Phase-resolved necessary retrofit bounds, not a realized retrofit.

The fixed 18.5 MW published DH anchor is conditionally reconstructed as a
fully condensing steam duty under the r40 DECLARED steam/condensate domain.
This is an input-domain extension, not independent plant reproduction.
Overhead, compression and heat-pump branches remain optimistic rectangles;
their true composites, installed hardware and off-design power are unresolved.

For a common duty D and return Tr, every shifted-hot-composite cut implies
  m >= [D - Q_above(theta)]_+ / [h_water(theta) - h_water(Tr)].
Thus the supremum of these cuts gives the minimum flow for this NECESSARY
domain, provided total usable heat >= D. It does not give minimum cost.
"""
from pathlib import Path
from datetime import datetime, timezone
from functools import lru_cache
import csv
import hashlib
import json
import sys

import numpy as np
from scipy.optimize import brentq, minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cache/python_packages_r32'))
from iapws import IAPWS97
from audit_primary_margin_20261011 import h, ua_for_same_secondary

D, TR, Q_STEAM, APPROACH = 36.5, 60.0, 18.5, 10.0
OTHER = [(5.3, 91.0), (1.6, 158.0), (9.8 * 5.5 / 4.5, 77.0)]
INLET = IAPWS97(P=6.0, T=673.15)
ISENTROPIC = IAPWS97(P=0.4, s=INLET.s)
SAT_LIQUID = IAPWS97(P=0.4, x=0)
SAT_VAPOR = IAPWS97(P=0.4, x=1)
T_SAT = SAT_VAPOR.T - 273.15
RETURN_COLD = IAPWS97(P=0.4, T=333.15).h / 1000
PHASE_GRADE = T_SAT - APPROACH


@lru_cache(None)
def threshold_h(theta):
    """Hot-side enthalpy above a cold theta + declared minimum approach.

    At the condensation plateau the right limit excludes latent heat from
    duty needed strictly ABOVE the plateau, retaining only superheat.
    """
    hot = theta + APPROACH
    if abs(hot - T_SAT) < 1e-8:
        return SAT_VAPOR.h / 1000
    return IAPWS97(P=0.4, T=hot + 273.15).h / 1000


def q_above(theta, ho, hr):
    steam = Q_STEAM * np.clip((ho - max(hr, threshold_h(theta))) / (ho - hr), 0, 1)
    return float(steam + sum(q for q, grade in OTHER if grade > theta))


def required_flow_cut(theta, ho, hr):
    return max(0.0, D - q_above(theta, ho, hr)) / (h(theta) - h(TR))


def critical_flow(ho, hr):
    if q_above(TR, ho, hr) < D - 1e-10:
        return None, None
    knots = [TR + 1e-7, 77.0, 91.0, PHASE_GRADE, 158.0, 160.0]
    candidates = [(required_flow_cut(t, ho, hr), t) for t in knots]
    for lower, upper in zip(knots[:-1], knots[1:]):
        # Smooth open intervals; all jump right limits are explicit candidates.
        r = minimize_scalar(lambda t: -required_flow_cut(t, ho, hr),
                            bounds=(lower + 1e-6, upper - 1e-6), method='bounded',
                            options={'xatol': 1e-10})
        candidates.append((-float(r.fun), float(r.x)))
    return max(candidates)


def maximum_duty(ts, flow, ho, hr, grid):
    """Dense independent cut assembly (grid validation, not sampling)."""
    upper = min(q_above(TR, ho, hr), flow * (h(ts) - h(TR)))
    for theta in grid:
        if TR < theta < ts:
            upper = min(upper, q_above(float(theta), ho, hr)
                        * (h(ts) - h(TR)) / (h(ts) - h(float(theta))))
    return upper


def main():
    hout = [ISENTROPIC.h / 1000, INLET.h / 1000]
    hret = [RETURN_COLD, SAT_LIQUID.h / 1000]
    knots = [77.0, 91.0, PHASE_GRADE - 1e-7, PHASE_GRADE, 158.0]
    grid = sorted(set(np.linspace(TR + 1e-5, 160.0, 5001).tolist() + knots))
    rows = []
    for i, ho in enumerate(hout):
        for j, hr in enumerate(hret):
            flow, theta = critical_flow(ho, hr)
            assert flow is not None
            ts = brentq(lambda t: h(t) - h(TR) - D / flow, 85.0, 130.0, xtol=1e-11)
            dense = max(required_flow_cut(float(t), ho, hr) for t in grid)
            assert abs(flow - dense) < 1e-7
            # Independently assembled duty bounds just below/above the flow
            # frontier: no retuning the source states to pass these tests.
            under = maximum_duty(ts, flow * 0.99999, ho, hr, grid)
            over = maximum_duty(ts, flow * 1.00001, ho, hr, grid)
            assert under < D - 1e-5 and over >= D - 1e-7
            rows.append(dict(
                steam_state_domain=('isentropic' if i == 0 else 'inlet_enthalpy_upper'),
                condensate_domain=('60C_lower' if j == 0 else 'saturated_liquid_upper'),
                steam_h_in_MJ_kg=ho, condensate_h_out_MJ_kg=hr,
                conditional_steam_mass_kg_s=Q_STEAM / (ho - hr),
                usable_aggregate_above60_MW=q_above(TR, ho, hr),
                heat_above77_MW=q_above(77.0, ho, hr),
                controlling_cold_cut_C=theta,
                minimum_flow_NECESSARY_kg_s=flow,
                increase_from150_percent=(flow / 150 - 1) * 100,
                maximum_supply_NECESSARY_C=ts,
                ideal_secondary_UA_MW_K=ua_for_same_secondary(ts),
                UA_increase_vs120_percent=(ua_for_same_secondary(ts)
                                          / ua_for_same_secondary(120.0) - 1) * 100,
                dense_frontier_error_kg_s=abs(flow - dense),
                under_frontier_duty_bound_MW=under,
                above_frontier_duty_bound_MW=over,
                scope='Anchored steam-duty domain; other recovery remains optimistic; not installed hardware or investment validation'))
    # Analytic monotonicity: for a fixed threshold enthalpy a > hr,
    # d[(ho-a)/(ho-hr)]/dho=(a-hr)/(ho-hr)^2 >=0 and the derivative
    # in hr is also nonnegative. Clipping preserves monotonicity.
    # All intermediate states therefore lie between the endpoint profiles.
    # Verify deterministically; these states have no empirical probabilities.
    ordered = all(q_above(float(t), hout[0], hret[0])
                  <= q_above(float(t), ho, hr) + 1e-10
                  <= q_above(float(t), hout[-1], hret[-1]) + 2e-10
                  for t in [60.0, 77.0, 85.0, 91.0, 110.0, 120.0, PHASE_GRADE, 150.0]
                  for ho in np.linspace(*hout, 11)
                  for hr in np.linspace(*hret, 11))
    assert ordered
    out = ROOT / 'results'
    with (out / 'steam_composite_margin_20261011.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    report = dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        status='PASS conditional necessary-domain extension; NOT a sufficient retrofit or factory reproduction',
        service={'D_MW': D, 'primary_return_C': TR,
                 'secondary_supply_return_C': [80, 50], 'secondary_minimum_approach_K': 5},
        source={'steam_duty_anchor_MW': Q_STEAM,
                'steam_extraction_pressure_MPa': 0.4,
                'steam_approach_DECLARED_K': APPROACH,
                'hout_domain_MJ_kg': hout, 'hreturn_domain_MJ_kg': hret,
                'published_basis': 'Su 2023 Table3 backpressure duty; r40 declared adiabatic full-condensation domain'},
        formula='m_min = sup_theta [D-Q_above(theta)]_+/(h_water(theta)-h_water(Tr)); requires Q_above(Tr)>=D',
        profiles_bracket_intermediate_states=ordered,
        minimum_necessary_flow_range_kg_s=[min(r['minimum_flow_NECESSARY_kg_s'] for r in rows),
                                          max(r['minimum_flow_NECESSARY_kg_s'] for r in rows)],
        supply_boundary_range_C=[min(r['maximum_supply_NECESSARY_C'] for r in rows),
                                 max(r['maximum_supply_NECESSARY_C'] for r in rows)],
        states=rows,
        limitations=[
            'Steam mass is conditional on the fixed heat anchor, not independently measured or reproduced.',
            'Endpoint heat/power feasibility is not jointly closed; this is a conservative declared state domain.',
            'Other recovery remains rectangular, so even a worst-steam-domain pass is not full robust hardware feasibility.',
            'Ideal secondary UA is not total branch/network conductance or cost.',
            'No hourly reliability, pump energy, LCA increment, capital cost or investment ranking is recalculated.',
            'Deterministic grids and state ranges are not confidence or credible intervals.'])
    (out / 'steam_composite_margin_20261011.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
