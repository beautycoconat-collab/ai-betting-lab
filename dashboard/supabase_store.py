"""Append-only binding to existing 001–005 tables. No DDL, grants or wallet SQL.

A plan is parameterized and can be dry-run/reviewed. The connection must already
have explicitly provisioned ingestion privileges. No role escalation is done.
"""
import json
from uuid import NAMESPACE_URL,uuid5
from betting_lab.domain import digest

PROJECT='oswpkwwbjwyktuqcakhr'

def uid(*parts):return str(uuid5(NAMESPACE_URL,'abl-dashboard:'+digest(parts)))

def plan(data):
    if data.get('execution_enabled') is not False or data.get('pilot_enabled') is not False:
        raise ValueError('execution_must_be_disabled')
    rows=[]
    def insert(table, body):
        if table not in {'sources','raw_snapshots','teams','matches','match_versions','model_versions','predictions','agent_runs','audit_events'}:
            raise ValueError('write_table_forbidden')
        columns=list(body)
        rows.append((f"INSERT INTO lab.{table} ({','.join(columns)}) VALUES ({','.join('%s::uuid[]' if k=='input_snapshot_ids' else '%s' for k in columns)}) ON CONFLICT DO NOTHING",list(body.values())))
    for f in data['fixtures']:
        if f.get('mode')!='verified_fixture' or f['source_id']!='openliga':raise ValueError('verified_real_source_required')
        from .daily import aware
        if aware(f['observed_at'])>aware(data['generated_at']):raise ValueError('future_snapshot')
        insert('sources',dict(id='openliga',status='approved',license_url='https://www.openligadb.de/lizenz',reviewed_at=f['observed_at'],review_expires='2026-11-13T00:00:00+00:00',request_policy=json.dumps({'internal_requests_per_day':4}),attribution=f['attribution']))
        sid=uid('snapshot',f['snapshot_id'])
        insert('raw_snapshots',dict(id=sid,source_id='openliga',request_url=f['source_url'],received_at=f['observed_at'],source_updated_at=None,content_sha256=f['snapshot_sha256'],payload=json.dumps({'artifact_path':'/data/openliga-2026-bl1.json','sha256':f['snapshot_sha256']}),data_kind='real'))
        home,away=uid('openliga',f['competition'],f['home']),uid('openliga',f['competition'],f['away'])
        for tid,name in ((home,f['home']),(away,f['away'])):insert('teams',dict(id=tid,name=name,country='DE',gender='men',squad_type='first'))
        insert('matches',dict(id=f['id'],competition=f['competition'],season=f['season'],home_id=home,away_id=away,kickoff_at=f['kickoff_at'],status='scheduled'))
        insert('match_versions',dict(id=uid('fixture-version',f['id'],f['snapshot_id']),match_id=f['id'],observed_at=f['observed_at'],snapshot_id=sid,kickoff_at=f['kickoff_at'],status='scheduled',home_goals=None,away_goals=None))
        for s in f.get('scenarios',[]):
            for name,m in s['models'].items():
                mid=uid('conditional-model',name,m['model_sha256'],s['neutral'])
                insert('model_versions',dict(id=mid,name=name+':conditional_venue',code_sha=data['engine_code_sha256'],parameters=json.dumps({'neutral_scenario':s['neutral'],'final_forecast':False,'model_state_sha256':m['model_sha256']}),trained_through=m['training_end']+'T23:59:59+00:00',role='challenger',dataset_hash=s['training_dataset_sha256']))
                grid=json.dumps({'representation':'top_scores_only','top_scores':m['top_scores'],'outside_display_grid_probability':m['outside_grid_probability'],'full_grid_included':False,'conditional_venue':s['neutral']})
                insert('predictions',dict(id=uid('prediction',s['id'],name),match_id=f['id'],model_id=mid,feature_cutoff=f['as_of'],kickoff_at=f['kickoff_at'],p_home=m['p_1x2'][0],p_draw=m['p_1x2'][1],p_away=m['p_1x2'][2],score_grid=grid,input_snapshot_ids=[sid]))
            for role in f['roles']:
                if role['status']=='done':insert('agent_runs',dict(id=uid('run',s['id'],role['id']),role_id=role['id'],fixture_id=f['id'],as_of=f['as_of'],mode='prematch'))
            summary={k:s[k] for k in ('id','neutral','models','markets','findings','reviews')}
            summary.update(schema_version='1.0',fixture_id=f['id'],as_of=f['as_of'],source_snapshot_id=sid,execution_enabled=False)
            body=json.dumps(summary,ensure_ascii=False,allow_nan=False)
            if len(body.encode())>14000:raise ValueError('audit_payload_budget')
            # Idempotency is guarded by a deterministic entity_id in a serialized transaction.
            rows.append(("INSERT INTO lab.audit_events(actor,event_type,entity_id,payload) SELECT %s,%s,%s,%s WHERE NOT EXISTS(SELECT 1 FROM lab.audit_events WHERE event_type=%s AND entity_id=%s)",['dashboard_worker','conditional_research_v1',s['id'],body,'conditional_research_v1',s['id']]))
    return rows


def persist(connection,data):
    with connection.transaction():
        connection.execute("SET LOCAL statement_timeout='15s'")
        connection.execute("SET LOCAL lock_timeout='3s'")
        # Serialize this bounded import; do not affect wallet/other project locks.
        connection.execute("SELECT pg_advisory_xact_lock(71603119)")
        source=connection.execute("SELECT status FROM lab.sources WHERE id='openliga'").fetchone()
        if source and source[0]!='approved':raise ValueError('hosted_source_not_approved')
        for sql,values in plan(data):connection.execute(sql,values)


def connect_and_persist(data,env=None):
    from cloudcheck.config import settings
    import os,psycopg
    env=os.environ if env is None else env
    if env.get('LAB_TEST_PROJECT_REF')!=PROJECT:raise ValueError('wrong_project')
    config=settings('hosted',env,require_auth=False)
    with psycopg.connect(**config) as conn:persist(conn,data)
