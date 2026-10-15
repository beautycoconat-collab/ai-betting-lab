"""Create a checked phase 0.1 archive without credentials or transient files."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];destination=Path(a.out).resolve()
    allowed={'TEST_REPORT.md','CONTINUE.md'};comparison=[]
    with zipfile.ZipFile(a.baseline) as archive:
        for entry in archive.infolist():
            if entry.is_dir():continue
            name=str(Path(entry.filename).relative_to('ai-betting-lab'))
            unchanged=(root/name).read_bytes()==archive.read(entry)
            if not unchanged and name not in allowed:raise ValueError('unexpected_baseline_change:'+name)
            comparison.append({'file':name,'unchanged':unchanged})
    out=root/'reports/phase01';out.mkdir(parents=True,exist_ok=True)
    (out/'baseline-integrity.json').write_text(json.dumps({'files':comparison,'changed_documents':sorted(allowed)},indent=2))
    files=[]
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if not path.is_file() or path.is_symlink() or {'node_modules','__pycache__','.venv','.git','data'}.intersection(relative.parts):continue
        if path==destination or path.name.startswith('compat-') or (path.name.startswith('.env') and path.name!='.env.example'):continue
        if path.suffix in ('.pem','.key','.crt','.sqlite','.pyc') or path==out/'release-manifest.json':continue
        files.append(path)
    manifest=out/'release-manifest.json';manifest.write_text(json.dumps({str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},indent=2));files.append(manifest)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in files:archive.write(path,str(Path('ai-betting-lab')/path.relative_to(root)))
    with zipfile.ZipFile(destination) as archive:assert archive.testzip() is None
    print(json.dumps({'files':len(files),'bytes':destination.stat().st_size,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}))

if __name__=='__main__':main()
