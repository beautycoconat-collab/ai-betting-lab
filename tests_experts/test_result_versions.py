"""Synthetic provider correction evidence; no real forward prediction claim."""
import json
import sqlite3
import unittest
from datetime import timedelta
from experts.result_versions import VersionedResults
from experts.result_scheduler import ResultScheduler
import tests_experts.test_outcome_journal as outcome_tests


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.h = outcome_tests.ForwardOutcomeTests('test_verified_result_and_graded_prediction_with_audit')
        self.h.setUp()
        self.h.locked()
        self.v = VersionedResults(self.h.r)
        self.scheduler = ResultScheduler(self.h.r)

    def tearDown(self):
        self.h.tearDown()

    def observe(self, score):
        h = self.h
        h.now = max(h.now,h.kickoff+timedelta(hours=3))
        h.r.queue.enqueue('openfootball','collect',h.source_params,h.now.isoformat(),cycle=h.now.date().isoformat())
        raw = json.dumps({'matches':[{'date':h.kickoff.date().isoformat(),'team1':'Alpha','team2':'Beta','score':{'ft':list(score)}}]}).encode()
        response = h.r.queue.work_one(lambda url:(raw,{}), clock=lambda:h.now.isoformat())
        self.assertEqual(response['status'],'done')
        return self.v.observe(h.fid,response['snapshot_id'],h.nid), response['snapshot_id']

    def correction(self):
        first,_ = self.observe((2,1))
        self.v.grade(self.h.pid)
        self.h.now += timedelta(days=1)
        second,sid = self.observe((0,1))
        return first,second,sid

    def request(self, version, sid, **overrides):
        h = self.h
        run = h.r.start_run('scientific_referee',h.fid,mode='retrospective')
        return dict(schema_version='1.0',version_id=version['version_id'],reviewer_run_id=run,
            idempotency_key='correction-review-1',decision='approved',
            reason='Provider corrected the persisted final score.',evidence_snapshot_ids=[sid]) | overrides

    def test_correction_is_quarantined_then_regraded_append_only(self):
        first,second,sid = self.correction()
        self.assertEqual(second['status'],'conflicting')
        self.assertEqual(self.v.current(self.h.fid)['id'],first['version_id'])
        request = self.request(second,sid)
        self.assertEqual(self.v.review(request),'approved')
        self.assertEqual(self.v.review(request),'approved')
        grade = self.v.grade(self.h.pid)
        self.assertEqual(grade['result_version_id'],second['version_id'])
        self.assertEqual(self.v.grade(self.h.pid),grade)
        self.assertEqual(self.h.r.db.execute('SELECT count(*) FROM lab_prediction_grade_versions').fetchone()[0],2)
        self.assertTrue(self.h.r.verify_audit())
        perf=self.v.performance(7)
        self.assertEqual(perf['graded_predictions'],1)
        self.assertAlmostEqual(perf['log_loss'],-__import__('math').log(.2))
        self.assertEqual(sum(b['count'] for b in perf['calibration']),3)
        self.assertIsNone(perf['roi'])
        self.assertIsNone(perf['coverage'])
        # The public scheduler/CLI report must use the reviewed revision too.
        self.assertAlmostEqual(self.scheduler.performance_windows()['windows']['7']['log_loss'],perf['log_loss'])

    def test_same_snapshot_idempotent(self):
        first,sid = self.observe((2,1))
        self.assertEqual(self.v.observe(self.h.fid,sid,self.h.nid),first)
        self.assertEqual(self.h.r.db.execute('SELECT count(*) FROM lab_result_versions').fetchone()[0],1)

    def test_no_missing_evidence_or_wrong_role(self):
        _,second,sid = self.correction()
        with self.assertRaises(ValueError):
            self.v.review(self.request(second,sid,evidence_snapshot_ids=['absent']))
        run = self.h.r.start_run('red_team',self.h.fid,mode='retrospective')
        with self.assertRaises(ValueError):
            self.v.review(self.request(second,sid,reviewer_run_id=run))

    def test_rejected_correction_keeps_original(self):
        first,second,sid = self.correction()
        self.v.review(self.request(second,sid,decision='rejected'))
        self.assertEqual(self.v.current(self.h.fid)['id'],first['version_id'])

    def test_same_score_new_snapshot_is_corroboration(self):
        first,_ = self.observe((2,1))
        self.h.now += timedelta(days=1)
        second,_ = self.observe((2,1))
        self.assertNotEqual(first['version_id'],second['version_id'])
        self.assertEqual(second['status'],'approved')

    def test_cannot_edit_or_delete_revision_or_grade(self):
        self.observe((2,1)); self.v.grade(self.h.pid)
        for table in ('lab_result_versions','lab_result_version_decisions','lab_prediction_grade_versions'):
            with self.assertRaises(sqlite3.IntegrityError):
                self.h.r.db.execute('DELETE FROM '+table)
            self.h.r.db.rollback()

    def test_independent_connections_do_not_duplicate_result_or_grade(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from foundation.runtime import Runtime
        first,sid=self.observe((2,1))
        barrier=threading.Barrier(2)
        def worker(_):
            r=Runtime(self.h.r.queue.store.path,clock=lambda:self.h.now.isoformat(),registry=self.h.r.queue.registry)
            v=VersionedResults(r)
            try:
                barrier.wait(timeout=10)
                observed=v.observe(self.h.fid,sid,self.h.nid)
                return observed,v.grade(self.h.pid)
            finally:r.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(worker,range(2)))
        self.assertEqual(results[0],results[1])
        self.assertEqual(self.h.r.db.execute('SELECT count(*) FROM lab_result_versions').fetchone()[0],1)
        self.assertEqual(self.h.r.db.execute('SELECT count(*) FROM lab_prediction_grade_versions').fetchone()[0],1)
