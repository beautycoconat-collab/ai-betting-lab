"""Verify and unpack the complete AI Betting Lab source without external services."""
import hashlib,io,json,zipfile
from pathlib import Path

root=Path(__file__).resolve().parent
manifest=json.loads((root/'source-package.json').read_text())
parts=[]
for item in manifest['parts']:
    path=(root/item['name']).resolve()
    if path.parent!=root:raise ValueError('invalid_part_path')
    body=path.read_bytes()
    if hashlib.sha256(body).hexdigest()!=item['sha256']:raise ValueError('part_hash_mismatch')
    parts.append(body)
body=b''.join(parts)
if hashlib.sha256(body).hexdigest()!=manifest['archive_sha256']:raise ValueError('archive_hash_mismatch')
with zipfile.ZipFile(io.BytesIO(body)) as archive:
    for member in archive.infolist():
        name=Path(member.filename)
        if not name.parts or name.parts[0]!='ai-betting-lab' or '..' in name.parts:raise ValueError('invalid_archive_path')
        relative=Path(*name.parts[1:]);target=(root/relative).resolve()
        if not target.is_relative_to(root):raise ValueError('path_escape')
        if member.is_dir():target.mkdir(parents=True,exist_ok=True);continue
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(member))
print('Complete original source, models, historical evidence and tests restored. No network requests.')
