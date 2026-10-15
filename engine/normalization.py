"""Pure parsing, whole-conflict quarantine, and auditable cached replay (no HTTP)."""
import hashlib,json,zlib
from pathlib import Path
from betting_lab.domain import utcnow,digest
from .adapters import ADAPTERS

def normalize(adapter,payload,params):
    seen={};indices={};bad={};conflicts=set()
    for i,row in enumerate(adapter.rows(payload)):
        try:
            item=adapter.parse(row,params).dict();key=item['native_id']
            if key in seen:
                indices[key].append(i)
                if seen[key]!=item:conflicts.add(key)
            else:seen[key]=item;indices[key]=[i]
        except (ValueError,TypeError,KeyError,AttributeError) as e:bad[i]=type(e).__name__+':'+str(e)[:100]
    for key in conflicts:
        for i in indices[key]:bad[i]='conflicting_native_duplicate'
    return [v for k,v in seen.items() if k not in conflicts],sorted(bad.items())

def replay(queue,snapshot_id):
    """Rebuild derived rows only; raw evidence, observation time, request ledger unchanged."""
    db=queue.db
    r=db.execute('SELECT s.*,j.params,j.kind FROM v2_snapshots s JOIN v2_jobs j ON j.id=s.job_id WHERE s.id=?',(snapshot_id,)).fetchone()
    if not r or r['kind']!='collect':raise ValueError('collect_snapshot_required')
    adapter=ADAPTERS[r['source']];body=zlib.decompress(r['body'])
    if digest(body)!=r['sha256']:raise ValueError('snapshot_hash_mismatch')
    good,bad=normalize(adapter,adapter.decode(body,'collect'),json.loads(r['params']))
    parser_hash=digest([hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),hashlib.sha256(Path(__file__).with_name('adapters.py').read_bytes()).hexdigest()])
    db.execute('CREATE TABLE IF NOT EXISTS v2_normalization_runs(id TEXT PRIMARY KEY,snapshot_id TEXT,parser_sha256 TEXT,run_at TEXT,accepted INTEGER,rejected INTEGER)')
    key=digest([snapshot_id,parser_hash])
    with db:
        db.execute('DELETE FROM v2_results WHERE snapshot_id=?',(snapshot_id,));db.execute('DELETE FROM v2_rejected WHERE snapshot_id=?',(snapshot_id,))
        for item in good:db.execute('INSERT INTO v2_results VALUES(?,?,?,?)',(snapshot_id,r['source'],item['native_id'],json.dumps(item,ensure_ascii=False)))
        for i,reason in bad:db.execute('INSERT INTO v2_rejected VALUES(?,?,?)',(snapshot_id,i,reason))
        db.execute('INSERT OR IGNORE INTO v2_normalization_runs VALUES(?,?,?,?,?,?)',(key,snapshot_id,parser_hash,utcnow(),len(good),len(bad)))
    return {'source':r['source'],'snapshot_id':snapshot_id,'raw_sha256':r['sha256'],'observed_at':r['observed_at'],'parser_sha256':parser_hash,'accepted':len(good),'rejected':len(bad),'network_requests':0}
