"""Portable nine-stage revision runner; requires no C/F/E path or raw PDF.

Source anchors and declared domains are printed in the scripts and supplement.
This regenerates the Oct11 new analysis, not the preceding hourly/monthly
pipeline in Zenodo v1.0.0. Run from a D work checkout on the author's machine.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
STAGES=[
    'audit_primary_margin_20261011.py',
    'audit_steam_composite_margin_20261011.py',
    'audit_recovery_composite_20261011.py',
    'construct_finite_heat_path_20261011.py',
    'finite_path_decision_budget_20261011.py',
    'verify_finite_heat_path_20261011.py',
    'finite_service_capacity_20261011.py',
    'verify_finite_capacity_cuts_20261011.py',
    'audit_constructed_path_derating_20261011.py',
]


def main():
    (ROOT/'results').mkdir(exist_ok=True)
    logs=ROOT/'logs/r42_clean_run'
    logs.mkdir(parents=True,exist_ok=True)
    if sys.platform=='win32' and ROOT.drive.upper()!='D:':
        raise SystemExit('Windows compute outputs must be on D: under this project storage policy.')
    steps=[]
    for index,name in enumerate(STAGES,1):
        start=datetime.now(timezone.utc).isoformat()
        result=subprocess.run([sys.executable,str(ROOT/'src'/name)],cwd=ROOT,
            capture_output=True,text=True,encoding='utf-8',errors='replace')
        (logs/f'{index:02d}_{name}.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        steps.append(dict(stage=name,start_utc=start,end_utc=datetime.now(timezone.utc).isoformat(),
                          returncode=result.returncode))
        print(f'{index}/{len(STAGES)} {name}: exit {result.returncode}',flush=True)
        if result.returncode:
            raise SystemExit(f'FAILED: {name}; consult its log. No pass declared.')
    finite=json.loads((ROOT/'results/finite_heat_path_audit_20261011.json').read_text())
    budget=json.loads((ROOT/'results/finite_path_decision_budget_audit_20261011.json').read_text())
    cuts=json.loads((ROOT/'results/finite_capacity_cut_QA_20261011.json').read_text())
    assert finite['matrix_rows']==96 and finite['constructed_paths']==44
    assert budget['row_count']==93312 and cuts['lower_passes']==96 and cuts['upper_exclusions']==96
    reference=ROOT/'reference/r42_reference_metrics.json'
    current=dict(empty_window_K=json.loads((ROOT/'results/primary_margin_audit_20261011.json').read_text())['empty_window_K'],
        recovery_UA_MW_K=finite['representative']['recovery_network_sufficient_UA_bound_MW_K'],
        unused_eligible_MW=finite['representative']['unused_eligible_hot_MW'],
        derating_percent_01K=json.loads((ROOT/'results/constructed_path_derating_audit_20261011.json').read_text())['resolutions'][1]['maximum_proportional_derating_percent'],
        climate_upgrade_kg_year=next(r['included_delta_climate_kgCO2e_year'] for r in budget['central_rows']
                if r['comparator']=='95adapted100' and r['effective_fossil_value_EUR2020_t_SCENARIO']==300))
    comparisons={}
    if reference.exists():
        expected=json.loads(reference.read_text())
        comparisons={k:dict(current=v,expected=expected[k],absolute_error=abs(v-expected[k])) for k,v in current.items()}
        assert all(x['absolute_error']<=max(1e-8,abs(x['expected'])*1e-10) for x in comparisons.values())
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS nine analysis stages',
        root=str(ROOT),python=sys.version,stages=steps,key_metrics=current,
        reference_comparisons=comparisons,
        scripts_sha256={name:hashlib.sha256((ROOT/'src'/name).read_bytes()).hexdigest() for name in STAGES},
        scope='New Oct11 numerical model only. Not independent process validation, hourly/monthly rerun, publication or DOI release.')
    (ROOT/'results/r42_clean_reproduction.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=report['status'],key_metrics=current,reference_comparisons=comparisons),indent=2))


if __name__=='__main__':main()
