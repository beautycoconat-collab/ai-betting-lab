"""Restore shipped CC0 evidence offline and MERGE request counters, never reset them."""
import argparse,json,zlib
from pathlib import Path
from betting_lab.domain import digest

def merge_budget(db,root=None):
    path=(Path(root) if root else Path(__file__).resolve().parents[1])/'evidence/phase2/quota-state.json'
    if not path.exists():return
    seed=json.loads(path.read_text())
    with db:
        for r in seed['requests']:
            db.execute('INSERT INTO requests(source,at) SELECT ?,? WHERE NOT EXISTS(SELECT 1 FROM requests WHERE source=? AND at=?)',(r['source'],r['at'],r['source'],r['at']))
        for r in seed['cooldowns']:
            db.execute('INSERT INTO cooldowns(source,until_at) VALUES(?,?) ON CONFLICT(source) DO UPDATE SET until_at=max(until_at,excluded.until_at)',(r['source'],r['until_at']))

def restore(q,root=None):
    from .normalization import replay
    root=Path(root) if root else Path(__file__).resolve().parents[1]
    merge_budget(q.db,root);index=json.loads((root/'evidence/phase2/snapshot-index.json').read_text());out=[]
    for item in index:
        path=(root/item['file']).resolve()
        if not path.is_relative_to((root/'evidence/phase2/raw').resolve()):raise ValueError('invalid_evidence_path')
        body=path.read_bytes()
        if digest(body)!=item['sha256']:raise ValueError('evidence_hash_mismatch')
        sid=item['id'];kind=item.get('kind','collect');jid=q.enqueue(item['source'],kind,item['params'],item['observed_at'])
        with q.db:
            q.db.execute("UPDATE v2_jobs SET status='done',lease_token=NULL,lease_until=NULL WHERE id=? AND status='pending'",(jid,))
            q.db.execute('INSERT OR IGNORE INTO v2_snapshots VALUES(?,?,?,?,?,?,?,?)',(sid,jid,item['source'],item['url'],item['observed_at'],item['sha256'],zlib.compress(body),json.dumps(item['headers'])))
        if kind=='discover':
            from .adapters import ADAPTERS
            adapter=ADAPTERS[item['source']];catalog=adapter.catalog(adapter.decode(body,kind))
            with q.db:
                if not q.db.execute('SELECT 1 FROM v2_catalog WHERE snapshot_id=?',(sid,)).fetchone():q.db.execute('INSERT INTO v2_catalog VALUES(?,?,?)',(sid,item['source'],json.dumps(catalog)))
            out.append({'source':item['source'],'catalog_entries':len(catalog),'network_requests':0})
        else:out.append(replay(q,sid))
    return out

def main():
    from .queue import Queue
    p=argparse.ArgumentParser();p.add_argument('--db',default='data/lab.sqlite');a=p.parse_args();q=Queue(a.db)
    try:print(json.dumps(restore(q),indent=2))
    finally:q.close()
if __name__=='__main__':main()
