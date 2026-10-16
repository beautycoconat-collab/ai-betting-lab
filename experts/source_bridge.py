"""Fail-closed bridge from an *already collected* phase-2 source snapshot.

This is offline verified replay, not a live collector or a publication-time proof.
The source Queue owns network access, quotas, and collection jobs. The expert
Dispatcher can consume its durable output only after the job is settled.
"""
import json
import zlib
from .contracts import Fixture
from .dispatcher import TaskOutput
from .research import aware, approved
from betting_lab.domain import digest
from engine.adapters import ADAPTERS
from engine.normalization import normalize


def verified_snapshot_handler(runtime, load_input):
    """Create a `collect` task handler bound to the existing v2 storage.

    Input is an immutable dict with fixture, as_of, snapshot_id and native_id.
    The exact native match ID is mandatory: no fuzzy matching or guessed IDs.
    Return only fixture-level provenance, *not* lineup, odds or predictions.
    """
    def execute(job, dependencies):
        if job.kind != 'collect' or job.fixture_id is None:
            raise ValueError('collect_fixture_required')
        payload = load_input(job)
        fixture = Fixture.model_validate(payload['fixture'])
        at = aware(payload['as_of'])
        if fixture.id != job.fixture_id:
            raise ValueError('fixture_identity_mismatch')
        if at >= fixture.kickoff_at:
            raise ValueError('kickoff_passed')
        snapshot_id = payload['snapshot_id']
        native_id = payload['native_id']
        if not isinstance(snapshot_id, str) or not snapshot_id or not isinstance(native_id, str) or not native_id:
            raise ValueError('snapshot_and_native_id_required')
        record = runtime.db.execute('''SELECT s.*,j.status AS job_status,j.kind AS job_kind,
            j.source AS job_source FROM v2_snapshots s
            JOIN v2_jobs j ON j.id=s.job_id WHERE s.id=?''', (snapshot_id,)).fetchone()
        if not record:
            return TaskOutput(schema_version='1.0', status='blocked', reason='source_snapshot_missing')
        observed = aware(record['observed_at'])
        policy = runtime.queue.registry.get(record['source'], {})
        if (record['job_status'] != 'done' or record['job_kind'] != 'collect'
                or record['job_source'] != record['source']):
            return TaskOutput(schema_version='1.0', status='blocked', reason='collection_not_verified')
        if not approved(policy, at):
            return TaskOutput(schema_version='1.0', status='blocked', reason='source_policy_blocked')
        if observed > at or observed >= fixture.kickoff_at:
            return TaskOutput(schema_version='1.0', status='blocked', reason='snapshot_not_available_at_cutoff')
        if not record['url'].startswith('https://'):
            return TaskOutput(schema_version='1.0', status='blocked', reason='unsafe_source_url')
        try:
            # Maximum 10 MB decompressed; do not accept decompression bombs.
            decompressor = zlib.decompressobj()
            raw = decompressor.decompress(record['body'], 10_000_001)
            if len(raw) > 10_000_000 or not decompressor.eof:
                raise ValueError('snapshot_expansion_limit')
        except (TypeError, zlib.error, ValueError):
            return TaskOutput(schema_version='1.0', status='blocked', reason='snapshot_corrupt')
        if digest(raw) != record['sha256']:
            return TaskOutput(schema_version='1.0', status='blocked', reason='snapshot_hash_mismatch')
        job_record = runtime.db.execute('SELECT params FROM v2_jobs WHERE id=?', (record['job_id'],)).fetchone()
        try:
            params = json.loads(job_record['params'])
            adapter = ADAPTERS[record['source']]
            if record['url'] != adapter.url('collect', params):
                raise ValueError('unexpected_source_url')
            normalized, rejected = normalize(adapter, adapter.decode(raw, 'collect'), params)
        except (KeyError, ValueError, TypeError, AttributeError, zlib.error):
            return TaskOutput(schema_version='1.0', status='blocked', reason='source_parse_unverified')
        rows = runtime.db.execute('''SELECT payload FROM v2_results
            WHERE snapshot_id=? AND source=? AND native_id=?''',
            (snapshot_id, record['source'], native_id)).fetchall()
        if len(rows) != 1:
            return TaskOutput(schema_version='1.0', status='blocked', reason='normalized_fixture_not_found')
        try:
            match = json.loads(rows[0]['payload'])
        except (TypeError, ValueError):
            return TaskOutput(schema_version='1.0', status='blocked', reason='normalized_fixture_corrupt')
        # Prove that the stored normalized row was derived from the immutable raw
        # snapshot rather than inserted or mutated after collection.
        matching = [row for row in normalized if row['native_id'] == native_id]
        if len(matching) != 1 or matching[0] != match:
            return TaskOutput(schema_version='1.0', status='blocked', reason='normalized_payload_not_from_snapshot')
        # Deliberately reject shortcuts: historic final scores observed after a
        # kickoff cannot masquerade as pre-match fixture information.
        if (match.get('home') != fixture.home or match.get('away') != fixture.away
                or match.get('competition') != fixture.competition
                or str(match.get('season')) != fixture.season
                or match.get('date') != fixture.kickoff_at.date().isoformat()
                or match.get('target') != fixture.target
                or match.get('neutral') != fixture.neutral):
            return TaskOutput(schema_version='1.0', status='blocked', reason='fixture_or_target_mismatch')
        if match.get('kickoff_at') and aware(match['kickoff_at']) != fixture.kickoff_at:
            return TaskOutput(schema_version='1.0', status='blocked', reason='kickoff_mismatch')
        if match.get('home_goals') is not None or match.get('away_goals') is not None:
            return TaskOutput(schema_version='1.0', status='blocked', reason='future_result_in_fixture_row')
        return TaskOutput(schema_version='1.0', status='ready', data={
            'kind': 'verified_fixture_snapshot', 'fixture_id': str(fixture.id),
            'source_id': record['source'], 'source_url': record['url'],
            'snapshot_id': record['id'], 'snapshot_sha256': record['sha256'],
            'native_id': native_id, 'observed_at': observed.isoformat(),
            'as_of': at.isoformat(), 'publication_time_status': 'not_proven',
            'lineup_status': 'not_proven', 'odds_status': 'not_proven',
            'kickoff_precision': 'exact' if match.get('kickoff_at') else 'date_only'})
    return execute
