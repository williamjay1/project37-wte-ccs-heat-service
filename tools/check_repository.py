"""Read-only integrity, source attribution and public-file checks."""
from pathlib import Path
import hashlib, json, re, sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)')

def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    errors = []
    for item in manifest['files']:
        path = (ROOT / item['path']).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            errors.append('missing/unsafe path: ' + item['path'])
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            errors.append('changed hash: ' + item['path'])
        if path.suffix in {'.py', '.md', '.json', '.yml', '.yaml', '.csv', '.cff', '.txt'}:
            content = path.read_text(encoding='utf-8-sig')
            if FORBIDDEN.search(content):
                errors.append('credential-pattern match: ' + item['path'])
            if re.search(r'[DEFC]:[\\/](?:Users|AcademicData|MLWork)', content):
                errors.append('originating-machine absolute path: ' + item['path'])
    sources = json.loads((ROOT / 'docs/DATA_SOURCES.json').read_text(encoding='utf-8'))
    if len(sources['inputs']) != 6:
        errors.append('Expected six actual computational inputs.')
    for record in sources['inputs']:
        path = ROOT / record['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            errors.append('input hash/provenance mismatch: ' + record['path'])
        if not record['source_url'] or not record['license_basis'] or not record['claim_boundary']:
            errors.append('incomplete source record: ' + record['path'])
    print(json.dumps(dict(status='PASS' if not errors else 'FAIL',
        files_checked=len(manifest['files']), inputs_checked=len(sources['inputs']),
        errors=errors, warning='Integrity/access/licensing records are not scientific validation or author approval.'), indent=2))
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
