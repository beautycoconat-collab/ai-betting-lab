"""Explicit SYNTHETIC, offline protocol demo. No real news, odds or bets."""
import argparse,json
from pathlib import Path
from uuid import uuid4
from .runtime import Runtime

NOW='2026-10-15T00:00:00+00:00'
POLICY={'openfootball':{'status':'approved','review_expires':'2026-11-13','requests_per_24h':4,'requests_per_31d':124,'min_interval_seconds':3600}}

def setup(runtime):
    fid=str(uuid4());runtime.fixture(fid,'2026-10-16T18:00:00+00:00','regulation90','SYNTHETIC A','SYNTHETIC B')
    runtime.queue.enqueue('openfootball','collect',{'league':'de.1','season':'2024-25'},NOW)
    payload=json.dumps({'matches':[{'date':'2024-08-01','team1':'SYNTHETIC A','team2':'SYNTHETIC B','score':{'ft':[1,0]}}]}).encode()
    runtime.queue.work_one(lambda _: (payload,{'data-kind':'synthetic'}),lambda:NOW)
    snapshot=runtime.db.execute('SELECT * FROM v2_snapshots LIMIT 1').fetchone()
    eid=str(uuid4());runtime.add_evidence(dict(schema_version='1.0',evidence_id=eid,fixture_id=fid,snapshot_id=snapshot['id'],source_id='openfootball',source_url=snapshot['url'],observed_at=NOW,published_at=None,quality='unknown',score_target='regulation90',claim='SYNTHETIC: lineup evidence unavailable; not a real injury claim'))
    return fid,eid,snapshot['id']

def message(fid,eid,sid,run):
    return dict(schema_version='1.0',message_id=str(uuid4()),agent_run_id=run,fixture_id=fid,agent_role='red_team',created_at=NOW,input_snapshot_ids=[sid],evidence_ids=[eid],model_version_id=None,issue_type='lineup_uncertainty',severity='critical',requested_action='scenario_analysis',status='pending_review',numeric_override=None,note='SYNTHETIC protocol example')

def run_demo(path):
    rt=Runtime(path,clock=lambda:NOW,registry=POLICY)
    try:
        fid,eid,sid=setup(rt);red=rt.start_run('red_team',fid);referee=rt.start_run('scientific_referee',fid)
        msg=message(fid,eid,sid,red);finding=rt.message(msg)
        first=rt.review(finding,referee,'demo-review-1-'+fid);second=rt.review(finding,referee,'demo-review-2-'+fid)
        job=rt.enqueue(dict(schema_version='1.0',idempotency_key='demo-reanalysis-'+fid,kind='reanalysis',fixture_id=fid))
        claimed=rt.claim('offline-worker','score_engine');rt.finish(claimed['id'],claimed['lease_token'],'offline-worker',error='scenario_model_not_implemented')
        return {'data_kind':'synthetic','message':msg,'decisions':[first,second],'job_id':job,'audit_chain_valid':rt.verify_audit(),'final_risk_action':second['risk_action'],'probabilities_modified':False,'network_requests':0}
    finally:rt.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--db',default='data/foundation-demo.sqlite');p.add_argument('--out',default='reports/phase0/demo.json');a=p.parse_args()
    result=run_demo(a.db);Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
