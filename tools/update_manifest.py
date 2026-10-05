"""Refresh file integrity after reviewed edits; not a scientific approval command."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]

def main():
    sources = json.loads((ROOT / 'docs/DATA_SOURCES.json').read_text(encoding='utf-8'))
    for item in sources['inputs']:
        assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256'], item['path']
    files = []
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or path.name == 'manifest.json':
            continue
        relative = path.relative_to(ROOT)
        if any(part in {'.git', '.venv', '__pycache__', 'cache', 'logs', 'results', 'temp'} for part in relative.parts):
            continue
        files.append(dict(path=relative.as_posix(),
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size))
    (ROOT / 'manifest.json').write_text(json.dumps(dict(
        created_utc=datetime.now(timezone.utc).isoformat(), files=files,
        state='Reviewed file inventory only; independent numerical checks, real authors and archival state remain separate.'), indent=2), encoding='utf-8')
    print('Manifest refreshed after unchanged-input checks; re-run tests/comparison before any changed code release.')

if __name__ == '__main__':
    main()
