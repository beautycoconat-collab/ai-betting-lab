"""Connect the v2 *persisted* source queue to the expert dispatcher.

The source worker is always run independently using its own policy and quota
checks. This adapter only consumes a committed collection job and does not
claim that a parsed fixture is lineup or odds evidence.
"""
from betting_lab.domain import digest
from .contracts import Fixture
from .dispatcher import Dispatcher
from .research import SourceHunter, aware
from .source_bridge import verified_snapshot_handler


class CollectionPipeline:
    def __init__(self, runtime):
        self.runtime = runtime
        self.dispatcher = Dispatcher(runtime, {'collect': verified_snapshot_handler(runtime, lambda job: self.dispatcher.load_input(job))})

    def request(self, fixture, source, params, as_of):
        """Schedule permission-checked source job; do not perform HTTP inline."""
        f, at = Fixture.model_validate(fixture), aware(as_of)
        if at > aware(self.runtime.clock()) or at >= f.kickoff_at:
            raise ValueError('invalid_collection_cutoff')
        if not isinstance(params, dict):
            raise ValueError('invalid_source_params')
        return SourceHunter(self.runtime.queue).schedule(source, 'collect', params, at, cycle=at.date().isoformat())

    def bind(self, fixture, source_job_id, native_id, as_of):
        """Bind a fully completed source snapshot to one immutable expert input.

        The expert worker independently checks the byte-level raw snapshot,
        normalized row, match identity and all timestamps when it runs.
        """
        f, at = Fixture.model_validate(fixture), aware(as_of)
        if at > aware(self.runtime.clock()) or at >= f.kickoff_at:
            raise ValueError('invalid_collection_cutoff')
        if not isinstance(native_id, str) or not native_id:
            raise ValueError('native_id_required')
        source_job = self.runtime.db.execute(
            "SELECT id,kind,status,source FROM v2_jobs WHERE id=?", (source_job_id,)).fetchone()
        if not source_job or source_job['kind'] != 'collect' or source_job['status'] != 'done':
            raise ValueError('source_job_not_completed')
        if SourceHunter(self.runtime.queue).inspect(at).get(source_job['source'], {}).get('status') != 'ready':
            raise ValueError('source_permission_unverified')
        snapshots = self.runtime.db.execute('''SELECT s.id FROM v2_snapshots s
            JOIN v2_results r ON r.snapshot_id=s.id AND r.source=s.source
            WHERE (s.job_id=? OR EXISTS (SELECT 1 FROM v2_job_snapshots js
                    WHERE js.job_id=? AND js.snapshot_id=s.id))
              AND s.source=? AND r.native_id=? AND s.observed_at<=?
            ORDER BY s.observed_at DESC,s.id DESC''',
            (source_job_id, source_job_id, source_job['source'], native_id, at.isoformat())).fetchall()
        if len(snapshots) != 1:
            # No guessing among several versions, no borrowing another job's cache.
            raise ValueError('source_snapshot_not_unique_or_missing')
        old = self.runtime.db.execute('SELECT * FROM f_fixtures WHERE id=?', (str(f.id),)).fetchone()
        if old:
            if (old['home'] != f.home or old['away'] != f.away or old['target'] != f.target
                    or aware(old['kickoff_at']) != f.kickoff_at):
                raise ValueError('fixture_identity_conflict')
        else:
            self.runtime.fixture(str(f.id), f.kickoff_at.isoformat(), f.target, f.home, f.away)
        sid = snapshots[0]['id']
        key = 'verified-source:' + digest([str(f.id), sid, native_id, at.isoformat()])
        task_id = self.runtime.enqueue(dict(schema_version='1.0', kind='collect',
            fixture_id=str(f.id), idempotency_key=key))
        self.dispatcher.bind_input(task_id, dict(fixture=f.model_dump(mode='json'),
            as_of=at.isoformat(), snapshot_id=sid, native_id=native_id))
        return task_id
