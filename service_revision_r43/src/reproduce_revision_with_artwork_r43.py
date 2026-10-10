"""Recompute thirteen service stages, inner/outer certificates, QA and artwork.

The separate preceding public pipeline retains its own runner. No access to a
paid database, source-paper PDF, skill installation or original raw drive is
needed here. Frozen references are compared after calculation, not preloaded
as scientific results. Use a fresh D: checkout on the author's Windows host.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import io
import importlib.metadata
import json
import math
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def compare_csv_payload(fresh, reference):
    """Strict schema/labels, 1e-12 scaled numeric tolerance and recorded bytes.

    Floating results from different libm implementations can differ by a few
    ulps. The panel-data tolerance is tighter than the scientific-output test;
    it is not a permission to round or overwrite the input/reference values.
    """
    a = list(csv.reader(io.StringIO(fresh.decode('utf-8'))))
    b = list(csv.reader(io.StringIO(reference.decode('utf-8'))))
    matched = len(a) == len(b) and bool(a) and a[0] == b[0]
    maximum = 0.0
    unequal_cells = 0
    if matched:
        for row_a, row_b in zip(a[1:], b[1:]):
            if len(row_a) != len(row_b):
                matched = False
                break
            for x, y in zip(row_a, row_b):
                if x == y:
                    continue
                unequal_cells += 1
                if x != x.strip() or y != y.strip():
                    matched = False
                    continue
                try:
                    n, m = float(x), float(y)
                except ValueError:
                    matched = False
                    continue
                if not math.isfinite(n) or not math.isfinite(m):
                    matched = False
                    continue
                error = abs(n-m)/max(1.0, abs(n), abs(m))
                maximum = max(maximum, error)
                if error > 1e-12:
                    matched = False
    return dict(raw_byte_identical=fresh == reference,
                payload_identical_after_crlf_normalization=
                    fresh.replace(b'\r\n', b'\n') == reference.replace(b'\r\n', b'\n'),
                source_values_match=matched, unequal_serialized_cells=unequal_cells,
                maximum_scaled_numeric_error=maximum, numerical_tolerance=1e-12)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artwork-only',action='store_true',
                        help='Requires already computed scientific results; not a new numerical reproduction.')
    args=parser.parse_args()
    if sys.platform=='win32' and ROOT.drive.upper()!='D:':
        raise SystemExit('Windows computational and figure outputs must be on D:.')
    required=['primary_margin_audit_20261011.json','finite_heat_path_audit_20261011.json',
              'finite_path_decision_budget_audit_20261011.json']
    if not args.artwork_only and any((ROOT/'results'/n).exists() for n in required):
        raise SystemExit('Scientific outputs already exist. Use a fresh checkout or --artwork-only; no silent overwrite.')
    commands=[]
    if not args.artwork_only:
        commands.extend([
            ['src/reproduce_service_revision_r42.py'],
            ['src/certify_continuous_service_domain_r45_20261011.py'],
            ['src/verify_continuous_domain_transport_r45_20261011.py'],
            ['src/certify_continuum_outer_cuts_r46_20261011.py',
             '--output-dir','results/continuum_outer_r46'],
            ['src/verify_continuum_outer_cuts_r46_20261011.py',
             '--data-dir','results/continuum_outer_r46',
             '--output','results/continuum_outer_r46/continuum_outer_independent_QA_r46_20261011.json'],
            ['src/compare_service_revision_outputs_r42.py','--reference-dir','reference/outputs',
             '--fresh-dir','results','--output','results/full_output_comparison.json',
             '--include-continuous-domain','--include-continuum-outer']])
    commands.extend([
        ['src/plot_service_frontier_r41_20261011.py','--data-root',str(ROOT),
         '--output-dir',str(ROOT/'results/artwork/frontier')],
        ['src/plot_finite_path_budget_r42_20261011.py','--data-root',str(ROOT),
         '--output-dir',str(ROOT/'results/artwork/construction')],
        ['src/draw_service_certificate_GA_r46_20261011.py','--data-root',str(ROOT),
         '--output-dir',str(ROOT/'output/graphical_abstract')]])
    logs=ROOT/'logs/r43_integrated_reproduction'
    logs.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    records=[]
    for index,cmd in enumerate(commands,1):
        begin=time.monotonic()
        completed=subprocess.run([sys.executable]+cmd,cwd=ROOT,capture_output=True,text=True,
                                 encoding='utf-8',errors='replace')
        log=logs/f'{index:02d}_{Path(cmd[0]).stem}.log'
        log.write_text(completed.stdout+'\n'+completed.stderr,encoding='utf-8')
        records.append(dict(command=cmd,returncode=completed.returncode,elapsed_s=time.monotonic()-begin))
        print(f'{index}/{len(commands)} {cmd[0]}: exit {completed.returncode}',flush=True)
        if completed.returncode:
            print((completed.stdout+'\n'+completed.stderr)[-12000:], flush=True)
            raise SystemExit(f'Failed stage; inspect {log}. No reproduction pass declared.')
    refs=ROOT/'reference/artwork'
    comparisons=[]
    for subdir,prefix in [('frontier','Fig2'),('construction','Fig3')]:
        for panel in ['a','b']:
            name=f'{prefix}_panel_{panel}_data.csv'
            a=ROOT/'results/artwork'/subdir/name
            b=refs/subdir/name
            if b.exists():
                check=compare_csv_payload(a.read_bytes(),b.read_bytes())
                assert check['source_values_match'], f'Different source-bound plot data: {name}'
                comparisons.append(dict(file=f'{subdir}/{name}',**check,
                    scope='Schema/labels exact; 1e-12 scaled numeric tolerance; raw and newline-normalized bytes separately recorded.'))
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),
                status='PASS artwork only' if args.artwork_only else 'PASS thirteen science stages including continuous-domain and continuum outer certificates, independent checks and three artwork products',
                elapsed_s=time.monotonic()-start,python=sys.version,commands=records,
                versions={n:importlib.metadata.version(n) for n in ['numpy','scipy','matplotlib','pandas','iapws']},
                plot_data_comparisons=comparisons,
                source_sha256={Path(c[0]).name:hashlib.sha256((ROOT/c[0]).read_bytes()).hexdigest() for c in commands},
                visual_status='PENDING actual rendered inspection',
                scope='New revision only; not preceding hourly/monthly rerun, empirical validation, public release or journal submission.')
    (ROOT/'results/r43_integrated_reproduction.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
