"""Independent direct property/energy audit of continuum point-cut witnesses.

Does not import the production source curves or the finite allocator.
Verifies source properties, point-cut capacities, scale covariance, and
distinguishes method failure from outer exclusion. No field validation.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import json
import math
from iapws import IAPWS97


def water(t):
    return IAPWS97(P=1., T=t+273.15).h/1000


def direct(theta, capture, retained):
    inlet=IAPWS97(P=6.,T=673.15)
    extraction=IAPWS97(P=.4,s=inlet.s).h/1000
    liquid=IAPWS97(P=.4,T=333.15).h/1000
    threshold=IAPWS97(P=.4,T=theta+283.15).h/1000
    hp99=9.8*5.5/4.5
    rec=1. if capture=='99.72' else 18.1/(5.3+1.6+hp99)
    H=18.5 if capture=='99.72' else 19.9
    steam=H*retained*min(1.,max(0.,(extraction-max(liquid,threshold))/(extraction-liquid)))
    overhead=5.3*rec*retained*min(1.,max(0.,(91.-theta)/36.))
    compressor=1.6*rec*retained*min(1.,max(0.,(121.-theta)/66.))
    a=(water(100.)-water(theta))/(water(100.)-water(60.))
    b=max(0.,(water(77.)-water(theta))/(water(77.)-water(60.)))
    hp=hp99*rec*retained
    source=steam+overhead+compressor
    return source,a,b,hp,(source+hp*b)/a,36.5*a-hp*b-source


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        raise FileExistsError('Retain previous verification receipts.')
    with (args.data_dir/'continuum_cut_witnesses_r46_20261011.csv').open(newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    maximum=0.;values=[]
    keys=['eligible_non_hp_MW','cold_above_fraction','hp_above_fraction',
          'hp_delivered_module_MW','continuum_necessary_upper_MW','nominal_contract_cut_deficit_MW']
    for row in rows:
        theta=float(row['cold_grade_C']);retained=float(row['retained_duty_DECLARED'])
        independently=direct(theta,row['capture_percent'],retained)
        for key,actual in zip(keys,independently):
            error=abs(actual-float(row[key]))
            assert error<1e-10,(key,row,error)
            maximum=max(maximum,error)
        assert theta!=77. or independently[2]==0.
        values.append(dict(capture_percent=row['capture_percent'],retained_duty_DECLARED=retained,
                           grade_C=theta,independent_upper_MW=independently[4]))
    assert len(rows)==12
    with (args.data_dir/'continuum_inner_outer_brackets_r46_20261011.csv').open(newline='',encoding='utf-8') as f:
        brackets=list(csv.DictReader(f))
    for row in brackets:
        L=float(row['finite_constructed_lower_MW']);U=float(row['continuum_necessary_upper_MW'])
        r=float(row['retained_duty_DECLARED'])
        assert U>=L
        assert math.isclose(float(row['target_retained_fraction_sufficient']),36.5/L*r,abs_tol=1e-12)
        assert math.isclose(float(row['target_retained_fraction_necessary']),36.5/U*r,abs_tol=1e-12)
        assert float(row['finite_grid_failure_upper_NOT_physical_MW'])<U
    for capture,theta in [('99.72',77.),('95',60.)]:
        assert math.isclose(direct(theta,capture,.95)[4],.95*direct(theta,capture,1.)[4],abs_tol=1e-12)
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        status='PASS independent direct continuum property and energy witness checks',
        witnesses_checked=len(rows),numeric_fields_checked=len(rows)*len(keys),
        maximum_absolute_difference=maximum,brackets_checked=len(brackets),
        source_curve_imported=False,allocator_called=False,
        hp_above_77_MW=0.,scalar_temperature_bounds_K=[60.,77.,91.],
        scope='Algorithm/property arithmetic verification of declared-route necessary cuts; not independent factory states, whole-cycle validation, confidence interval or global continuous optimum.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
