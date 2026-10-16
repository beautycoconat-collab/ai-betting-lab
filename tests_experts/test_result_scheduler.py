"""Offline integration tests: approved fake sources, never real provider acceptance."""
import json
import sqlite3
import unittest
from datetime import timedelta

from experts.result_scheduler import ResultScheduler
import tests_experts.test_outcome_journal as outcome_tests


class ResultSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = outcome_tests.ForwardOutcomeTests('test_verified_result_and_graded_prediction_with_audit')
        self.fixture.setUp()
        self.h = self.fixture
        self.h.locked()
        self.scheduler = ResultScheduler(self.h.r)

    def tearDown(self):
        self.fixture.tearDown()

    def plan(self, **kw):
        return self.scheduler.plan(self.h.fid, 'openfootball', self.h.source_params, self.h.nid, **kw)

    def run_queue(self, score=(2,1)):
        body=json.dumps({'matches':[{'date':self.h.kickoff.date().isoformat(),
            'team1':'Alpha','team2':'Beta','score':{'ft':list(score)} if score is not None else None}]}).encode()
        if score is None:
            body=json.dumps({'matches':[{'date':self.h.kickoff.date().isoformat(),
                'team1':'Alpha','team2':'Beta'}]}).encode()
        return self.h.r.queue.work_one(lambda u:(body,{}),clock=lambda:self.h.now.isoformat())

    def test_pre_due_is_queued_but_not_fetched(self):
        plan=self.plan()
        self.assertEqual(self.scheduler.reconcile(plan['plan_id'])['status'],'source_pending')
        self.assertIsNone(self.h.r.queue.work_one(lambda u:self.fail('premature_http'), clock=lambda:self.h.now.isoformat()))
        row=self.h.r.db.execute('SELECT not_before FROM v2_jobs WHERE id=?',(plan['source_job_id'],)).fetchone()
        self.assertEqual(row['not_before'],(self.h.kickoff+timedelta(hours=2)).isoformat())

    def test_real_queue_snapshot_to_journal_to_metrics(self):
        plan=self.plan()
        self.h.now=self.h.kickoff+timedelta(minutes=125)
        self.assertEqual(self.run_queue()['status'],'done')
        result=self.scheduler.reconcile(plan['plan_id'])
        self.assertEqual(result['status'],'graded')
        self.assertEqual(result['graded'],1)
        self.assertEqual(result['final']['home'],2)
        perf=self.scheduler.performance_windows()
        self.assertEqual(perf['windows']['7']['graded_predictions'],1)
        self.assertIsNone(perf['windows']['7']['roi'])
        self.assertTrue(self.h.r.verify_audit())
        self.assertEqual(self.scheduler.reconcile(plan['plan_id'])['status'],'graded')
        self.assertEqual(self.h.r.db.execute('SELECT COUNT(*) FROM lab_prediction_grades').fetchone()[0],1)

    def test_plan_is_idempotent_and_append_only(self):
        p=self.plan()
        self.assertEqual(self.plan()['plan_id'],p['plan_id'])
        self.assertEqual(self.h.r.db.execute('SELECT count(*) FROM lab_result_collection_plans').fetchone()[0],1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.h.r.db.execute("UPDATE lab_result_collection_plans SET native_id='tampered'")
        self.h.r.db.rollback()

    def test_no_locked_prediction_no_poll(self):
        self.h.r.db.execute('INSERT INTO f_fixtures VALUES(?,?,?,?,?)',
            ('00000000-0000-0000-0000-000000000999',self.h.kickoff.isoformat(),'regulation90','Gamma','Delta'))
        with self.assertRaisesRegex(ValueError,'pre_kickoff_locked_prediction_required'):
            self.scheduler.plan('00000000-0000-0000-0000-000000000999','openfootball',self.h.source_params,'native')

    def test_denies_unapproved_source(self):
        with self.assertRaisesRegex(ValueError,'result_source_policy_unapproved'):
            self.scheduler.plan(self.h.fid,'unknown-source',self.h.source_params,self.h.nid)
        self.h.r.queue.registry['openfootball']['status']='blocked'
        with self.assertRaisesRegex(ValueError,'result_source_policy_unapproved'):
            self.plan()

    def test_rejects_future_or_retroactive_cycle(self):
        with self.assertRaisesRegex(ValueError,'cycle_must_equal_current_day'):
            self.plan(cycle='2028-01-01')
        with self.assertRaisesRegex(ValueError,'invalid_result_wait'):
            self.plan(minimum_after_kickoff_minutes=25)

    def test_pending_final_and_next_cycle_retry(self):
        plan=self.plan()
        self.h.now=self.h.kickoff+timedelta(hours=3)
        self.assertEqual(self.run_queue(score=None)['status'],'done')
        self.assertEqual(self.scheduler.reconcile(plan['plan_id'])['status'],'waiting_for_final')
        self.h.now+=timedelta(days=1)
        newer=self.plan()
        self.assertNotEqual(newer['source_job_id'],plan['source_job_id'])
        self.assertEqual(self.run_queue(score=(1,0))['status'],'done')
        self.assertEqual(self.scheduler.reconcile(newer['plan_id'])['status'],'graded')

    def test_cached_old_result_cannot_claim_fresh_result(self):
        self.h.now=self.h.kickoff+timedelta(minutes=95)
        original=self.h.collect(score=(1,0))
        self.h.now=self.h.kickoff+timedelta(minutes=125)
        plan=self.plan()
        # Freshly scheduled job reuses a cached observation older than
        # the 120-minute conservative threshold.
        result=self.h.r.queue.work_one(lambda _:self.fail('should reuse cache'),
                                        clock=lambda:self.h.now.isoformat())
        self.assertEqual(result['status'],'cached')
        self.assertEqual(original,result['snapshot_id'])
        self.assertEqual(self.scheduler.reconcile(plan['plan_id'])['status'],
                         'stale_snapshot_repoll_next_cycle')

    def test_score_correction_cannot_overwrite_graded_result(self):
        first=self.plan()
        self.h.now=self.h.kickoff+timedelta(hours=3)
        self.assertEqual(self.run_queue(score=(2,1))['status'],'done')
        self.assertEqual(self.scheduler.reconcile(first['plan_id'])['status'],'graded')
        self.h.now+=timedelta(days=1)
        second=self.plan()
        self.assertEqual(self.run_queue(score=(0,1))['status'],'done')
        self.assertEqual(self.scheduler.reconcile(second['plan_id'])['status'],'manual_review_required')
        self.assertEqual(json.loads(self.h.r.db.execute('SELECT result_body FROM lab_verified_results').fetchone()[0])['home'],2)

    def test_rejects_wrong_fixture_and_native_id(self):
        self.h.now=self.h.kickoff+timedelta(hours=3)
        plan=self.scheduler.plan(self.h.fid,'openfootball',self.h.source_params,'not-real')
        self.assertEqual(self.run_queue()['status'],'done')
        self.assertEqual(self.scheduler.reconcile(plan['plan_id'])['status'],'waiting_for_final')
        self.assertEqual(self.h.r.db.execute('SELECT COUNT(*) FROM lab_verified_results').fetchone()[0],0)

    def test_rejects_unserializable_params(self):
        with self.assertRaisesRegex(ValueError,'invalid_source_params'):
            self.scheduler.plan(self.h.fid,'openfootball',{'not_valid':object()},self.h.nid)

    def test_no_metric_invention_without_final(self):
        self.assertEqual(self.scheduler.performance_windows()['windows']['7']['pending_predictions'],1)
        self.assertIsNone(self.scheduler.performance_windows()['windows']['7']['brier'])
        self.assertIsNone(self.scheduler.performance_windows()['windows']['7']['log_loss'])


if __name__ == '__main__':
    unittest.main()
