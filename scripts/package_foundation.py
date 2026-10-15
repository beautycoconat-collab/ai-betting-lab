"""Package source and evidence without transient databases or dependencies."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = Path(args.out).resolve()
    excluded = {'node_modules', '__pycache__', '.venv', '.git', 'data'}
    files = []
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if not path.is_file() or path.is_symlink() or excluded.intersection(rel.parts):
            continue
        if path == output or path.name.startswith('compat-') or path.name in {'.env', 'release-manifest.json'}:
            continue
        if path.suffix in {'.pyc', '.sqlite', '.sqlite3'}:
            continue
        files.append(path)
    manifest = root/'reports/phase0/release-manifest.json'
    manifest.write_text(json.dumps({str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, indent=2))
    files.append(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, str(Path('ai-betting-lab')/path.relative_to(root)))
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
    print(json.dumps({'file':str(output),'files':len(files),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))

if __name__ == '__main__':
    main()
