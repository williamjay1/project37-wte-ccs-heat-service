"""A fixed-temperature cut margin, distinct from aggregate unused heat.

The overhead fraction0.5 is a declared structural coordinate, not measured.
An independent cut calculation gives the retained-duty threshold of the
conservative interval model, then checks allocations on both sides. It is
not an observed uncertainty tolerance or an annual service guarantee.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import numpy as np

from construct_finite_heat_path_20261011 import (
    construct, source_chunks, h, HP99, ISENTROPIC, RETURN_COLD)

ROOT=Path(__file__).resolve().parents[1]
D=36.5


def independent_boundary(step):
    hot=source_chunks(18.5,1.,ISENTROPIC.h/1000,RETURN_COLD,.5,136.,step)
    hp_span=h(77.)-h(60.)
    water_span=h(100.)-h(60.)
    cuts=[]
    for a,b in [(60.,77.),(77.,100.)]:
        knots=np.linspace(a,b,math.ceil((b-a)/step)+1)
        for lo,hi in zip(knots[:-1],knots[1:]):
            # Cold tail starts at this interval's lower endpoint. This differs
            # from the hot eligibility threshold at its upper endpoint.
            demand_coefficient=(h(100.)-h(float(lo)))/water_span
            hp_coefficient=HP99*max(0.,h(77.)-h(float(lo)))/hp_span
            available=sum(j['available_MW'] for j in hot
                          if j['shifted_low_C']>=float(hi)-1e-10)
            threshold=D*demand_coefficient/(available+hp_coefficient)
            cuts.append(dict(cold_lower_C=float(lo),cold_upper_C=float(hi),
                nominal_eligible_hot_MW=available,hp_preheat_coefficient_MW=hp_coefficient,
                retained_duty_required=threshold))
    control=max(cuts,key=lambda x:x['retained_duty_required'])
    retained=control['retained_duty_required']
    # Formula uses the unsaturated HP water split at this duty.
    assert HP99*retained/hp_span < D/water_span
    low=construct(100.,18.5*(retained-1e-6),retained-1e-6,
                  ISENTROPIC.h/1000,RETURN_COLD,.5,136.,step)[0]
    high=construct(100.,18.5*(retained+1e-6),retained+1e-6,
                   ISENTROPIC.h/1000,RETURN_COLD,.5,136.,step)[0]
    assert not low['thermal_path_constructed'] and high['thermal_path_constructed']
    aggregate=sum(j['available_MW'] for j in hot)+HP99
    return dict(temperature_step_K=step,controlling_cut=control,
        maximum_proportional_derating_percent=100*(1-retained),
        aggregate_prerequisite_derating_percent=100*(1-D/aggregate),
        nominal_contract_capacity_of_interval_model_MW=D/retained,
        low_retained_unmet_MW=low['unmet_MW'],high_retained_unmet_MW=high['unmet_MW'],
        checks_pass=True)


def main():
    rows=[independent_boundary(s) for s in [.2,.1,.05]]
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        status='PASS independent fixed-temperature cut margin and two-sided allocator checks',
        contract='36.5MW, primary100/60C, customer80/50C, fixed waste throughput',
        profile='Cold steam endpoint; compressor136C; declared overhead plateau0.5',
        resolutions=rows,
        limitations=['Thermal duties and HP output are proportionally scaled as a prescribed stress.',
            'Not a measured operating tolerance, installed hardware rating or annual reliability.',
            'The cut is exact only for the divisible conservative interval graph.',
            'Duty changes do not recalculate capture, turbine power or finances.'])
    path=ROOT/'results/constructed_path_derating_audit_20261011.json'
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
