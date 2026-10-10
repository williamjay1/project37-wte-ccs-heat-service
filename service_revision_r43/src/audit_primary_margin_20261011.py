"""Independent diagnostic of the submitted r40 necessary service screen.

This is NOT a certified retrofit, a plant validation, or a new investment result.
Su's process anchors and this paper's DECLARED service coordinates are kept
separate. Exact liquid-water properties reproduce the paper's empty window;
an independent static heat-allocation LP checks the algebra. The resulting
distances to a screening boundary must not be called source uncertainty.

Run with Python 3.12 from any directory. Outputs are written only to D work.
"""
from pathlib import Path
from functools import lru_cache
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cache/python_packages_r32'))
from iapws import IAPWS97
from scipy.optimize import brentq, linprog

DEMAND = 36.5  # MW, declared contract, NOT a printed Su observation
RETURN = 60.0  # C, declared primary circuit
FLOW_CAP = 150.0  # kg/s, declared screen coordinate
USER_SUPPLY, USER_RETURN = 80.0, 50.0  # C, unchanged secondary service
MIN_PRIMARY_SUPPLY = USER_SUPPLY + 5.0  # declared terminal approach
WATER_PRESSURE = 1.0  # MPa = 10 bar, declared liquid property coordinate
# Recovery duty/grade rectangles are optimistic outer bounds, not composites.
BASE_SOURCES = [('steam', 18.5, 390.0), ('overhead', 5.3, 91.0),
                ('compressor', 1.6, 158.0), ('heat_pump', 9.8 * 5.5 / 4.5, 77.0)]


@lru_cache(None)
def h(temperature):
    """MJ/kg: kg/s times an enthalpy difference returns MW."""
    return IAPWS97(P=WATER_PRESSURE, T=temperature + 273.15).h / 1000


def grade_upper(ts, sources=BASE_SOURCES):
    """Maximum service duty permitted by the optimistic grade-only cuts."""
    limits = [sum(q for _, q, grade in sources if grade > RETURN)]
    for theta in sorted({grade for _, _, grade in sources}):
        if RETURN < theta < ts:
            eligible = sum(q for _, q, grade in sources if grade > theta)
            upper_fraction = (h(ts) - h(theta)) / (h(ts) - h(RETURN))
            limits.append(eligible / upper_fraction)
    return min(limits)


def allocation_lp(ts, flow, sources=BASE_SOURCES):
    """Independent LP, no call to the existing project service solver.

    The first four variables are delivered branch duties and the fifth is
    total delivered duty. This tests only aggregate/grade/hydraulic cuts;
    finite source composites, UA hardware, pumps and availability are absent.
    """
    equalities = [[1.0] * 4 + [-1.0]]
    inequalities, right = [], []
    for theta in sorted({grade for _, _, grade in sources}):
        if RETURN < theta < ts:
            fraction = (h(theta) - h(RETURN)) / (h(ts) - h(RETURN))
            inequalities.append([float(grade <= theta) for _, _, grade in sources]
                                + [-fraction])
            right.append(0.0)
    bounds = [(0.0, q) for _, q, _ in sources]
    bounds.append((0.0, min(DEMAND, flow * (h(ts) - h(RETURN)))))
    result = linprog([0.0] * 4 + [-1.0], A_ub=inequalities or None,
                     b_ub=right or None, A_eq=equalities, b_eq=[0.0],
                     bounds=bounds, method='highs')
    if not result.success:
        raise RuntimeError(result.message)
    return float(result.x[-1])


def ua_for_same_secondary(ts):
    """Ideal countercurrent UA coordinate (MW/K), not an installed rating."""
    a, b = ts - USER_SUPPLY, RETURN - USER_RETURN
    assert min(a, b) >= 5.0
    lmtd = (a - b) / math.log(a / b) if abs(a - b) > 1e-10 else a
    return DEMAND / lmtd


def maximum_ts(sources=BASE_SOURCES):
    if grade_upper(MIN_PRIMARY_SUPPLY, sources) < DEMAND - 1e-9:
        return None
    return brentq(lambda ts: grade_upper(ts, sources) - DEMAND,
                  MIN_PRIMARY_SUPPLY, 130.0, xtol=1e-11)


def main():
    ts_max = maximum_ts()
    ts_min = brentq(lambda ts: FLOW_CAP * (h(ts) - h(RETURN)) - DEMAND,
                    85.0, 130.0, xtol=1e-11)
    flow_min = DEMAND / (h(ts_max) - h(RETURN))
    dh77 = h(77.0) - h(RETURN)
    high_required = DEMAND * (1.0 - dh77 / (DEMAND / FLOW_CAP))
    high_available = sum(q for _, q, grade in BASE_SOURCES if grade > 77.0)
    grade_required = brentq(lambda t: h(t) - h(RETURN)
                            - (DEMAND - high_available) / FLOW_CAP, 70.0, 90.0)
    assert abs(ts_max - 115.6609354663482) < 1e-7
    assert abs(ts_min - 117.86986290966021) < 1e-7
    rows, errors = [], []
    # Deterministic coordinates: their distribution has no empirical meaning.
    for ts in [85.0, 90.0, 100.0, 110.0, ts_max, ts_min, 120.0, 125.0]:
        for flow in [150.0, flow_min, 180.0, 217.525042353, 450.0]:
            upper = min(DEMAND, grade_upper(ts), flow * (h(ts) - h(RETURN)))
            calculated = allocation_lp(ts, flow)
            errors.append(abs(upper - calculated))
            rows.append(dict(primary_supply_C=ts, flow_cap_kg_s=flow,
                             necessary_delivered_bound_MW=upper,
                             independent_LP_delivered_MW=calculated,
                             necessary_screen_pass=upper >= DEMAND - 1e-8,
                             UA_same_secondary_MW_K=ua_for_same_secondary(ts),
                             evidence='declared coordinates, optimistic outer domain'))
    assert max(errors) < 1e-8
    # Monotonicity check: increasing Ts lowers required flow and UA until the
    # grade cut binds. This does not prove a minimum monetary-cost design.
    assert DEMAND / (h(100.0) - h(RETURN)) > flow_min
    assert ua_for_same_secondary(100.0) > ua_for_same_secondary(ts_max)
    assert allocation_lp(ts_max, flow_min) >= DEMAND - 1e-8
    assert allocation_lp(120.0, 150.0) < DEMAND - 1e-4
    perturbations = []
    for fraction in [1.0, 0.95, 0.9, 0.85, 0.8]:
        sources = [(name, q * fraction if name == 'overhead' else q, grade)
                   for name, q, grade in BASE_SOURCES]
        upper_ts = maximum_ts(sources)
        perturbations.append(dict(overhead_fraction_DESIGN_STRESS=fraction,
                                  aggregate_MW=sum(q for _, q, _ in sources),
                                  supply_upper_C=upper_ts,
                                  minimum_flow_kg_s=(DEMAND / (h(upper_ts) - h(RETURN))
                                                     if upper_ts is not None else None),
                                  interpretation='one-at-a-time structural stress, not a probability or error bar'))
    manuscript = ROOT / 'output/pdf/project37_manuscript_r40_20261006.pdf'
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                  manuscript=manuscript.name,
                  manuscript_sha256=(hashlib.sha256(manuscript.read_bytes()).hexdigest()
                                     if manuscript.exists() else None),
                  historical_file_scope='Optional submitted-file identifier only; no numerical input is read from that PDF.',
                  provenance={'process': 'Su 2023 published backpressure heat/recovery anchors',
                              'service': 'D=36.5 MW, flow=150 kg/s and primary transfers are analyst-declared, not published plant observations',
                              'model': 'r40 optimistic source-grade rectangles and IF97 10-bar liquid-water coordinate'},
                  status='PASS independent algebra/LP diagnostic; NOT certified physical repair',
                  primary_supply_max_C=ts_max, primary_supply_min_at150_C=ts_min,
                  empty_window_K=ts_min - ts_max,
                  minimum_flow_for_necessary_window_kg_s=flow_min,
                  flow_increase_from150_percent=(flow_min / FLOW_CAP - 1.0) * 100,
                  UA_at120_MW_K=ua_for_same_secondary(120.0),
                  UA_at_grade_boundary_MW_K=ua_for_same_secondary(ts_max),
                  UA_increase_from120_percent=(ua_for_same_secondary(ts_max) / ua_for_same_secondary(120.0) - 1.0) * 100,
                  flow_at100_kg_s=DEMAND / (h(100.0) - h(RETURN)),
                  UA_at100_MW_K=ua_for_same_secondary(100.0),
                  required_additional_above77_MW_at150=high_required - high_available,
                  margin_fraction_of_aggregate_percent=(high_required - high_available) / sum(q for _, q, _ in BASE_SOURCES) * 100,
                  effective_low_grade_boundary_C=grade_required,
                  effective_low_grade_shift_K=grade_required - 77.0,
                  independent_LP_comparisons=len(rows),
                  maximum_algebra_LP_error_MW=max(errors),
                  one_at_a_time_stresses=perturbations,
                  limits=['Passing necessary cuts is not a sufficient heat-exchanger network construction.',
                          'UA is an ideal terminal-temperature coordinate; installed UA, branch composites, pressure drop and pumping remain unknown.',
                          'The heat-grade perturbation does not establish a realizable heat-pump upgrade at unchanged COP/power.',
                          'Source closure residuals are not uncertainty distributions.',
                          'No new climate, cost, investment ordering, factory validation or EU-27 fleet claim is made.'])
    out = ROOT / 'results'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'primary_margin_audit_20261011.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with (out / 'primary_margin_frontier_20261011.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    # Plotting runtime is isolated from engineering packages. Export evaluated
    # IF97 coordinates rather than recomputing them with another property model.
    with (out / 'primary_flow_curve_20261011.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['primary_supply_C', 'required_flow_kg_s'])
        writer.writeheader()
        writer.writerows({'primary_supply_C': float(t),
                          'required_flow_kg_s': DEMAND / (h(float(t)) - h(RETURN))}
                         for t in np.linspace(85.0, 125.0, 301))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
