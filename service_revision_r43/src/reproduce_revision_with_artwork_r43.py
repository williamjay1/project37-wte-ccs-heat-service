"""Recompute nine service stages, continuous certificate, independent QA and artwork.

The separate preceding public pipeline retains its own runner. No access to a
paid database, source-paper PDF, skill installation or original raw drive is
needed here. Frozen references are compared after calculation, not preloaded
as scientific results. Use a fresh D: checkout on the author's Windows host.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


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
            ['src/compare_service_revision_outputs_r42.py','--reference-dir','reference/outputs',
             '--fresh-dir','results','--output','results/full_output_comparison.json',
             '--include-continuous-domain']])
    commands.extend([
        ['src/plot_service_frontier_r41_20261011.py','--data-root',str(ROOT),
         '--output-dir',str(ROOT/'results/artwork/frontier')],
        ['src/plot_finite_path_budget_r42_20261011.py','--data-root',str(ROOT),
         '--output-dir',str(ROOT/'results/artwork/construction')],
        ['src/draw_graphical_abstract_r42_20261011.py','--data-root',str(ROOT),
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
                assert a.read_bytes()==b.read_bytes(), f'Different source-bound plot data: {name}'
                comparisons.append(dict(file=f'{subdir}/{name}',byte_identical=True))
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),
                status='PASS artwork only' if args.artwork_only else 'PASS nine science stages plus continuous-domain certificate, independent transport verification and three artwork products',
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
