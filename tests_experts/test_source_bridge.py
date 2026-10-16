"""Offline, provenance-backed integration checks; no external network."""
import json
import tempfile
import unittest
import zlib
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from foundation.runtime import Runtime
from foundation.contracts import JobRequest
from betting_lab.domain import digest
from engine.adapters import ADAPTERS
from experts.source_bridge import verified_snapshot_handler
from experts.dispatcher import Dispatcher
from tests_experts.test_experts import NOW, fixture, REGISTRY


class SourceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.temp.name)/'lab.db', clock=lambda: NOW.isoformat(), registry=deepcopy(REGISTRY))
        self.fixture = fixture(competition="zz.1", season="2026-27")
        self.runtime.fixture(str(self.fixture.id), self.fixture.kickoff_at.isoformat(), self.fixture.target,
                             self.fixture.home, self.fixture.away)
        self.sid = 'stored-snapshot-1'
        self.params = {'league': self.fixture.competition, 'season': self.fixture.season}
        self.nid = digest([self.fixture.competition, self.fixture.season, self.fixture.home,
                           self.fixture.away, self.fixture.kickoff_at.date().isoformat()])
        self.raw = json.dumps({'matches': [{'date': self.fixture.kickoff_at.date().isoformat(),
            'team1': self.fixture.home, 'team2': self.fixture.away}]}).encode()
        self.observed = (NOW-timedelta(minutes=10)).isoformat()
        self.url = ADAPTERS['openfootball'].url('collect', self.params)
        self.source_job = self.runtime.queue.enqueue('openfootball', 'collect', self.params, self.observed)
        self.runtime.db.execute('UPDATE v2_jobs SET status=? WHERE id=?', ('done', self.source_job))
        self.runtime.db.execute('''INSERT INTO v2_snapshots
            (id,job_id,source,url,observed_at,sha256,body,headers)
            VALUES (?,?,?,?,?,?,?,?)''',
            (self.sid, self.source_job, 'openfootball', self.url, self.observed,
             digest(self.raw), zlib.compress(self.raw), '{}'))
        row = {'native_id': self.nid, 'home': self.fixture.home, 'away': self.fixture.away,
               'competition': self.fixture.competition, 'season': self.fixture.season,
               'date': self.fixture.kickoff_at.date().isoformat(), 'target': self.fixture.target,
               'neutral': False, 'home_goals': None, 'away_goals': None,
               'kickoff_at': None, 'source': 'openfootball'}
        self.runtime.db.execute('INSERT INTO v2_results VALUES(?,?,?,?)',
                                (self.sid, 'openfootball', self.nid, json.dumps(row)))
        self.runtime.db.commit()
        self.task = self.runtime.enqueue(dict(schema_version='1.0', kind='collect',
            fixture_id=str(self.fixture.id), idempotency_key='bridge-fixture-test'))
        self.dispatcher = Dispatcher(self.runtime, {})
        self.input = dict(fixture=self.fixture.model_dump(mode='json'), as_of=NOW.isoformat(),
                          snapshot_id=self.sid, native_id=self.nid)

    def tearDown(self):
        self.runtime.close()
        self.temp.cleanup()

    def run_handler(self):
        self.dispatcher.handlers['collect'] = verified_snapshot_handler(self.runtime, self.dispatcher.load_input)
        self.dispatcher.bind_input(self.task, self.input)
        status = self.dispatcher.work_one('source-worker', 'source_hunter')
        result = self.runtime.db.execute('SELECT body FROM expert_task_outputs WHERE task_id=?', (self.task,)).fetchone()
        return status, json.loads(result[0]) if result else None

    def test_real_stored_source_snapshot_reaches_dispatcher(self):
        status, result = self.run_handler()
        self.assertEqual(status['status'], 'done')
        self.assertEqual(result['data']['kind'], 'verified_fixture_snapshot')
        self.assertEqual(result['data']['publication_time_status'], 'not_proven')
        self.assertEqual(result['data']['kickoff_precision'], 'date_only')
        self.assertEqual(result['data']['snapshot_sha256'], digest(self.raw))
        self.assertTrue(self.runtime.verify_audit())

    def test_snapshot_after_as_of_blocked(self):
        self.runtime.db.execute('UPDATE v2_snapshots SET observed_at=? WHERE id=?',
                                ((NOW + timedelta(minutes=1)).isoformat(), self.sid))
        self.runtime.db.commit()
        self.assertEqual(self.run_handler()[1]['reason'], 'snapshot_not_available_at_cutoff')

    def test_snapshot_with_future_result_blocked(self):
        row = json.loads(self.runtime.db.execute('SELECT payload FROM v2_results').fetchone()[0])
        row['home_goals'], row['away_goals'] = 3, 1
        self.runtime.db.execute('UPDATE v2_results SET payload=?', (json.dumps(row),))
        self.runtime.db.commit()
        self.assertEqual(self.run_handler()[1]['reason'], 'normalized_payload_not_from_snapshot')

    def test_snapshot_hash_tampering_blocked(self):
        self.runtime.db.execute('UPDATE v2_snapshots SET sha256=?', ('not-the-hash',))
        self.runtime.db.commit()
        self.assertEqual(self.run_handler()[1]['reason'], 'snapshot_hash_mismatch')

    def test_normalized_row_not_in_raw_blocked(self):
        row = json.loads(self.runtime.db.execute('SELECT payload FROM v2_results').fetchone()[0])
        row['season'] = '2025-26'
        self.runtime.db.execute('UPDATE v2_results SET payload=?', (json.dumps(row),))
        self.runtime.db.commit()
        self.assertEqual(self.run_handler()[1]['reason'], 'normalized_payload_not_from_snapshot')

    def test_identity_mismatch_blocked(self):
        row = json.loads(self.runtime.db.execute('SELECT payload FROM v2_results').fetchone()[0])
        row['away'] = 'Another team'
        self.runtime.db.execute('UPDATE v2_results SET payload=?', (json.dumps(row),))
        self.runtime.db.commit()
        self.assertEqual(self.run_handler()[1]['reason'], 'normalized_payload_not_from_snapshot')

    def test_unapproved_source_blocked(self):
        self.runtime.queue.registry['openfootball'] = dict(REGISTRY['openfootball'], status='blocked')
        self.assertEqual(self.run_handler()[1]['reason'], 'source_policy_blocked')

    def test_unfinished_source_job_blocked(self):
        self.runtime.db.execute('UPDATE v2_jobs SET status=?', ('pending',))
        self.runtime.db.commit()
        self.assertEqual(self.run_handler()[1]['reason'], 'collection_not_verified')

    def test_missing_native_id_blocked(self):
        self.input['native_id'] = 'nonexistent'
        self.assertEqual(self.run_handler()[1]['reason'], 'normalized_fixture_not_found')

    def test_missing_snapshot_blocked(self):
        self.input['snapshot_id'] = 'nonexistent'
        self.assertEqual(self.run_handler()[1]['reason'], 'source_snapshot_missing')

    def test_rejects_unbound_missing_input(self):
        self.dispatcher.handlers['collect'] = verified_snapshot_handler(self.runtime, self.dispatcher.load_input)
        result = self.dispatcher.work_one('source-worker', 'source_hunter')
        self.assertEqual(result['status'], 'retry_or_failed')
        self.assertEqual(self.runtime.db.execute('SELECT count(*) FROM expert_task_outputs').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
