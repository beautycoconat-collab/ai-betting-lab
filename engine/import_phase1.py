"""Reuse Phase 1 raw snapshots without requests, altered clocks or reset budgets."""
import argparse,json,re,zlib
from .queue import Queue
from .normalization import replay
from betting_lab.domain import digest

def run(q):
    results=[]
    for r in q.db.execute('SELECT s.*,b.body FROM snapshots s JOIN blobs b ON b.hash=s.hash ORDER BY observed_at').fetchall():
        if r['source']=='openfootball':
            m=re.search(r'/master/(20\d{2}-\d{2})/([a-z]{2,3}\.\d+)\.json$',r['url'])
            if not m:continue
            params={'season':m[1],'league':m[2]}
        elif r['source']=='openliga':
            m=re.search(r'/getmatchdata/([^/]+)/(\d{4})$',r['url'])
            if not m:continue
            params={'league':m[1],'season':m[2]}
        else:continue
        if digest(zlib.decompress(r['body']))!=r['hash']:raise ValueError('phase1_raw_hash_mismatch')
        jid=q.enqueue(r['source'],'collect',params,r['observed_at'])
        with q.db:
            q.db.execute("UPDATE v2_jobs SET status='done',lease_token=NULL,lease_until=NULL WHERE id=? AND status='pending'",(jid,))
            q.db.execute('INSERT OR IGNORE INTO v2_snapshots VALUES(?,?,?,?,?,?,?,?)',(r['id'],jid,r['source'],r['url'],r['observed_at'],r['hash'],r['body'],r['headers']))
        results.append(replay(q,r['id']))
    return results

def main():
    p=argparse.ArgumentParser();p.add_argument('--db',default='data/lab.sqlite');a=p.parse_args();q=Queue(a.db)
    try:print(json.dumps(run(q),indent=2))
    finally:q.close()
if __name__=='__main__':main()
