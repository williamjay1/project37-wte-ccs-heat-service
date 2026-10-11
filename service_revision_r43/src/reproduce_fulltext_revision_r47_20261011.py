"""Recompute r46 thermal certificates and the r47 printed/origin diagnostic.

References are inspected only after calculation. An empty results directory is
required. No original article PDF or private operational series is needed.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ['audit.json', 'normalized_origin_grid.csv',
            'printed_wang_normalized.csv', 'conditional_value_diagnostic.csv',
            'temporal_origin_counterexamples.csv']


def compare(reference, fresh):
    counts = dict(numeric_fields=0, categorical_fields=0, differences=0,
                  maximum_scaled_error=0.0)
    exclusions = []
    examples = []

    def fail(loc, a, b):
        counts['differences'] += 1
        examples.append(dict(locator=loc, reference=str(a), fresh=str(b)))

    def walk(a, b, loc):
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(set(a) | set(b)):
                if loc == 'audit.json' and k in ['created_utc', 'ledger_sha256']:
                    exclusions.append(dict(locator=f'{loc}/{k}',
                        reason='Timestamp, or digest of a freshly regenerated ledger containing its own timestamp; all scientific ledger fields are separately checked by the preceding runner.'))
                elif k not in a or k not in b:
                    fail(f'{loc}/{k}', a.get(k, '<missing>'), b.get(k, '<missing>'))
                else:
                    walk(a[k], b[k], f'{loc}/{k}')
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                fail(loc+'/length', len(a), len(b))
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f'{loc}/{i}')
        elif isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
            counts['categorical_fields'] += 1
            if type(a) is not type(b) or a != b:
                fail(loc, a, b)
        else:
            try:
                x, y = float(a), float(b)
            except (ValueError, TypeError):
                counts['categorical_fields'] += 1
                if a != b:
                    fail(loc, a, b)
                return
            counts['numeric_fields'] += 1
            error = abs(x-y)/max(1.0, abs(x), abs(y))
            counts['maximum_scaled_error'] = max(counts['maximum_scaled_error'], error)
            if not math.isfinite(error) or error > 1e-10:
                fail(loc, a, b)

    for name in PRODUCTS:
        a, b = reference/name, fresh/name
        if not a.is_file() or not b.is_file():
            fail(name, a.is_file(), b.is_file())
            continue
        if name.endswith('.csv'):
            with a.open(encoding='utf-8', newline='') as x, b.open(encoding='utf-8', newline='') as y:
                left, right = csv.DictReader(x), csv.DictReader(y)
                if left.fieldnames != right.fieldnames:
                    fail(name+'/schema', left.fieldnames, right.fieldnames)
                walk(list(left), list(right), name)
        else:
            walk(json.loads(a.read_text(encoding='utf-8')),
                 json.loads(b.read_text(encoding='utf-8')), name)
    return dict(status='PASS' if counts['differences'] == 0 else 'FAIL',
                tolerance=1e-10, **counts, products=PRODUCTS,
                exclusions=exclusions, examples=examples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compare-only', action='store_true')
    args = parser.parse_args()
    if sys.platform == 'win32' and ROOT.drive.upper() != 'D:':
        raise SystemExit('Windows calculations must be stored on D:.')
    results = ROOT/'results'
    if not args.compare_only and results.exists() and any(results.iterdir()):
        raise SystemExit('Use an empty-results checkout; previous outputs are retained.')
    started = time.monotonic()
    commands = []
    if not args.compare_only:
        specs = [['src/reproduce_revision_with_artwork_r43.py'],
                 ['src/audit_near_neighbor_accounting_r47_20261011.py',
                  '--output-dir', 'results/near_neighbor_r47']]
        logs = ROOT/'logs/r47'
        logs.mkdir(parents=True, exist_ok=True)
        for i, spec in enumerate(specs, 1):
            begin = time.monotonic()
            p = subprocess.run([sys.executable]+spec, cwd=ROOT, capture_output=True,
                text=True, encoding='utf-8', errors='replace')
            (logs/f'{i:02d}.log').write_text(p.stdout+'\n'+p.stderr, encoding='utf-8')
            commands.append(dict(command=spec, returncode=p.returncode,
                                 elapsed_s=time.monotonic()-begin))
            print(f'{i}/2 {spec[0]}: exit {p.returncode}', flush=True)
            if p.returncode:
                print((p.stdout+'\n'+p.stderr)[-10000:])
                raise SystemExit('Failed computation; no reproduction pass declared.')
    check = compare(ROOT/'reference/near_neighbor_r47', results/'near_neighbor_r47')
    thermal = json.loads((results/'full_output_comparison.json').read_text(encoding='utf-8'))
    assert thermal['status'] == 'PASS' and thermal['differences'] == 0
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(),
        status='PASS fresh computation and comparison' if check['status'] == 'PASS' else 'FAIL',
        compare_only=args.compare_only, commands=commands, elapsed_s=time.monotonic()-started,
        numerical_stages=14, scientific_products=30, thermal_comparison=thermal,
        printed_origin_comparison=check,
        input_sha256=hashlib.sha256((ROOT/'datasets/near_neighbor_inputs_r47_20261011.json').read_bytes()).hexdigest(),
        scope='Computational reproduction and consistency, not empirical validation, legal settlement, journal submission or a new DOI.')
    (results/'r47_fulltext_reproduction.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'thermal_comparison'}, indent=2))
    if check['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
