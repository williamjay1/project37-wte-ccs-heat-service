"""Construct a conservative, finite split/recombine heat-exchanger network.

This is a conditional steady thermal construction, not a factory validation.
The Su heat-pump module is retained at its printed 60 -> 77 C water/COP 5.5
anchor. It is not treated as an isothermal 77 C hot source or freely boosted.
Other streams use the explicit steam/recovery families of the Oct-11 audit.

For every cold-water interval, a hot interval is usable only if its LOWEST
temperature exceeds the cold interval's HIGHEST temperature by the prescribed
approach. Cold split fractions recombine at identical outlet states. Hot
exchanges can be ordered serially, retaining unexchanged enthalpy: unused hot
flow is not assumed to have reached a colder nominal state. This rule gives a finite
constructive certificate, with conservative sum(q/minimum_delta_T) conductance.
An excluded construction is not proof that every possible network is excluded.
No storage, fuel substitution, backup burner or unreported heat source is used.
"""
from pathlib import Path
from functools import lru_cache
from datetime import datetime, timezone
import csv
import heapq
import json
import math
import sys

import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cache/python_packages_r32'))
from iapws import IAPWS97
from audit_primary_margin_20261011 import h, ua_for_same_secondary
from audit_steam_composite_margin_20261011 import (
    ISENTROPIC, INLET, RETURN_COLD, SAT_LIQUID)

D, TR, HP_OUT, HP_COP = 36.5, 60.0, 77.0, 5.5
HP99 = 9.8 * HP_COP / (HP_COP - 1)
RECOVERY_SCALE95 = (38 - 19.9) / (5.3 + 1.6 + HP99)
SAT = IAPWS97(P=.4, x=0)
VAP = IAPWS97(P=.4, x=1)
TSAT = SAT.T - 273.15


@lru_cache(None)
def steam_h(t):
    return IAPWS97(P=.4, T=float(t) + 273.15).h / 1000


def boundaries(lo, hi, step):
    return np.linspace(lo, hi, max(1, math.ceil((hi - lo) / step)) + 1)


def source_chunks(steam_q, recovery_scale, ho, hr, fraction, comp_in, step):
    chunks = []
    steam_mass = steam_q / (ho - hr)

    def add(branch, lo, hi, q, approach):
        if q > 1e-12:
            chunks.append(dict(branch=branch, hot_low_C=lo, hot_high_C=hi,
                               available_MW=q, approach_K=approach,
                               shifted_low_C=lo - approach))

    # Steam-liquid sensible heat: don't assign its entire duty to saturation.
    t_return = IAPWS97(P=.4, h=hr * 1000).T - 273.15
    knots = boundaries(max(t_return, TR + 10), TSAT, step)
    for lo, hi in zip(knots[:-1], knots[1:]):
        # The saturated endpoint is liquid, not the numerical vapour branch.
        hl = steam_h(float(lo))
        hh = SAT.h / 1000 if abs(hi - TSAT) < 1e-8 else steam_h(float(hi))
        add('steam_liquid', float(lo), float(hi), steam_mass * (hh - hl), 10.)
    latent = max(0., min(ho, VAP.h / 1000) - SAT.h / 1000)
    add('steam_latent', TSAT, TSAT, steam_mass * latent, 10.)
    if ho > VAP.h / 1000 + 1e-10:
        t_in = IAPWS97(P=.4, h=ho * 1000).T - 273.15
        knots = boundaries(TSAT, t_in, step)
        for lo, hi in zip(knots[:-1], knots[1:]):
            hl = VAP.h / 1000 if abs(lo - TSAT) < 1e-8 else steam_h(float(lo))
            add('steam_superheat', float(lo), float(hi),
                steam_mass * (steam_h(float(hi)) - hl), 10.)
    # Recovery sensible heat capacities and plateau split are DECLARED.
    for name, inlet, q in [('overhead_sensible', 106., 5.3 * (1 - fraction)),
                            ('compressor_sensible', comp_in, 1.6)]:
        knots = boundaries(max(70., TR + 15), inlet, step)
        for lo, hi in zip(knots[:-1], knots[1:]):
            add(name, float(lo), float(hi), recovery_scale * q
                * (hi - lo) / (inlet - 70), 15.)
    add('overhead_plateau', 106., 106., recovery_scale * 5.3 * fraction, 15.)
    return chunks


def construct(ts, steam_q, recovery_scale, ho, hr, fraction, comp_in, step=.1, demand_MW=D):
    mass = demand_MW / (h(ts) - h(TR))
    hp_q = HP99 * recovery_scale
    hp_module_mass = hp_q / (h(HP_OUT) - h(TR))
    hp_mass = min(mass, hp_module_mass)
    hp_used = hp_mass * (h(HP_OUT) - h(TR))
    # At120 C the required primary mass can be smaller than the complete HP
    # module output-water stream. Retain full HP power and explicitly reject
    # the surplus; do not claim a free part-load COP curve or external credit.
    hp_rejection = hp_q - hp_used
    cold = []
    # HP branch heats hp_mass at the exact source anchor; remaining water is
    # heated by recovered streams. Both recombine at 77 C, then heat to Ts.
    for lo, hi, m in [(TR, HP_OUT, mass - hp_mass), (HP_OUT, ts, mass)]:
        knots = boundaries(lo, hi, step)
        for a, b in zip(knots[:-1], knots[1:]):
            cold.append(dict(cold_low_C=float(a), cold_high_C=float(b),
                             required_MW=m * (h(float(b)) - h(float(a)))))
    hot = source_chunks(steam_q, recovery_scale, ho, hr, fraction, comp_in, step)
    ranked = sorted(enumerate(hot), key=lambda x: x[1]['shifted_low_C'], reverse=True)
    remaining = [s['available_MW'] for s in hot]
    allocations, active, pos, unmet = [], [], 0, 0.
    for c in reversed(cold):
        while pos < len(ranked) and ranked[pos][1]['shifted_low_C'] >= c['cold_high_C'] - 1e-10:
            index, s = ranked[pos]
            heapq.heappush(active, (s['shifted_low_C'], index))
            pos += 1
        need = c['required_MW']
        while need > 1e-10 and active:
            _, index = heapq.heappop(active)
            s = hot[index]
            q = min(need, remaining[index])
            delta = s['hot_low_C'] - c['cold_high_C']
            assert delta + 1e-8 >= s['approach_K']
            allocations.append(dict(source_chunk=index, **c, **s, exchanged_MW=q,
                                    minimum_temperature_difference_K=delta,
                                    sufficient_UA_bound_MW_K=q / delta))
            need -= q
            remaining[index] -= q
            if remaining[index] > 1e-10:
                heapq.heappush(active, (s['shifted_low_C'], index))
        unmet += max(0., need)
    exchanged = sum(a['exchanged_MW'] for a in allocations)
    by_branch = {name: sum(a['exchanged_MW'] for a in allocations if a['branch'] == name)
                 for name in sorted({s['branch'] for s in hot})}
    energy_error = abs(hp_used + exchanged + unmet - demand_MW)
    assert energy_error < 1e-7
    assert min(remaining) > -1e-9
    summary = dict(demand_MW=demand_MW, primary_supply_C=ts, primary_return_C=TR, primary_water_kg_s=mass,
                   heat_pump_water_kg_s=hp_mass, heat_pump_module_water_kg_s=hp_module_mass,
                   heat_pump_duty_MW=hp_q, heat_pump_delivered_MW=hp_used,
                   heat_pump_surplus_rejection_MW=hp_rejection,
                   heat_pump_power_MW=hp_q / HP_COP,
                   heat_pump_anchor='60 -> 77 C water, COP5.5, source module retained',
                   hot_stream_available_above_approach_MW=sum(s['available_MW'] for s in hot),
                   recovered_hot_delivered_MW=exchanged,
                   unused_eligible_hot_MW=sum(remaining), unmet_MW=unmet,
                   thermal_path_constructed=bool(unmet < 1e-7),
                   energy_closure_error_MW=energy_error,
                   recovery_network_sufficient_UA_bound_MW_K=sum(a['sufficient_UA_bound_MW_K'] for a in allocations),
                   secondary_interface_UA_MW_K=ua_for_same_secondary(ts) * demand_MW / D,
                   minimum_non_HP_approach_K=min(a['minimum_temperature_difference_K'] for a in allocations),
                   number_of_matched_interval_exchangers=len(allocations),
                   delivered_by_branch_MW=by_branch,
                   temperature_interval_K=step,
                   scope='Constructed split/recombine thermal path; count is numerical subdivisions, not recommended equipment count. HP internal UA/pressure drops/turbine/off-design/availability unverified.')
    return summary, allocations


def save(name, rows):
    with (ROOT / 'results' / name).open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    rows, detail, convergence = [], [], []
    for design, steam_q, scale in [('99.72', 18.5, 1.), ('95', 19.9, RECOVERY_SCALE95)]:
        for ho_name, ho in [('isentropic', ISENTROPIC.h / 1000), ('inlet_upper', INLET.h / 1000)]:
            for hr_name, hr in [('60C', RETURN_COLD), ('saturated_liquid', SAT_LIQUID.h / 1000)]:
                for comp in [136., 173.]:
                    for fraction in [0., .5, 1.]:
                        for ts in [100., 120.]:
                            s, allocations = construct(ts, steam_q, scale, ho, hr, fraction, comp)
                            meta = dict(design_capture_percent=design, steam_enthalpy_endpoint=ho_name,
                                        steam_return_endpoint=hr_name, compressor_inlet_C=comp,
                                        overhead_plateau_fraction_DECLARED=fraction)
                            rows.append({**meta, **{k: v for k, v in s.items() if k != 'delivered_by_branch_MW'}})
                            if design == '99.72' and ho_name == 'isentropic' and hr_name == '60C' and comp == 136 and fraction == .5 and ts == 100:
                                detail = [{**meta, **a} for a in allocations]
                                representative = {**meta, **s}
    # Independent refinement diagnostic on the controlling construction, not
    # empirical error bars. The conservative rule tightens as intervals shrink.
    for step in [.5, .2, .1, .05]:
        s, _ = construct(100., 18.5, 1., ISENTROPIC.h / 1000, RETURN_COLD, .5, 136., step)
        convergence.append(s)
    # Coarse intervals may discard the very small heat surplus. Report this
    # failure and require construction only at the two finest tested steps.
    assert all(s['thermal_path_constructed'] for s in convergence[-2:])
    assert all(r['thermal_path_constructed'] for r in rows if r['primary_supply_C'] == 100 and r['overhead_plateau_fraction_DECLARED'] >= .5)
    # Every interval certificate is stronger than the ideal composite screen;
    # failed constructions stay in the table, never relabelled as impossibility.
    save('finite_heat_path_matrix_20261011.csv', rows)
    save('finite_heat_path_allocation_20261011.csv', detail)
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                  status='PASS finite conditional thermal construction and interval-refinement checks',
                  matrix_rows=len(rows), constructed_paths=sum(r['thermal_path_constructed'] for r in rows),
                  representative=representative, convergence=convergence,
                  max_energy_closure_error_MW=max(r['energy_closure_error_MW'] for r in rows),
                  fixed_secondary_service='36.5 MW at80/50 C, fixed residual-waste throughput; primary60 C return, 5 K minimum interface approach.',
                  source_module_limit='HP output water anchor used directly; internal condenser UA not reconstructed. Steam/recovery endpoint profiles remain declared domains.',
                  no_claims=['Not installed hardware or minimal HEN cost/number of exchangers.',
                             'No independently reconstructed net turbine power or pressure loss.',
                             'No empirical probability or annual reliability from static construction.',
                             'No investment ranking until non-cancelling capital and differential burdens are included.'])
    (ROOT / 'results/finite_heat_path_audit_20261011.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
