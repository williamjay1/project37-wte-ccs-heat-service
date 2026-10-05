"""Compare every frozen scientific numeric output, with documented volatile exclusions."""
from pathlib import Path
import argparse, csv, json, math

ROOT = Path(__file__).resolve().parents[1]
TIMING = {'created_utc', 'started_utc', 'solver_seconds', 'total_solver_seconds'}

def read(path):
    if path.suffix == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as stream:
            return list(csv.DictReader(stream))
    return json.loads(path.read_text(encoding='utf-8'))

def compare_outputs(fresh):
    differences, names, certified_defaults = [], [], []
    counts = {'numeric_fields': 0, 'maximum_scaled_error': 0.0}
    def walk(a, b, locator):
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted((set(a) | set(b)) - TIMING):
                if key not in a or key not in b:
                    if key == 'maintained_hot_loss_MW_SCENARIO' and key in b and float(b[key]) == 0:
                        certified_defaults.append(locator + '/' + key)
                    else:
                        differences.append([locator + '/' + key, a.get(key), b.get(key)])
                else:
                    walk(a[key], b[key], locator + '/' + key)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                differences.append([locator + '/length', len(a), len(b)])
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f'{locator}/{i}')
        elif isinstance(a, bool) or isinstance(b, bool):
            if a != b:
                differences.append([locator, a, b])
        else:
            try:
                x, y = float(a), float(b)
                counts['numeric_fields'] += 1
                if math.isnan(x) and math.isnan(y):
                    return
                error = 0 if x == y else abs(x-y) / max(1, abs(x), abs(y))
                counts['maximum_scaled_error'] = max(counts['maximum_scaled_error'], error)
                if error > 1e-10 or not math.isfinite(error):
                    differences.append([locator, a, b])
            except (ValueError, TypeError):
                if a != b:
                    differences.append([locator, a, b])
    for reference in sorted((ROOT / 'reference_results').glob('*')):
        if reference.suffix not in {'.json', '.csv'}:
            continue
        actual = fresh / 'results' / reference.name
        if reference.name == 'hagenholz_monthly_clean_r35_20261002.csv':
            actual = fresh / 'datasets' / reference.name
        if not actual.is_file():
            differences.append([reference.name, 'reference present', 'fresh output missing'])
            continue
        a, b = read(reference), read(actual)
        # Original frozen CSVs predate explicit default metadata. Certify each
        # default against the unchanged inputs; do not drop arbitrary fields.
        if reference.suffix == '.csv':
            for i, (old, new) in enumerate(zip(a, b)):
                expected = {'assumed_heatpump_COP': 5.5, 'unavailable_hours': 0}
                if reference.name == 'physical_service_feasibility_pilot_r32_20261002.csv':
                    expected.update(storage_hot_C=90, storage_approach_K=5,
                                    storage_power_limit_MW=37.3,
                                    storage_usable_capacity_MWh=37.3*float(old['store_hours']),
                                    hydraulic_flow_limit_kg_s='')
                for key, value in expected.items():
                    if key not in old and key in new:
                        valid = new[key] == value if value == '' else float(new[key]) == value
                        if not valid:
                            differences.append([f'{reference.name}/{i}/{key}', value, new[key]])
                        else:
                            certified_defaults.append(f'{reference.name}/{i}/{key}')
                            new.pop(key)
        walk(a, b, reference.name)
        names.append(reference.name)
    if not names:
        differences.append(['reference_results', 'nonempty benchmark', 'no comparisons'])
    return dict(status='PASS' if not differences else 'FAIL', compared_files=names,
                **counts, timing_keys_ignored=sorted(TIMING),
                certified_default_cells=len(certified_defaults), differences=differences,
                scope='Computational agreement, not independent operational validation.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fresh-dir', required=True)
    args = parser.parse_args()
    fresh = Path(args.fresh_dir).resolve()
    if not fresh.is_dir():
        raise FileNotFoundError(fresh)
    report = compare_outputs(fresh)
    (fresh / 'results/reference_comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'compared_files'}, indent=2))
    raise SystemExit(0 if report['status'] == 'PASS' else 1)

if __name__ == '__main__':
    main()
