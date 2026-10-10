"""Conditional contract capacity over the declared profile family, not confidence.

For a fixed hot profile and Ts=100 C, every cold interval requirement is
nondecreasing in the delivered duty. Bisection therefore brackets the maximum
constructible duty of the conservative interval model. Heat duty derating is
a prescribed stress, NOT a source uncertainty distribution or extra feed.
"""
from pathlib import Path
from datetime import datetime, timezone
import csv
import json

from construct_finite_heat_path_20261011 import (
    construct, ISENTROPIC, INLET, RETURN_COLD, SAT_LIQUID, RECOVERY_SCALE95)

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = []
    for retained in [1., .95]:
        for design, H, rec in [('99.72', 18.5, 1.), ('95', 19.9, RECOVERY_SCALE95)]:
            for on, ho in [('isentropic', ISENTROPIC.h / 1000), ('inlet_upper', INLET.h / 1000)]:
                for rn, hr in [('60C', RETURN_COLD), ('saturated_liquid', SAT_LIQUID.h / 1000)]:
                    for comp in [136., 173.]:
                        for fraction in [0., .5, 1.]:
                            lo, hi = 20., 41.
                            args = (100., H * retained, rec * retained, ho, hr, fraction, comp)
                            assert construct(*args, demand_MW=lo)[0]['thermal_path_constructed']
                            assert not construct(*args, demand_MW=hi)[0]['thermal_path_constructed']
                            while hi - lo > .001:
                                mid = (lo + hi) / 2
                                if construct(*args, demand_MW=mid)[0]['thermal_path_constructed']:
                                    lo = mid
                                else:
                                    hi = mid
                            low = construct(*args, demand_MW=lo)[0]
                            high = construct(*args, demand_MW=hi)[0]
                            assert low['thermal_path_constructed'] and not high['thermal_path_constructed']
                            rows.append(dict(retained_heat_duty_DECLARED=retained,
                                capture_percent=design, steam_endpoint=on, return_endpoint=rn,
                                compressor_inlet_C=comp, overhead_fraction_DECLARED=fraction,
                                constructed_duty_lower_MW=lo, conservative_method_failure_upper_MW=hi,
                                width_MW=hi-lo, boundary_primary_flow_kg_s=low['primary_water_kg_s'],
                                boundary_recovery_UA_MW_K=low['recovery_network_sufficient_UA_bound_MW_K'],
                                high_unmet_MW=high['unmet_MW']))
    with (ROOT/'results/finite_service_capacity_20261011.csv').open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    bounds = []
    for retained in [1., .95]:
        for design in ['99.72', '95']:
            group = [r for r in rows if r['retained_heat_duty_DECLARED']==retained and r['capture_percent']==design]
            controlling=min(group,key=lambda r:r['constructed_duty_lower_MW'])
            common_lower=min(r['constructed_duty_lower_MW'] for r in group)
            common_upper=min(r['conservative_method_failure_upper_MW'] for r in group)
            # Re-run ALL family endpoints at the common lower bound, not just
            # the selected endpoint; no statement about observed probability.
            passes=[]
            for r in group:
                ho=ISENTROPIC.h/1000 if r['steam_endpoint']=='isentropic' else INLET.h/1000
                hr=RETURN_COLD if r['return_endpoint']=='60C' else SAT_LIQUID.h/1000
                H=18.5 if design=='99.72' else 19.9
                rec=1. if design=='99.72' else RECOVERY_SCALE95
                passes.append(construct(100.,H*retained,rec*retained,ho,hr,
                    r['overhead_fraction_DECLARED'],r['compressor_inlet_C'],demand_MW=common_lower)[0]['thermal_path_constructed'])
            assert all(passes)
            bounds.append(dict(retained_heat_duty_DECLARED=retained,capture_percent=design,
                family_common_constructed_lower_MW=common_lower,
                family_conservative_method_upper_MW=common_upper,
                all_endpoint_rechecks_pass=all(passes),endpoints_checked=len(passes),
                controlling=controlling))
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS conditional common-capacity bracketing',
        primary_supply_return_C=[100,60],customer_supply_return_C=[80,50],temperature_step_K=.1,
        profiles=len(rows),family_bounds=bounds,
        limits=['Finite interval family only, not installed/annual firm service or global optimal topology.',
                'Five percent duty derating is a prescribed stress, not measured uncertainty.',
                'Boundary costs/power not recomputed; no financial ranking from capacity alone.',
                'Profile endpoints are not independent plants or probability samples.'])
    (ROOT/'results/finite_service_capacity_audit_20261011.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
