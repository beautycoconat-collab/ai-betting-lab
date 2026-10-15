"""Optional phase-1 snapshot import. Run migration first. No public schema writes.
Requires psycopg[binary]. DATABASE_URL is server-side only; sslmode=require is forced.
This imports raw/source observations, NOT auto-approved canonical matches or bets.
"""
import json
import os
from pathlib import Path
import sqlite3
import uuid
import zlib
import argparse

def main():
    import psycopg
    from psycopg.types.json import Jsonb
    p=argparse.ArgumentParser();p.add_argument('--db',default='data/lab.sqlite');a=p.parse_args()
    dsn=os.environ.get('DATABASE_URL')
    if not dsn:raise SystemExit('DATABASE_URL missing; do not paste it into chat or source files.')
    path=Path(a.db)
    if not path.is_file():raise SystemExit('Collector database missing')
    local=sqlite3.connect(f'file:{path.resolve()}?mode=ro',uri=True);local.row_factory=sqlite3.Row
    cfg=json.loads((Path(__file__).resolve().parents[1]/'config/sources.json').read_text())
    count=0
    # SSL errors stop execution. Do not retry with SSL disabled.
    with psycopg.connect(dsn,sslmode='require',connect_timeout=15) as conn:
      with conn.cursor() as cur:
        cur.execute('SELECT pg_database_size(current_database())')
        if cur.fetchone()[0]>350_000_000:raise SystemExit('Supabase storage safety threshold exceeded; import stopped')
        for source in ('openliga','openfootball'):
          c=cfg[source]
          cur.execute('''INSERT INTO lab.sources(id,status,license_url,reviewed_at,review_expires,request_policy,attribution)
            VALUES(%s,'approved',%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING''',
            (source,c['terms_url'],c['reviewed_at'],c['review_expires'],Jsonb(c),source+'; '+c['license']))
        for r in local.execute('SELECT s.*,b.body FROM snapshots s JOIN blobs b ON s.hash=b.hash'):
          sid=uuid.uuid5(uuid.NAMESPACE_URL,'ai-betting-lab:snapshot:'+r['id'])
          cur.execute('''INSERT INTO lab.raw_snapshots(id,source_id,request_url,received_at,content_sha256,payload,data_kind)
           VALUES(%s,%s,%s,%s,%s,%s,'real') ON CONFLICT(id) DO NOTHING''',
           (sid,r['source'],r['url'],r['observed_at'],r['hash'],Jsonb(json.loads(zlib.decompress(r['body'])))))
          for m in local.execute('SELECT * FROM observations WHERE snapshot_id=?',(r['id'],)):
            cur.execute('''INSERT INTO lab.source_observations(snapshot_id,source_match_id,observed_at,payload)
              VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id,source_match_id) DO NOTHING''',
              (sid,m['source_match_id'],m['observed_at'],Jsonb(json.loads(m['data']))))
          for q in local.execute('SELECT * FROM quarantine WHERE snapshot_id=?',(r['id'],)):
            cur.execute('''INSERT INTO lab.quarantine(snapshot_id,row_index,reason) VALUES(%s,%s,%s)
              ON CONFLICT(snapshot_id,row_index) DO NOTHING''',(sid,q['row_index'],q['reason']))
          count+=1
    local.close()
    print(json.dumps({'snapshots_processed':count,'destination':'lab schema','bets_created':0}))

if __name__=='__main__':
    try:main()
    except Exception as e:
        # Avoid printing DSN/passwords from driver errors.
        raise SystemExit('Import failed: '+type(e).__name__+'; transaction rolled back. Check server logs securely.')
