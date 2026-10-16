"""Real queue -> persisted snapshot -> expert worker, with fake network input."""
import json
import tempfile
from copy import deepcopy
import unittest
from pathlib import Path
from datetime import timedelta
from foundation.runtime import Runtime
from betting_lab.domain import digest
from experts.collection_pipeline import CollectionPipeline
from tests_experts.test_experts import fixture, NOW, REGISTRY


class CollectionPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name) / 'test.db', clock=lambda: NOW.isoformat(), registry=deepcopy(REGISTRY))
        self.f = fixture(competition='zz.1', season='2026-27')
        self.pipeline = CollectionPipeline(self.r)
        self.params = {'league': self.f.competition, 'season': self.f.season}
        self.nid = digest([self.f.competition, self.f.season,
                           self.f.home, self.f.away, self.f.kickoff_at.date().isoformat()])
        self.body = json.dumps({'matches': [{'date': self.f.kickoff_at.date().isoformat(),
                         'team1': self.f.home, 'team2': self.f.away}]}).encode()

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def collect(self, body=None):
        jid = self.pipeline.request(self.f, 'openfootball', self.params, NOW)
        result = self.r.queue.work_one(lambda _: (self.body if body is None else body, {}),
                                      clock=lambda: NOW.isoformat())
        return jid, result

    def test_queue_to_expert_verified_provenance_and_no_invented_lineup(self):
        jid, source_result = self.collect()
        self.assertEqual(source_result['status'], 'done')
        tid = self.pipeline.bind(self.f, jid, self.nid, NOW)
        self.assertEqual(tid, self.pipeline.bind(self.f, jid, self.nid, NOW))
        self.assertEqual(self.pipeline.dispatcher.work_one('worker-1', 'source_hunter')['status'], 'done')
        result = json.loads(self.r.db.execute('''SELECT body FROM expert_task_outputs
              WHERE task_id=?''',(tid,)).fetchone()[0])
        self.assertEqual(result['data']['native_id'], self.nid)
        self.assertEqual(result['data']['publication_time_status'], 'not_proven')
        self.assertEqual(result['data']['lineup_status'], 'not_proven')
        self.assertTrue(self.r.verify_audit())
        self.assertEqual(self.r.db.execute('SELECT COUNT(*) FROM requests').fetchone()[0], 1)

    def test_waits_for_actual_source_worker(self):
        jid = self.pipeline.request(self.f, 'openfootball', self.params, NOW)
        with self.assertRaisesRegex(ValueError, 'source_job_not_completed'):
            self.pipeline.bind(self.f, jid, self.nid, NOW)
        self.assertEqual(self.r.db.execute('SELECT COUNT(*) FROM f_tasks').fetchone()[0], 0)

    def test_rejects_foreign_native_match(self):
        jid, _ = self.collect()
        with self.assertRaisesRegex(ValueError, 'source_snapshot_not_unique_or_missing'):
            self.pipeline.bind(self.f, jid, 'wrong-match', NOW)

    def test_suspect_final_score_is_not_prematch_evidence(self):
        dirty = json.dumps({'matches': [{'date': self.f.kickoff_at.date().isoformat(),
                  'team1': self.f.home, 'team2': self.f.away, 'score': {'ft': [1, 0]}}]}).encode()
        jid, _ = self.collect(dirty)
        tid = self.pipeline.bind(self.f, jid, self.nid, NOW)
        self.assertEqual(self.pipeline.dispatcher.work_one('worker-1', 'source_hunter')['status'],'blocked')
        output = json.loads(self.r.db.execute('SELECT body FROM expert_task_outputs WHERE task_id=?',
                                              (tid,)).fetchone()[0])
        self.assertEqual(output['reason'], 'future_result_in_fixture_row')

    def test_rejects_post_kickoff_binding(self):
        jid, _ = self.collect()
        with self.assertRaisesRegex(ValueError, 'invalid_collection_cutoff'):
            self.pipeline.bind(self.f, jid, self.nid, self.f.kickoff_at + timedelta(seconds=1))

    def test_rejects_expired_policy_on_binding(self):
        jid, _ = self.collect()
        self.r.queue.registry['openfootball']['review_expires'] = '2026-01-01'
        with self.assertRaisesRegex(ValueError, 'source_permission_unverified'):
            self.pipeline.bind(self.f, jid, self.nid, NOW)

    def test_completed_cache_job_preserves_verified_source_provenance(self):
        first, first_result = self.collect()
        self.assertEqual(first_result['status'], 'done')
        # Another date-specific source job reuses the already collected snapshot.
        second = self.r.queue.enqueue('openfootball','collect',self.params,
                                      NOW.isoformat(),cycle='2026-10-16')
        out = self.r.queue.work_one(lambda u:self.fail('should use cache'),
                                    clock=lambda: NOW.isoformat())
        self.assertEqual(out['status'], 'cached')
        self.assertNotEqual(first, second)
        tid = self.pipeline.bind(self.f, second, self.nid, NOW)
        self.assertEqual(self.pipeline.dispatcher.work_one('w','source_hunter')['status'],'done')
        record = json.loads(self.r.db.execute('SELECT body FROM expert_task_outputs WHERE task_id=?',
                                              (tid,)).fetchone()[0])
        self.assertEqual(record['data']['snapshot_id'],first_result['snapshot_id'])
        self.assertEqual(record['data']['publication_time_status'],'not_proven')

    def test_rejects_unapproved_request(self):
        with self.assertRaisesRegex(ValueError, 'source_not_approved_or_no_adapter'):
            self.pipeline.request(self.f, 'unknown', self.params, NOW)

if __name__ == '__main__':
    unittest.main()
