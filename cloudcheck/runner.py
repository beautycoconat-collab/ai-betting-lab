"""Empty-project migration and security probes. Reports never include secrets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError
from uuid import uuid4
from .config import settings,ConfigError
from .capacity import collect,decision

ROOT=Path(__file__).resolve().parents[1]

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def http(url,headers,method='GET',body=None):
    request=Request(url,headers=headers,method=method,data=None if body is None else json.dumps(body).encode())
    try:
        with build_opener(NoRedirect).open(request,timeout=15) as response:
            return response.status,json.loads(response.read(65536))
    except HTTPError as error:
        try: payload=json.loads(error.read(65536))
        except Exception: payload={}
        return error.code,payload

def hosted_auth():
    base='https://'+os.environ['LAB_TEST_PROJECT_REF']+'.supabase.co'
    headers={'apikey':os.environ['LAB_SUPABASE_ANON_KEY'],'Authorization':'Bearer '+os.environ['LAB_AUTH_JWT']}
    status,user=http(base+'/auth/v1/user',headers)
    if status!=200 or not user.get('id'): raise AssertionError('valid_test_user_required')
    # Positive Auth check prevents expired/invalid JWT from masquerading as RLS denial.
    anon={'apikey':os.environ['LAB_SUPABASE_ANON_KEY']}
    status,_=http(base+'/auth/v1/settings',anon)
    if status!=200: raise AssertionError('valid_anon_key_required')
    count=0
    for identity in (anon,headers):
        h={**identity,'Content-Profile':'lab','Content-Type':'application/json'}
        for table,column,value in [('predictions','p_home',0.9),('review_decisions','status','approved'),('paper_wallet','balance_kurus',999999)]:
            status,payload=http(base+'/rest/v1/'+table+'?id=eq.'+('1' if table=='paper_wallet' else str(uuid4())),h,'PATCH',{column:value})
            # lab is intentionally not exposed: PGRST106 is an API boundary, not an RLS proof.
            if status not in (403,406) or payload.get('code') not in ('PGRST106','42501'):
                raise AssertionError('api_write_denial_not_proven')
            count+=1
    return count

def security(db,mode):
    from psycopg import sql
    checks=0
    def check(value):
        nonlocal checks
        if not value: raise AssertionError('security_assertion_failed')
        checks+=1
    check(db.execute("select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='lab' and c.relkind='r' and not c.relrowsecurity").fetchone()[0]==0)
    check(db.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='lab' and p.prosecdef and not ('search_path=pg_catalog, lab, pg_temp'=any(coalesce(p.proconfig,'{}')))").fetchone()[0]==0)
    roles=[r[0] for r in db.execute('select id from lab.agent_roles')]
    for role in roles:
        name='lab_'+role
        attributes=db.execute('select rolcanlogin,rolsuper,rolcreaterole,rolcreatedb,rolbypassrls from pg_roles where rolname=%s',(name,)).fetchone()
        check(attributes is not None and not any(attributes))
        for table in ('predictions','prediction_runs','review_decisions','paper_wallet','wallet_ledger'):
            check(not db.execute('select has_table_privilege(%s,%s,\'INSERT,UPDATE,DELETE\')',(name,'lab.'+table)).fetchone()[0])
    for name in ('anon','authenticated'):
        if not db.execute('select 1 from pg_roles where rolname=%s',(name,)).fetchone():
            if mode=='hosted': raise AssertionError('hosted_auth_role_missing')
            db.execute(sql.SQL('create role {} nologin').format(sql.Identifier(name)))
        db.execute(sql.SQL('set role {}').format(sql.Identifier(name)))
        try:
            for command in ('update lab.paper_wallet set balance_kurus=1','delete from lab.predictions','delete from lab.review_decisions',"select lab.post_agent_message('{}')"):
                try: db.execute(command)
                except Exception as error:
                    check(getattr(error,'sqlstate',None)=='42501')
                else: raise AssertionError('unauthorized_operation_allowed')
        finally: db.execute('reset role')
    # Test RLS separately from schema/table ACLs, with a temporary transactional role grant.
    # Everything rolls back; no persistent privilege is broadened.
    with db.transaction():
        db.execute('grant usage on schema lab to authenticated')
        db.execute('grant select,update on lab.paper_wallet to authenticated')
        db.execute('set local role authenticated')
        check(db.execute('select count(*) from lab.paper_wallet').fetchone()[0]==0)
        check(db.execute('update lab.paper_wallet set balance_kurus=1 returning id').fetchall()==[])
        db.execute('reset role')
        # Explicit rollback via psycopg Rollback avoids retaining the temporary grants.
        from psycopg import Rollback
        raise Rollback()
    db.execute('set role lab_red_team')
    try:
        try:db.execute("select lab.record_prediction(gen_random_uuid(),gen_random_uuid(),gen_random_uuid(),gen_random_uuid(),'{}')")
        except Exception as error:check(getattr(error,'sqlstate',None)=='42501')
        else:raise AssertionError('red_team_override_allowed')
        try:db.execute("select lab.start_agent_run('score_engine',gen_random_uuid(),now(),'prematch')")
        except Exception as error:check('agent_permission_denied' in str(error))
        else:raise AssertionError('role_spoof_allowed')
    finally:db.execute('reset role')
    check(db.execute('select balance_kurus=100000 and not betting_enabled and pilot_start is null from lab.paper_wallet').fetchone()[0])
    return checks

def concurrent_claim(connect,db):
    db.execute('set role lab_coordinator')
    db.execute("select lab.enqueue_workflow('cloudcheck-concurrent','validate',null)")
    db.execute('reset role')
    barrier=Barrier(2)
    def worker(i):
        with connect() as connection:
            connection.execute('set role lab_data_validator');barrier.wait(timeout=20)
            return connection.execute("select id from lab.claim_workflow('data_validator',%s)",(str(i),)).fetchall()
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(worker,range(2)))
    if sum(map(len,results))!=1:raise AssertionError('duplicate_or_missing_claim')

def concurrent_budget(connect,db):
    # Isolated trigger test, NOT a pilot or a wager-placement RPC. All data synthetic.
    # Wallet stays disabled and balance remains 1000 TRY throughout.
    db.execute("insert into lab.sources(id,status,license_url) values('cloudcheck-synthetic','pending','https://example.invalid')")
    raw=db.execute("insert into lab.raw_snapshots(source_id,request_url,content_sha256,payload,data_kind) values('cloudcheck-synthetic','https://example.invalid',repeat('a',64),'{}','synthetic') returning id").fetchone()[0]
    home=db.execute("insert into lab.teams(name) values('SYNTHETIC cloud A') returning id").fetchone()[0]
    away=db.execute("insert into lab.teams(name) values('SYNTHETIC cloud B') returning id").fetchone()[0]
    model=db.execute("insert into lab.model_versions(name,code_sha,parameters,trained_through,role,dataset_hash) values('SYNTHETIC','test','{}',now()-interval '2 days','candidate','test') returning id").fetchone()[0]
    rows=[]
    for i in range(12):
        fixture=db.execute("insert into lab.matches(competition,season,home_id,away_id,kickoff_at,status) values('SYNTHETIC','TEST',%s,%s,now()+interval '1 day','scheduled') returning id",(home,away)).fetchone()[0]
        prediction=db.execute("insert into lab.predictions(match_id,model_id,feature_cutoff,kickoff_at,p_home,p_draw,p_away,score_grid,input_snapshot_ids) values(%s,%s,now()-interval '1 hour',now()+interval '1 day',.5,.3,.2,'{}',%s) returning id",(fixture,model,[raw])).fetchone()[0]
        odds=db.execute("insert into lab.odds_snapshots(match_id,source_id,bookmaker,market,outcome,decimal_odds,source_updated_at,raw_snapshot_id) values(%s,'cloudcheck-synthetic','SYNTHETIC','1X2','H',2,now(),%s) returning id",(fixture,raw)).fetchone()[0]
        rows.append((fixture,prediction,odds))
    barrier=Barrier(12)
    def worker(i):
        with connect() as connection:
            barrier.wait(timeout=20)
            fixture,prediction,odds=rows[i]
            try:
                connection.execute("insert into lab.paper_bets(idempotency_key,prediction_id,odds_id,match_id,stake_kurus,locked_odds,outcome,budget_day) values(%s,%s,%s,%s,1000,2,'H',(clock_timestamp() at time zone 'Europe/Istanbul')::date)",('cloudcheck-'+str(i),prediction,odds,fixture))
                return 'accepted'
            except Exception as error:
                if 'daily_limit' not in str(error):raise
                return 'limited'
    with ThreadPoolExecutor(12) as pool:results=list(pool.map(worker,range(12)))
    if results.count('accepted')!=10 or results.count('limited')!=2:raise AssertionError('daily_cap_failed')
    if db.execute('select sum(stake_kurus) from lab.paper_bets').fetchone()[0]!=10000:raise AssertionError('daily_sum_failed')
    if not db.execute('select balance_kurus=100000 and not betting_enabled and pilot_start is null from lab.paper_wallet').fetchone()[0]:raise AssertionError('pilot_or_wallet_changed')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['native','hosted'],required=True)
    parser.add_argument('--out',required=True);args=parser.parse_args()
    report={'environment':args.mode,'status':'blocked','migrations':[], 'pilot_started':False}
    code=2
    try:
        params=settings(args.mode)
        import psycopg
        connect=lambda:psycopg.connect(**params,autocommit=True)
        with connect() as db:
            # Exclusive session guard, empty application schemas only, never DROP/reset.
            if not db.execute('select pg_try_advisory_lock(42601015)').fetchone()[0]:raise ConfigError('test_project_busy')
            if db.execute("select 1 from pg_namespace where nspname='lab'").fetchone():raise ConfigError('requires_empty_lab_schema')
            if db.execute("select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind in ('r','p') limit 1").fetchone():raise ConfigError('public_application_tables_present')
            if args.mode=='hosted' and not db.execute("select to_regclass('auth.users')").fetchone()[0]:raise ConfigError('not_hosted_supabase')
            for migration in sorted((ROOT/'supabase/migrations').glob('*.sql')):
                db.execute(migration.read_text())
                report['migrations'].append({'name':migration.name,'sha256':hashlib.sha256(migration.read_bytes()).hexdigest(),'status':'passed'})
            report['stage']='sql_security'
            report['sql_security_checks']=security(db,args.mode)
            report['stage']='concurrent_claim'
            concurrent_claim(connect,db);report['concurrent_claim']='passed'
            report['stage']='concurrent_budget'
            concurrent_budget(connect,db);report['concurrent_budget_trigger']='passed'
            report['stage']='capacity'
            report['capacity_measurement']=collect(db)
            report['collection_gate']=decision(report['capacity_measurement'])
            if args.mode=='hosted': report['auth_api_write_denials']=hosted_auth()
            report['status']='passed';report['stage']='finished';code=0
    except ConfigError as error:
        report['reason']=str(error)
    except Exception as error:
        # Do not serialize exceptions: DB errors can contain DSNs, claims or SQL values.
        report['status']='failed';report['reason']='validation_failed';report['error_type']=type(error).__name__;report['sqlstate']=getattr(error,'sqlstate',None);code=1
    finally:
        output=Path(args.out);output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2));print(json.dumps({'environment':args.mode,'status':report['status']}))
    return code

if __name__=='__main__':raise SystemExit(main())
