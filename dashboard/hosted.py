"""Optional server-side, read-only Supabase reconciliation of the public feed.
No browser key, Data API grant or wallet read. Only matching real source fixtures
and our typed conditional-research records are eligible. Unknown DB rows are not
promoted into the public feed. This does not constitute Auth/JWT/RLS acceptance.
"""
import json
from .contracts import ModelSummary
from .supabase_store import PROJECT


def reconcile(connection, seed):
    output=dict(seed);fixtures=[]
    with connection.transaction():
        connection.execute('SET TRANSACTION READ ONLY')
        connection.execute("SET LOCAL statement_timeout='5s'")
        records=connection.execute('''SELECT m.id::text,h.name home,a.name away,v.kickoff_at,
              s.content_sha256,s.received_at FROM lab.matches m
            JOIN lab.teams h ON h.id=m.home_id JOIN lab.teams a ON a.id=m.away_id
            JOIN LATERAL (SELECT * FROM lab.match_versions mv WHERE mv.match_id=m.id
                ORDER BY mv.observed_at DESC,mv.id DESC LIMIT 1) v ON true
            JOIN lab.raw_snapshots s ON s.id=v.snapshot_id
            JOIN lab.sources src ON src.id=s.source_id
            WHERE s.source_id='openliga' AND s.data_kind='real' AND src.status='approved'
            AND v.status='scheduled' AND v.kickoff_at>clock_timestamp()
            AND s.received_at BETWEEN clock_timestamp()-interval '24 hours' AND clock_timestamp()
            ORDER BY v.kickoff_at LIMIT 100''').fetchall()
        by_id={f['id']:f for f in seed['fixtures']}
        for r in records:
            # Row tuple order is fixed by the query, independent of cursor factory.
            fid,home,away,kickoff,sha,observed=r
            f=by_id.get(fid)
            if not f or (home,away,sha)!=(f['home'],f['away'],f['snapshot_sha256']) or kickoff.isoformat()!=f['kickoff_at']:
                continue
            stored=connection.execute("SELECT payload FROM lab.audit_events WHERE event_type='conditional_research_v1' AND payload->>'fixture_id'=%s ORDER BY id DESC LIMIT 20",(fid,)).fetchall()
            ids={}
            for row in stored:
                p=row[0] if isinstance(row[0],dict) else json.loads(row[0])
                if p.get('schema_version')!='1.0' or p.get('execution_enabled') is not False:continue
                for m in p.get('models',{}).values():ModelSummary.model_validate(m)
                ids[p['id']]=p
            clean=dict(f)
            clean['scenarios']=[s for s in f.get('scenarios',[]) if s['id'] in ids
                and s['models']==ids[s['id']]['models'] and s['reviews']==ids[s['id']]['reviews']]
            if f.get('scenarios') and not clean['scenarios']:
                clean.update(prediction_status='insufficient_data',prediction_reason='cloud_prediction_not_verified')
            fixtures.append(clean)
    output.update(fixtures=fixtures,connection='hosted_readonly_reconciled')
    return output


def load(seed,env=None):
    import os,psycopg
    from cloudcheck.config import settings
    env=os.environ if env is None else env
    if env.get('LAB_TEST_PROJECT_REF')!=PROJECT:raise ValueError('wrong_project')
    config=settings('hosted',env,require_auth=False)
    with psycopg.connect(**config) as connection:return reconcile(connection,seed)
