"""Printed-source closure and an origin-preserving carbon-value diagnostic.

No source PDF, private plant series, fitted surrogate or proprietary software
is needed. Existing process outputs are dependencies, not frozen inputs.
The pooled comparator is intentionally a different accounting convention,
NOT an alternative valid fossil-only reward and NOT a recalculation of Wang's
plant, fuel changes, free allowances or reported 49/58 EUR thresholds.
"""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import argparse
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]


def normalized_balance(f, r):
    if not 0 <= f <= 1 or not 0 <= r <= 1:
        raise ValueError('Fractions must lie in [0,1]')
    return dict(fossil_fraction=f, captured_fraction=r,
                captured_fossil=f*r, captured_biogenic=(1-f)*r,
                emitted_fossil=f*(1-r), emitted_biogenic=(1-f)*(1-r),
                pooled_net_carbon=f-r,
                difference_physical_fossil_minus_pooled=(1-f)*r)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'datasets/near_neighbor_inputs_r47_20261011.json')
    parser.add_argument('--ledger', type=Path, default=ROOT/'results/finite_path_decision_budget_audit_20261011.json')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'results/near_neighbor_audit_r47_20261011')
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError('Existing run is retained; specify a new version.')
    inputs = json.loads(args.input.read_text(encoding='utf-8'))
    ledger = json.loads(args.ledger.read_text(encoding='utf-8'))
    o, w = inputs['sources']['ong'], inputs['sources']['wang']
    # Independent decimal and float closures; no fitting to a paper total.
    gas_t = o['flue_gas_kg_s'] * o['co2_mass_fraction'] * o['annual_hours'] * 3.6
    gas_decimal = Decimal(str(o['flue_gas_kg_s'])) * Decimal(str(o['co2_mass_fraction'])) * Decimal(str(o['annual_hours'])) * Decimal('3.6')
    assert math.isclose(gas_t, float(gas_decimal), abs_tol=1e-9)
    ong = dict(table9_generated_CO2_t_year=gas_t,
               section31_printed_CO2_t_year=o['annual_co2_text_t'],
               table9_minus_text_fraction=gas_t/o['annual_co2_text_t']-1,
               implied_table14_generated_CO2_t_year=o['capture_table14_kt']*1000/o['capture_table14_fraction'],
               table14_capture_at90percent_of_table9_t_year=.9*gas_t,
               table8_thermal_MJ_kg=o['reboiler_table8_MJ_kg'],
               table10_thermal_MJ_kg=o['reboiler_table10_MWh_t']*3.6,
               scope='Internal printed aggregate consistency only. Inconsistencies are not silently reconciled. No Modelica process or dispatch reproduction.')
    rows = []
    for f in [0., .1, .2, .4, .45, .6, .9, 1.]:
        for r in [0., .1, .442, .45, .527, .9, 1.]:
            b = normalized_balance(f, r)
            assert abs(b['captured_fossil']+b['emitted_fossil']-f) < 1e-14
            assert abs(b['captured_biogenic']+b['emitted_biogenic']-(1-f)) < 1e-14
            assert abs(b['emitted_fossil']-b['pooled_net_carbon']-b['captured_biogenic']) < 1e-14
            rows.append(b)
    for f, r in [(-.1,.5), (.5,1.1)]:
        try:
            normalized_balance(f,r)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid origin fractions accepted')
    printed = [dict(rule=rule, **normalized_balance(w['fossil_fraction'], w[key]))
               for rule, key in [('OR1','annual_capture_fraction_OR1'),('OR2','annual_capture_fraction_OR2')]]
    temporal=[]
    # Declared counterexamples, not measured seasonal composition or dispatch.
    for name, rates in [('capture_in_lower_fossil_period',[.9,.1]),
                         ('neutral_capture',[.5,.5]),
                         ('capture_in_higher_fossil_period',[.1,.9])]:
        fractions=[.2,.6]; weights=[.5,.5]
        fgen=sum(a*b for a,b in zip(weights,fractions))
        rbar=sum(a*b for a,b in zip(weights,rates))
        covariance=sum(a*(f-fgen)*(r-rbar) for a,f,r in zip(weights,fractions,rates))
        fcap=sum(a*f*r for a,f,r in zip(weights,fractions,rates))/rbar
        assert abs(fcap-fgen-covariance/rbar)<1e-14
        temporal.append(dict(scenario=name,generation_weighted_fossil=fgen,
            capture_weighted_fossil=fcap,mean_capture_fraction=rbar,
            weighted_covariance=covariance,
            annual_average_attribution_error_per_generated_t=rbar*(fgen-fcap)))
    # Central ledger selection is explicit; no best-case search.
    central = next(r for r in ledger['central_rows']
                   if r['comparator']=='95adapted100' and r['effective_fossil_value_EUR2020_t_SCENARIO']==300)
    f = central['fossil_share_SCENARIO']
    retained_fossil = central['additional_retained_fossil_t_year']
    retained_total = retained_fossil/f
    fixed = central['extra_capture_fixed_cost_STRESS_EUR2020_year']
    electricity_cost = central['total_additional_electricity_MW']*central['hours_SCENARIO']*central['electricity_price_EUR2020_MWh_SCENARIO']
    chain_cost = central['additional_captured_t_year']*50.
    cost = electricity_cost+chain_cost+fixed
    correct_threshold = cost/retained_fossil
    pooled_threshold = cost/retained_total
    assert abs(correct_threshold-central['zero_remaining_budget_value_EUR2020_t']) < 1e-9
    assert abs(pooled_threshold-f*correct_threshold) < 1e-9
    values=[]
    for v in [0.,100.,pooled_threshold,300.,correct_threshold,500.]:
        proper = v*retained_fossil-cost
        pooled = v*retained_total-cost
        difference = v*retained_total*(1-f)
        assert abs((pooled-proper)-difference) < 1e-8
        values.append(dict(effective_value_EUR2020_t=v,
                    fossil_only_remaining_scope_EUR2020_year=proper,
                    pooled_all_origin_remaining_scope_EUR2020_year=pooled,
                    origin_misattribution_EUR2020_year=difference))
    finance = dict(additional_retained_total_t_year=retained_total,
                  additional_retained_fossil_t_year=retained_fossil,
                  noncarbon_included_cost_EUR2020_year=cost,
                  fossil_only_zero_scope_value_EUR2020_t=correct_threshold,
                  pooled_zero_scope_value_EUR2020_t=pooled_threshold,
                  sign_disagreement_open_interval_EUR2020_t=[pooled_threshold,correct_threshold],
                  values=values,
                  scope='Effective retained-carbon valuation at fixed r46 thermal paths and ledger assumptions. Not plant investment profit, correction of another paper or actual ETS deduction.')
    args.output_dir.mkdir(parents=True)
    for name,data in [('normalized_origin_grid.csv',rows),('printed_wang_normalized.csv',printed),('conditional_value_diagnostic.csv',values),('temporal_origin_counterexamples.csv',temporal)]:
        with (args.output_dir/name).open('w',newline='',encoding='utf-8') as out:
            writer=csv.DictWriter(out,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),
                status='PASS deterministic normalized balances, printed arithmetic and unchanged central-ledger identity',
                input_sha256=sha(args.input), ledger_sha256=sha(args.ledger),
                ong_printed_closure=ong, wang_normalized_printed_parameters=printed,
                financial_origin_diagnostic=finance, grid_rows=len(rows),
                temporal_origin_counterexamples=temporal,
                uncertainty='Structural accounting conventions; not a sample, confidence interval or probability distribution.',
                original_pdfs_redistributed=False)
    (args.output_dir/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
