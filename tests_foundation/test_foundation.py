"""Synthetic contract, safety and real simultaneous SQLite connection tests."""
import unittest,tempfile,json,sqlite3
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import datetime,timedelta
from pydantic import ValidationError
from foundation.contracts import AgentMessage,Evidence,JobRequest,Role,normalized_status,UnsupportedMarket
from foundation.runtime import Runtime
from foundation.demo import setup,message,NOW,POLICY,run_demo
from foundation.roles import registry
from engine.models import ConstantPoisson

class Foundation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'db.sqlite';self.now=NOW
        self.rt=Runtime(self.path,clock=lambda:self.now,registry=POLICY)
        self.fid,self.eid,self.sid=setup(self.rt)
        self.red=self.rt.start_run('red_team',self.fid);self.ref=self.rt.start_run('scientific_referee',self.fid)
        self.msg=message(self.fid,self.eid,self.sid,self.red)
    def tearDown(self):self.rt.close();self.temp.cleanup()
    def task(self,key='job-00001',**kwargs):return dict(schema_version='1.0',idempotency_key=key,kind='validate',fixture_id=self.fid,**kwargs)
    def test_valid_message(self):self.assertEqual(self.rt.message(self.msg),self.msg['message_id'])
    def test_missing_required_field(self):
        del self.msg['evidence_ids']
        with self.assertRaises(ValidationError):self.rt.message(self.msg)
    def test_unknown_schema(self):
        self.msg['schema_version']='2.0'
        with self.assertRaises(ValidationError):self.rt.message(self.msg)
    def test_numeric_override_rejected(self):
        self.msg['numeric_override']=.49
        with self.assertRaises(ValidationError):self.rt.message(self.msg)
    def test_extra_llm_probability_field_rejected(self):
        self.msg['probability']=.49
        with self.assertRaises(ValidationError):self.rt.message(self.msg)
    def test_missing_evidence(self):
        self.msg['evidence_ids']=[str(uuid4())]
        with self.assertRaisesRegex(ValueError,'evidence'):self.rt.message(self.msg)
    def test_missing_model_version(self):
        self.msg['model_version_id']=str(uuid4())
        with self.assertRaisesRegex(ValueError,'unknown_model_version'):self.rt.message(self.msg)
    def test_local_storage_limit(self):
        self.rt.max_db_bytes=1
        with self.assertRaisesRegex(ValueError,'storage_budget'):self.rt.message(self.msg)
    def test_duplicate_message_idempotent(self):
        self.rt.message(self.msg);self.rt.message(self.msg);self.assertEqual(self.rt.db.execute('SELECT count(*) FROM f_messages').fetchone()[0],1)
    def test_idempotency_conflict(self):
        self.rt.message(self.msg);self.msg['severity']='low'
        with self.assertRaisesRegex(ValueError,'idempotency_conflict'):self.rt.message(self.msg)
    def test_forged_agent_role(self):
        self.msg['agent_role']='score_engine'
        with self.assertRaisesRegex(ValueError,'role_or_fixture'):self.rt.message(self.msg)
    def test_wrong_fixture_evidence(self):
        other=str(uuid4());self.rt.fixture(other,'2026-10-16T18:00:00+00:00','regulation90','C','D');run=self.rt.start_run('red_team',other)
        self.msg.update(fixture_id=other,agent_run_id=run)
        with self.assertRaisesRegex(ValueError,'wrong_fixture'):self.rt.message(self.msg)
    def test_two_rounds_then_abstain_skip(self):
        fid=self.rt.message(self.msg);a=self.rt.review(fid,self.ref,'review-1');b=self.rt.review(fid,self.ref,'review-2')
        self.assertEqual(a['status'],'needs_reanalysis');self.assertEqual(b['status'],'abstain');self.assertEqual(b['risk_action'],'skip')
        with self.assertRaisesRegex(ValueError,'review_limit'):self.rt.review(fid,self.ref,'review-3')
    def test_review_retry_not_extra_round(self):
        fid=self.rt.message(self.msg);a=self.rt.review(fid,self.ref,'review-1');b=self.rt.review(fid,self.ref,'review-1');self.assertEqual(a,b)
    def test_red_team_cannot_referee(self):
        fid=self.rt.message(self.msg)
        with self.assertRaisesRegex(ValueError,'referee_permission'):self.rt.review(fid,self.red,'bad-review')
    def test_missing_resolution_evidence(self):
        fid=self.rt.message(self.msg)
        with self.assertRaisesRegex(ValueError,'evidence_missing'):self.rt.review(fid,self.ref,'review-1',resolution_evidence_ids=[str(uuid4())])
    def test_unknown_and_conflicting_stored(self):
        e=json.loads(self.rt.db.execute('SELECT body FROM f_evidence').fetchone()[0]);e['evidence_id']=str(uuid4());e['quality']='conflicting';self.rt.add_evidence(e)
        self.assertEqual(self.rt.db.execute('SELECT count(*) FROM f_evidence').fetchone()[0],2)
    def test_evidence_target_mismatch(self):
        e=json.loads(self.rt.db.execute('SELECT body FROM f_evidence').fetchone()[0]);e.update(evidence_id=str(uuid4()),score_target='final_including_extra_time')
        with self.assertRaisesRegex(ValueError,'target_mismatch'):self.rt.add_evidence(e)
    def test_future_snapshot_feature_blocked(self):
        self.msg['created_at']='2027-01-01T00:00:00+00:00'
        with self.assertRaisesRegex(ValueError,'time_mismatch'):self.rt.message(self.msg)
    def test_audit_chain(self):self.rt.message(self.msg);self.assertTrue(self.rt.verify_audit())
    def test_audit_append_only(self):
        with self.assertRaises(sqlite3.IntegrityError):self.rt.db.execute('DELETE FROM f_audit')
        self.rt.db.rollback()
    def test_registry_fourteen_roles(self):self.assertEqual(len(registry()),14);self.assertTrue(all(not r['llm_required'] for r in registry()))
    def test_source_status_mapping(self):self.assertEqual(normalized_status('pending_key'),'pending_review');self.assertEqual(normalized_status('nonsense'),'disabled')
    def test_unsupported_market_has_no_number(self):
        with self.assertRaises(ValidationError):UnsupportedMarket(schema_version='1.0',market='first_half_btts',status='unsupported',probability=.5,reason='no halftime data')
    def test_source_quota_uses_original_ledger(self):
        self.rt.queue.enqueue('openfootball','collect',{'league':'de.1','season':'2023-24'},NOW)
        result=self.rt.queue.work_one(lambda _:self.fail('HTTP forbidden by quota'),lambda:NOW)
        self.assertEqual(result['reason'],'minimum_interval')
    def test_job_retry_same_key(self):self.assertEqual(self.rt.enqueue(self.task()),self.rt.enqueue(self.task()))
    def test_job_conflicting_key(self):
        self.rt.enqueue(self.task())
        with self.assertRaises(ValueError):self.rt.enqueue(dict(self.task(),kind='model'))
    def test_dependency_waits(self):
        parent=self.rt.enqueue(self.task());child=self.rt.enqueue(self.task('job-00002'),[parent]);j=self.rt.claim('worker','data_validator');self.assertEqual(j['id'],parent);self.assertIsNone(self.rt.claim('other','data_validator'))
        self.rt.finish(parent,j['lease_token'],'worker');self.assertEqual(self.rt.claim('other','data_validator')['id'],child)
    def test_wrong_role_cannot_claim(self):self.rt.enqueue(self.task());self.assertIsNone(self.rt.claim('red-worker','red_team'))
    def test_two_concurrent_workers_one_claim(self):
        self.rt.enqueue(self.task());barrier=Barrier(2)
        def claim(i):
            r=Runtime(self.path,clock=lambda:NOW,registry=POLICY)
            try:barrier.wait();return r.claim(str(i),'data_validator')
            finally:r.close()
        with ThreadPoolExecutor(2) as ex:out=list(ex.map(claim,range(2)))
        self.assertEqual(sum(x is not None for x in out),1)
    def test_expired_lease_and_stale_completion(self):
        self.rt.enqueue(self.task(timeout_seconds=1));old=self.rt.claim('first','data_validator');self.now='2026-10-15T00:00:02+00:00';new=self.rt.claim('second','data_validator')
        self.assertNotEqual(old['lease_token'],new['lease_token']);self.assertFalse(self.rt.finish(old['id'],old['lease_token'],'first'));self.assertTrue(self.rt.finish(new['id'],new['lease_token'],'second'))
    def test_max_attempts_dead_letter(self):
        self.rt.enqueue(self.task(max_attempts=1));j=self.rt.claim('worker','data_validator');self.rt.finish(j['id'],j['lease_token'],'worker',error='schema_invalid');self.assertEqual(self.rt.db.execute('SELECT status FROM f_tasks').fetchone()[0],'failed')
    def test_failed_parent_blocks_child(self):
        parent=self.rt.enqueue(self.task(max_attempts=1));self.rt.enqueue(self.task('job-child'),[parent]);j=self.rt.claim('w','data_validator');self.rt.finish(j['id'],j['lease_token'],'w',error='bad');self.assertIsNone(self.rt.claim('w','data_validator'));self.assertEqual(self.rt.db.execute("SELECT count(*) FROM f_tasks WHERE status='blocked'").fetchone()[0],1)
    def test_prediction_revisions_append_only(self):
        e=json.loads(self.rt.db.execute('SELECT body FROM f_evidence').fetchone()[0]);e.update(evidence_id=str(uuid4()),quality='verified');eid=self.rt.add_evidence(e)
        model=ConstantPoisson().fit([dict(id='train',date='2020-01-01',home='A',away='B',home_goals=1,away_goals=0,neutral=False,target='regulation90')])
        fixture=dict(id=self.fid,date='2026-10-16',home='SYNTHETIC A',away='SYNTHETIC B',neutral=False,target='regulation90');run=self.rt.start_run('score_engine',self.fid)
        a=self.rt.predict(run,model,fixture,evidence_ids=[eid]);b=self.rt.predict(run,model,fixture,evidence_ids=[eid]);self.assertNotEqual(a,b)
        with self.assertRaises(sqlite3.IntegrityError):self.rt.db.execute("UPDATE f_prediction_revisions SET revision=8")
        self.rt.db.rollback();self.assertEqual(self.rt.db.execute('SELECT count(*) FROM f_prediction_revisions').fetchone()[0],2)
        with self.assertRaisesRegex(ValueError,'permission'):self.rt.predict(self.red,model,fixture,evidence_ids=[eid])
        with self.assertRaisesRegex(ValueError,'fixture'):self.rt.predict(run,model,dict(fixture,home='WRONG'),evidence_ids=[eid])

if __name__=='__main__':unittest.main()
