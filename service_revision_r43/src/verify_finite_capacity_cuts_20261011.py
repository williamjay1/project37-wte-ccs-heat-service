"""Independent cumulative interval cuts; never calls the allocator/bisection."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import json
import math
import numpy as np
from construct_finite_heat_path_20261011 import (
    source_chunks, h, HP99, RECOVERY_SCALE95, ISENTROPIC, INLET, RETURN_COLD, SAT_LIQUID)

ROOT=Path(__file__).resolve().parents[1]


def cut(duty, row):
    factor=float(row['retained_heat_duty_DECLARED'])
    design=row['capture_percent']
    H=18.5 if design=='99.72' else 19.9
    rec=1. if design=='99.72' else RECOVERY_SCALE95
    ho=ISENTROPIC.h/1000 if row['steam_endpoint']=='isentropic' else INLET.h/1000
    hr=RETURN_COLD if row['return_endpoint']=='60C' else SAT_LIQUID.h/1000
    hot=source_chunks(H*factor,rec*factor,ho,hr,float(row['overhead_fraction_DECLARED']),
                      float(row['compressor_inlet_C']),.1)
    m=duty/(h(100.)-h(60.))
    m_hp=min(m,HP99*rec*factor/(h(77.)-h(60.)))
    cold=[]
    for lo,hi,mass in [(60.,77.,m-m_hp),(77.,100.,m)]:
        # Independently assemble the specified endpoints and interval duties.
        bounds=np.linspace(lo,hi,math.ceil((hi-lo)/.1)+1)
        cold.extend((float(b),mass*(h(float(b))-h(float(a)))) for a,b in zip(bounds[:-1],bounds[1:]))
    violations=[]
    for k,(theta,_) in enumerate(cold):
        required=sum(q for _,q in cold[k:])
        available=sum(j['available_MW'] for j in hot if j['shifted_low_C']>=theta-1e-10)
        violations.append((required-available,theta))
    return max(violations)


def main():
    rows=list(csv.DictReader((ROOT/'results/finite_service_capacity_20261011.csv').open()))
    checked=[]
    for row in rows:
        dl,tl=cut(float(row['constructed_duty_lower_MW']),row)
        du,tu=cut(float(row['conservative_method_failure_upper_MW']),row)
        assert dl<=1e-7 and du>1e-7
        assert abs(du-float(row['high_unmet_MW']))<1e-7
        checked.append(dict(**row,lower_max_cut_violation_MW=dl,upper_max_cut_violation_MW=du,
                            controlling_upper_cold_interval_C=tu))
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS independent cumulative cuts',
        rows=len(rows),lower_passes=len(checked),upper_exclusions=len(checked),
        max_allocator_vs_cut_residual_MW=max(abs(float(r['high_unmet_MW'])-r['upper_max_cut_violation_MW']) for r in checked),
        nominal99_controlling=next(r for r in checked if r['retained_heat_duty_DECLARED']=='1.0'
            and r['capture_percent']=='99.72' and r['steam_endpoint']=='isentropic'
            and r['return_endpoint']=='60C' and r['compressor_inlet_C']=='136.0'
            and r['overhead_fraction_DECLARED']=='0.0'),
        limits='Cuts are sufficient/necessary for nested eligible interval graph only; not for all physical topologies or real plant.')
    (ROOT/'results/finite_capacity_cut_QA_20261011.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
