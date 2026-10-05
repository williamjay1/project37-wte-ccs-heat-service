"""Portable fresh-results runner; references are never used as model inputs."""
from pathlib import Path
import argparse, json, os, shutil, subprocess, sys, time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
STEPS = [
    'physical_service_pilot_r32_20261002.py',
    'physical_service_feasibility_r32_20261002.py',
    'verify_physical_service_r32_20261002.py',
    'physical_service_caseB_check_r32_20261002.py',
    'physical_service_volume_flow_r32_20261002.py',
    'verify_service_contract_r32_20261002.py',
    'physical_service_caseB_envelope_r32_20261002.py',
    'physical_service_annual_matrix_r32_20261002.py',
    'physical_service_annual_ledger_r32_20261002.py',
    'physical_service_followup_r32_20261002.py',
    'physical_service_hot_loss_stress_r32_20261002.py',
    'physical_service_adaptation_boundary_r32_20261002.py',
    'verify_adaptation_boundary_r32_20261002.py',
    'plot_physical_service_r32_20261002.py',
    'steam_phase_domain_r33_20261002.py',
    'verify_steam_phase_r33_20261002.py',
    'plot_steam_phase_r33_20261002.py',
    'check_herraiz_public_process_r33_20261002.py',
    'clean_monthly_cc0_r35_20261002.py',
    'swiss_monthly_service_cuts_r35_20261002.py',
    'verify_monthly_service_cuts_r35_20261002.py',
    'verify_water_state_boundary_r35_20261002.py',
    'exact_water_comparison_r35_20261002.py',
    'exact_water_followup_r35_20261002.py',
    'plot_exact_physical_r35_20261002.py',
    'plot_monthly_service_r35_20261002.py',
    'plot_nature_figures_r39_20261005.py',
    'audit_nature_artwork_r39_20261005.py',
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fresh-dir', required=True)
    parser.add_argument('--dependency-dir', help='Optional existing dependency path; no results are reused.')
    args = parser.parse_args()
    work = Path(args.fresh_dir).resolve()
    if work.exists():
        raise FileExistsError('Fresh directory already exists; no files will be removed or reused.')
    if work == ROOT or ROOT.is_relative_to(work):
        raise ValueError('Do not use the repository or its parent as a fresh calculation directory.')
    work.mkdir(parents=True)
    for name in ['src', 'datasets']:
        shutil.copytree(ROOT / name, work / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copyfile(ROOT / 'requirements.txt', work / 'requirements.txt')
    for name in ['results', 'logs', 'cache', 'temp']:
        (work / name).mkdir()
    env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
               MPLCONFIGDIR=str(work / 'cache/matplotlib'))
    if args.dependency_dir:
        dependency = Path(args.dependency_dir).resolve()
        if not dependency.is_dir():
            raise FileNotFoundError(dependency)
        env['PYTHONPATH'] = str(dependency) + os.pathsep + env.get('PYTHONPATH', '')
    started = time.perf_counter()
    records = []
    for i, script in enumerate(STEPS, 1):
        print(f'[{i}/{len(STEPS)}] {script}', flush=True)
        t = time.perf_counter()
        with (work / 'logs' / (script + '.log')).open('w', encoding='utf-8') as log:
            result = subprocess.run([sys.executable, '-X', 'utf8', str(work / 'src' / script)],
                                    cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
        records.append(dict(script=script, exit_code=result.returncode, wall_seconds=time.perf_counter()-t))
        if result.returncode:
            print((work / 'logs' / (script + '.log')).read_text(encoding='utf-8')[-5000:])
            raise SystemExit(result.returncode)
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                  status='PASS actual fresh-results execution', stages=records,
                  elapsed_seconds=time.perf_counter()-started,
                  reference_results_seeded=False,
                  scientific_scope='Computational reproduction; not factory validation, full LCA or submission clearance.')
    (work / 'results/reproduction_receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)

if __name__ == '__main__':
    main()
