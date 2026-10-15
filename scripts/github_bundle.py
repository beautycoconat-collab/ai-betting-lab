"""Losslessly bundle large historical test artifacts for source repository upload."""
import argparse,hashlib,json,zipfile,io
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()

def create():
    folder=ROOT/'artifact_bundle';folder.mkdir(exist_ok=True)
    files=[p for base in ('reports','evidence') for p in (ROOT/base).rglob('*') if p.is_file() and p.stat().st_size>200_000]
    buffer=io.BytesIO();entries={}
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            name=str(path.relative_to(ROOT));data=path.read_bytes();archive.writestr(name,data);entries[name]=sha(data)
    data=buffer.getvalue();chunks=[]
    for i,start in enumerate(range(0,len(data),2_000_000)):
        name=f'part-{i:03d}.bin';body=data[start:start+2_000_000];(folder/name).write_bytes(body)
        chunks.append({'file':name,'sha256':sha(body),'size':len(body)})
    (folder/'manifest.json').write_text(json.dumps({'archive_sha256':sha(data),'chunks':chunks,'files':entries},indent=2))
    print(json.dumps({'files':len(entries),'chunks':len(chunks),'bytes':len(data)}))

def restore():
    folder=ROOT/'artifact_bundle';manifest=json.loads((folder/'manifest.json').read_text());parts=[]
    for item in manifest['chunks']:
        path=(folder/item['file']).resolve()
        if path.parent!=folder.resolve():raise ValueError('invalid_chunk_path')
        data=path.read_bytes()
        if sha(data)!=item['sha256'] or len(data)!=item['size']:raise ValueError('chunk_hash_mismatch')
        parts.append(data)
    data=b''.join(parts)
    if sha(data)!=manifest['archive_sha256']:raise ValueError('archive_hash_mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if set(archive.namelist())!=set(manifest['files']):raise ValueError('manifest_mismatch')
        for name,digest in manifest['files'].items():
            path=(ROOT/name).resolve()
            if not path.is_relative_to(ROOT) or path.relative_to(ROOT).parts[0] not in ('reports','evidence'):raise ValueError('invalid_artifact_path')
            body=archive.read(name)
            if sha(body)!=digest:raise ValueError('artifact_hash_mismatch')
            if path.exists() and sha(path.read_bytes())!=digest:raise ValueError('refusing_to_replace_changed_artifact')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    print(json.dumps({'restored_unchanged_files':len(manifest['files'])}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['create','restore']);a=p.parse_args()
    create() if a.action=='create' else restore()
