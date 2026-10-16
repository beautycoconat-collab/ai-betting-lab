"""Research-only synthetic evidence around archived Bundesliga numerical models."""
import tempfile
import copy
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from foundation.runtime import Runtime
from experts.worker_pipeline import ResearchWorkerPipeline
from tests_experts import test_experts as support

MOCK_POLICY = {'mock_evidence': {'status': 'approved', 'reviewed_at': '2024-01-01',
    'review_expires': '2027-12-31', 'license': 'synthetic-test-only',
    'terms_url': 'https://example.invalid/mock-terms'}}


class WorkerPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.FootballTests.setUpClass()
        cls.engine, cls.synth, cls.row = (support.FootballTests.engine,
            support.FootballTests.synth, support.FootballTests.test_rows[0])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = '2026-10-16T12:00:00+00:00'
        self.runtime = Runtime(Path(self.tmp.name)/'research.db', clock=lambda: self.clock)
        self.pipeline = ResearchWorkerPipeline(self.runtime, self.engine, self.synth, copy.deepcopy(MOCK_POLICY))
        self.fixture_id = UUID(int=173)
        self.kickoff = datetime.fromisoformat(self.row['date']+'T18:00:00+00:00')
        self.as_of = self.kickoff - timedelta(hours=4)
        self.fixture = dict(schema_version='1.0', id=str(self.fixture_id),
            home=self.row['home'], away=self.row['away'], competition='synthetic',
            season='retrospective_mock', kickoff_at=self.kickoff.isoformat(),
            neutral=self.row['neutral'], target='regulation90')
        self.claim = dict(schema_version='1.0', id='evidence-test-1',
            fixture_id=str(self.fixture_id), source_id='mock_evidence',
            snapshot_id='synthetic-snapshot-1', source_url='https://example.invalid/mock',
            observed_at=(self.as_of-timedelta(hours=1)).isoformat(),
            published_at=(self.as_of-timedelta(hours=2)).isoformat(),
            target='regulation90', quality='verified', topic='lineup',
            subject=self.row['home'], value='synthetic lineup only')
        self.snapshots = {'synthetic-snapshot-1': dict(source_id='mock_evidence',
            source_url='https://example.invalid/mock', observed_at=self.claim['observed_at'])}

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def schedule(self, *, claims=None, snapshots=None, fixture=None, mode='retrospective'):
        return self.pipeline.plan(fixture or self.fixture, self.as_of,
            [self.claim] if claims is None else claims,
            self.snapshots if snapshots is None else snapshots, mode=mode)

    def drive_tasks(self, tasks):
        results = []
        for kind in ('validate', 'model', 'red_team', 'referee'):
            results.append(self.pipeline.dispatcher.work_one('test-worker',
                {'validate':'data_validator','model':'score_engine',
                 'red_team':'red_team','referee':'scientific_referee'}[kind]))
        return results

    def output(self, tid):
        from experts.dispatcher import TaskOutput
        row = self.runtime.db.execute('SELECT body FROM expert_task_outputs WHERE task_id=?',(tid,)).fetchone()
        return TaskOutput.model_validate_json(row[0]) if row else None

    def test_four_real_handlers_and_immutable_audit(self):
        tasks=self.schedule()
        self.assertEqual(self.drive_tasks(tasks)[0]['status'], 'done')
        self.assertEqual(self.output(tasks['validate']).data['stage'], 'validate')
        m=self.output(tasks['model']).data
        self.assertEqual(m['stage'], 'model')
        self.assertAlmostEqual(sum(m['probabilities']), 1, places=9)
        self.assertEqual(len(m['versions']),4)
        red=self.output(tasks['red_team']).data
        self.assertEqual(red['prediction_id'],m['prediction_id'])
        self.assertEqual(red['stage'],'red_team')
        referee=self.output(tasks['referee']).data
        self.assertIn(referee['verdict']['status'], ('approved','abstain'))
        self.assertFalse(referee['publishing_enabled'])
        self.assertEqual(self.runtime.db.execute('SELECT count(*) FROM f_prediction_revisions').fetchone()[0],0)
        self.assertEqual(self.runtime.db.execute('SELECT count(*) FROM expert_task_outputs').fetchone()[0],4)
        self.assertTrue(self.runtime.verify_audit())
        self.assertIsNone(self.pipeline.dispatcher.work_one('again','scientific_referee'))

    def test_invalid_snapshot_fails_closed(self):
        tasks=self.schedule(snapshots={})
        r=self.drive_tasks(tasks)
        self.assertEqual(r[0]['status'],'blocked')
        self.assertEqual(self.output(tasks['validate']).data['verification']['status'],'blocked')
        self.assertIsNone(self.output(tasks['model']))
        self.assertIsNone(self.output(tasks['red_team']))
        self.assertIsNone(self.output(tasks['referee']))

    def test_quarantined_evidence_fails_closed(self):
        invalid=dict(self.claim, id='e2', published_at=None)
        tasks=self.schedule(claims=[self.claim,invalid])
        self.assertEqual(self.drive_tasks(tasks)[0]['status'],'blocked')
        self.assertIsNone(self.output(tasks['model']))

    def test_future_observation_rejected_and_no_prediction(self):
        claim=dict(self.claim, observed_at=(self.as_of+timedelta(minutes=1)).isoformat(),
                   published_at=(self.as_of-timedelta(minutes=1)).isoformat())
        snaps={'synthetic-snapshot-1':dict(self.snapshots['synthetic-snapshot-1'],
                                         observed_at=claim['observed_at'])}
        tasks=self.schedule(claims=[claim], snapshots=snaps)
        self.assertEqual(self.drive_tasks(tasks)[0]['status'],'blocked')
        self.assertIsNone(self.output(tasks['model']))

    def test_expired_source_policy_blocks_validation(self):
        self.pipeline.registry['mock_evidence']['review_expires']='2024-01-01'
        tasks=self.schedule()
        self.assertEqual(self.drive_tasks(tasks)[0]['status'],'blocked')
        self.assertIsNone(self.output(tasks['referee']))

    def test_cancelled_validator_blocks_entire_chain(self):
        tasks=self.schedule()
        self.assertTrue(self.pipeline.dispatcher.cancel(tasks['validate']))
        self.assertIsNone(self.pipeline.dispatcher.work_one('w','data_validator'))
        self.assertIsNone(self.pipeline.dispatcher.work_one('w','score_engine'))
        self.assertIsNone(self.output(tasks['model']))

    def test_replay_idempotent_and_revisions_rejected(self):
        tasks=self.schedule()
        self.assertEqual(tasks,self.schedule())
        changed=dict(self.claim, value='altered')
        revised=self.schedule(claims=[changed])
        self.assertNotEqual(tasks, revised)
        # Immutable key for the old set never changes.
        self.assertEqual(tasks,self.schedule())

    def test_expired_lease_cannot_publish(self):
        tasks=self.schedule()
        original=self.pipeline.dispatcher.handlers['validate']
        def slow(job, deps):
            result=original(job,deps)
            self.clock='2026-10-18T12:00:00+00:00'
            return result
        self.pipeline.dispatcher.handlers['validate']=slow
        self.assertEqual(self.drive_tasks(tasks)[0]['status'],'lease_lost')
        self.assertIsNone(self.output(tasks['validate']))
        self.assertIsNone(self.output(tasks['model']))

    def test_prematch_refuses_retrospective_engine(self):
        with self.assertRaisesRegex(ValueError,'prospective'):
            self.schedule(mode='prematch')
        self.assertEqual(self.runtime.db.execute('SELECT count(*) FROM f_tasks').fetchone()[0],0)

    def test_no_fabricated_lineup_means_review_skip(self):
        no_lineup=dict(self.claim, topic='fixture')
        tasks=self.schedule(claims=[no_lineup])
        out=self.drive_tasks(tasks)
        self.assertEqual([o['status'] for o in out],['done']*4)
        review=self.output(tasks['referee']).data
        self.assertEqual(review['verdict']['status'],'abstain')
        self.assertEqual(review['verdict']['risk_action'],'skip')
        self.assertEqual(len(review['review_history']),2)
        self.assertIn('lineup_unverified', review['verdict']['reasons'])

    def test_model_does_not_run_before_validation(self):
        tasks=self.schedule()
        self.assertIsNone(self.pipeline.dispatcher.work_one('w','score_engine'))
        self.assertIsNone(self.output(tasks['model']))
        self.assertEqual(self.runtime.db.execute('SELECT count(*) FROM expert_task_outputs').fetchone()[0],0)

    def test_reject_invalid_fixture_and_future_cutoff(self):
        invalid=dict(self.fixture,home=self.fixture['away'],away=self.fixture['away'])
        with self.assertRaises(ValueError):
            self.schedule(fixture=invalid)
        with self.assertRaisesRegex(ValueError,'invalid_research_cutoff'):
            self.pipeline.plan(self.fixture,self.kickoff, [self.claim],self.snapshots)

if __name__ == '__main__':
    unittest.main()
