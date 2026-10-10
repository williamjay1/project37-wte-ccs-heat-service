"""Independent audit of exported allocations, without invoking their solver."""
from pathlib import Path
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cache/python_packages_r32'))
from iapws import IAPWS97


def water_h(t):
    return IAPWS97(P=1., T=t + 273.15).h / 1000


def main():
    rows = list(csv.DictReader((ROOT / 'results/finite_heat_path_allocation_20261011.csv').open()))
    cold, hot, required, capacity = defaultdict(float), defaultdict(float), {}, {}
    ua = 0.
    min_approach = 1000.
    for r in rows:
        c = (float(r['cold_low_C']), float(r['cold_high_C']))
        j = int(r['source_chunk'])
        q = float(r['exchanged_MW'])
        cold[c] += q; hot[j] += q
        required[c] = float(r['required_MW']); capacity[j] = float(r['available_MW'])
        delta = float(r['hot_low_C']) - c[1]
        assert delta >= float(r['approach_K']) - 1e-8
        assert q > 0 and delta > 0
        ua += q / delta
        min_approach = min(min_approach, delta)
    cold_residual = max(abs(cold[k] - required[k]) for k in cold)
    hot_excess = max(hot[k] - capacity[k] for k in hot)
    audit = json.loads((ROOT / 'results/finite_heat_path_audit_20261011.json').read_text())
    rep = audit['representative']
    mass = 36.5 / (water_h(100.) - water_h(60.))
    hp = 9.8 * 5.5 / 4.5
    energy_residual = abs(sum(cold.values()) + hp - 36.5)
    assert cold_residual < 1e-8 and hot_excess < 1e-8 and energy_residual < 1e-8
    assert abs(ua - rep['recovery_network_sufficient_UA_bound_MW_K']) < 1e-10
    assert abs(mass - rep['primary_water_kg_s']) < 1e-10
    assert min_approach >= 10
    convergence = audit['convergence']
    ua_refinement_percent = abs(convergence[-1]['recovery_network_sufficient_UA_bound_MW_K']
        / convergence[-2]['recovery_network_sufficient_UA_bound_MW_K'] - 1) * 100
    # SOURCE usability margin, not statistical uncertainty or hardware reserve.
    usable = rep['hot_stream_available_above_approach_MW'] + hp
    aggregate_derating_exclusion = 1 - 36.5 / usable
    budget = json.loads((ROOT / 'results/finite_path_decision_budget_audit_20261011.json').read_text())
    max_budget_residual = 0.
    for r in budget['central_rows']:
        extra_c = r['additional_captured_t_year']
        retained = extra_c * .99 * .995 * .4
        dw = r['total_additional_electricity_MW'] * 8000
        expected_climate = dw * 179 + extra_c * 50 - retained * 1000
        expected_headroom = r['effective_fossil_value_EUR2020_t_SCENARIO'] * retained - dw * 70 - extra_c * 50
        max_budget_residual = max(max_budget_residual, abs(expected_climate - r['included_delta_climate_kgCO2e_year']),
                                 abs(expected_headroom - r['pre_fixed_headroom_EUR2020_year']))
    assert max_budget_residual < 1e-7
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(), status='PASS independent CSV-allocation and budget arithmetic audit',
                  allocations=len(rows), cold_segments=len(cold), used_hot_segments=len(hot),
                  maximum_cold_balance_residual_MW=cold_residual, maximum_hot_capacity_excess_MW=max(0., hot_excess),
                  global_energy_residual_MW=energy_residual, recovery_UA_bound_MW_K=ua,
                  minimum_approach_K=min_approach, UA_change_0_1_to0_05_K_percent=ua_refinement_percent,
                  proportional_derating_above_which_aggregate_fails_percent=aggregate_derating_exclusion * 100,
                  maximum_central_budget_arithmetic_error=max_budget_residual,
                  limits='Source profiles and operating points remain assumptions; residuals and refinement are numerical checks, not measured validation/error distributions.')
    (ROOT / 'results/finite_heat_path_independent_QA_20261011.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
