"""Compare all new scientific JSON/CSV outputs after an empty-results run.

Reference outputs are read only after computation. Differences are not repaired
or overwritten. Exclusions are creation timestamps, an optional historical
submitted-PDF identifier, and explicitly certified additions documenting the
unchanged 36.5 MW contract. Scientific values are never dropped or tuned.
"""
from pathlib import Path
from datetime import datetime, timezone
from itertools import zip_longest
import argparse
import csv
import json
import math

FILES = [
    'primary_margin_audit_20261011.json', 'primary_margin_frontier_20261011.csv',
    'primary_flow_curve_20261011.csv', 'steam_composite_margin_20261011.json',
    'steam_composite_margin_20261011.csv', 'recovery_composite_audit_20261011.json',
    'recovery_composite_frontier_20261011.csv', 'finite_heat_path_matrix_20261011.csv',
    'finite_heat_path_allocation_20261011.csv', 'finite_heat_path_audit_20261011.json',
    'finite_heat_path_independent_QA_20261011.json', 'finite_path_decision_budget_20261011.csv',
    'finite_path_decision_budget_audit_20261011.json', 'finite_service_capacity_20261011.csv',
    'finite_service_capacity_audit_20261011.json', 'finite_capacity_cut_QA_20261011.json',
    'constructed_path_derating_audit_20261011.json',
]
HISTORICAL_SCOPE = ('Optional submitted-file identifier only; no numerical input '
                    'is read from that PDF.')
MISSING = object()


def compare(reference_dir, fresh_dir):
    counts = dict(numeric_fields=0, categorical_fields=0, differences=0,
                  maximum_scaled_error=0.0)
    examples, exclusions, compared = [], [], []
    fixed_contract = '36.5 MW at80/50 C, fixed residual-waste throughput; primary60 C return, 5 K minimum interface approach.'
    contract_certified = all(json.loads((directory/'finite_heat_path_audit_20261011.json').read_text(
        encoding='utf-8'))['fixed_secondary_service'] == fixed_contract
        for directory in [reference_dir, fresh_dir])

    def difference(locator, old, new):
        counts['differences'] += 1
        if len(examples) < 120:
            examples.append(dict(locator=locator, reference=str(old), fresh=str(new)))

    def walk(old, new, locator):
        if isinstance(old, dict) and isinstance(new, dict):
            for key in sorted(set(old) | set(new)):
                address = locator + '/' + key
                if key == 'created_utc' or (key=='elapsed_s' and locator in ['continuous_service_domain_r45_20261011.json','continuous_domain_transport_QA_r45_20261011.json','continuum_outer_r46/continuum_outer_cut_certificate_r46_20261011.json']):
                    exclusions.append(dict(locator=address, reason='volatile timestamp or measured run duration'))
                    continue
                if address == 'primary_margin_audit_20261011.json/manuscript_sha256':
                    exclusions.append(dict(locator=address, reference=old.get(key), fresh=new.get(key),
                        reason='Optional historical submitted-PDF identifier, not a numerical input'))
                    continue
                if address == 'primary_margin_audit_20261011.json/historical_file_scope' and key not in old:
                    if new[key] == HISTORICAL_SCOPE:
                        exclusions.append(dict(locator=address, reason='Certified non-input metadata addition'))
                        continue
                if (key == 'demand_MW' and key not in old and key in new and contract_certified
                    and locator.split('/')[0] in ['finite_heat_path_matrix_20261011.csv',
                                                   'finite_heat_path_audit_20261011.json',
                                                   'finite_path_decision_budget_audit_20261011.json']
                    and float(new[key]) == 36.5):
                    exclusions.append(dict(locator=address, fresh=new[key],
                        reason='Certified explicit demand field: both frozen and fresh fixed-service contracts are 36.5 MW'))
                    continue
                if key not in old or key not in new:
                    difference(address, old.get(key, '<missing>'), new.get(key, '<missing>'))
                else:
                    walk(old[key], new[key], address)
        elif isinstance(old, list) and isinstance(new, list):
            if len(old) != len(new):
                difference(locator + '/length', len(old), len(new))
            for index, (a, b) in enumerate(zip(old, new)):
                walk(a, b, f'{locator}/{index}')
        elif isinstance(old, bool) or isinstance(new, bool) or old is None or new is None:
            counts['categorical_fields'] += 1
            if type(old) is not type(new) or old != new:
                difference(locator, old, new)
        else:
            try:
                a, b = float(old), float(new)
            except (TypeError, ValueError):
                counts['categorical_fields'] += 1
                if old != new:
                    difference(locator, old, new)
                return
            counts['numeric_fields'] += 1
            if math.isnan(a) and math.isnan(b):
                return
            error = 0.0 if a == b else abs(a-b) / max(1.0, abs(a), abs(b))
            if not math.isfinite(error):
                difference(locator, old, new)
            else:
                counts['maximum_scaled_error'] = max(counts['maximum_scaled_error'], error)
                if error > 1e-10:
                    difference(locator, old, new)

    for name in FILES:
        old, new = reference_dir/name, fresh_dir/name
        if not old.is_file() or not new.is_file():
            difference(name, old.is_file(), new.is_file())
            continue
        if old.suffix == '.csv':
            with old.open(encoding='utf-8-sig', newline='') as a, new.open(encoding='utf-8-sig', newline='') as b:
                left, right = csv.DictReader(a), csv.DictReader(b)
                if left.fieldnames != right.fieldnames:
                    added_fixed_demand = (name == 'finite_heat_path_matrix_20261011.csv'
                        and contract_certified and 'demand_MW' not in left.fieldnames
                        and [key for key in right.fieldnames if key != 'demand_MW'] == left.fieldnames)
                    if added_fixed_demand:
                        exclusions.append(dict(locator=name+'/headers',
                            reason='Explicit fixed-demand field addition only; every cell certified against unchanged service'))
                    else:
                        difference(name + '/headers', left.fieldnames, right.fieldnames)
                for row, (x, y) in enumerate(zip_longest(left, right, fillvalue=MISSING)):
                    if x is MISSING or y is MISSING:
                        difference(f'{name}/row/{row}', x is not MISSING, y is not MISSING)
                    else:
                        walk(x, y, f'{name}/row/{row}')
        else:
            walk(json.loads(old.read_text(encoding='utf-8')),
                 json.loads(new.read_text(encoding='utf-8')), name)
        compared.append(name)
    return dict(created_utc=datetime.now(timezone.utc).isoformat(),
        status='PASS' if counts['differences'] == 0 and len(compared) == len(FILES) else 'FAIL',
        reference_dir=str(reference_dir), fresh_dir=str(fresh_dir), compared_files=compared,
        **counts, difference_examples=examples, exclusions=exclusions,
        tolerance='absolute difference / max(1, abs(reference), abs(fresh)) <= 1e-10',
        scope=f'Computational agreement of all {len(FILES)} scientific outputs; not empirical process validation.')


def main():
    global FILES
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-dir', type=Path, required=True)
    parser.add_argument('--fresh-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--include-continuous-domain',action='store_true')
    parser.add_argument('--include-continuum-outer',action='store_true')
    args = parser.parse_args()
    if args.include_continuous_domain:
        FILES=FILES+['continuous_service_domain_r45_20261011.json',
                     'continuous_service_capacity_r45_20261011.csv',
                     'continuous_service_allocation_r45_20261011.csv',
                     'continuous_domain_transport_QA_r45_20261011.json']
    if args.include_continuum_outer:
        FILES=FILES+['continuum_outer_r46/'+name for name in [
            'continuum_outer_cut_certificate_r46_20261011.json',
            'continuum_inner_outer_brackets_r46_20261011.csv',
            'continuum_cut_witnesses_r46_20261011.csv',
            'continuum_outer_independent_QA_r46_20261011.json']]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = compare(args.reference_dir.resolve(), args.fresh_dir.resolve())
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['compared_files','exclusions']}, indent=2))
    raise SystemExit(0 if report['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
