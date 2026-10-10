"""Refresh tracked public-file checksums; never inspect raw storage or secrets.

Run only after deliberately staging the intended public snapshot. This does
not publish anything or validate science. Generated run products stay ignored.
"""
from pathlib import Path
import hashlib
import json
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
files = []
for name in sorted(n for n in names if n and n != 'manifest.json'):
    path = (ROOT/name).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f'Unsafe or missing tracked path: {name}')
    files.append(dict(path=name, bytes=path.stat().st_size,
                      sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(ROOT/'manifest.json').write_text(json.dumps(dict(
    created_utc=datetime.now(timezone.utc).isoformat(), files=files,
    scope='Tracked public computational files; no DOI or scientific validation implied.'),
    indent=2), encoding='utf-8')
print(json.dumps(dict(files=len(files), status='manifest refreshed locally'), indent=2))
