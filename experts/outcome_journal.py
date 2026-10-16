"""Local, forward-only, append-only outcome audit (never a betting interface).

A provider's persisted collection snapshot is verified against its raw bytes,
normalization and exact fixture identity before an observed final may be recorded.
No settlement or grading is permitted without a prediction locked *before* kickoff.
The API performs no HTTP, wallet operations, odds lookups or hosted writes.
"""
import hashlib
import json
import math
import zlib
from datetime import timedelta
from uuid import UUID

from betting_lab.domain import digest
from engine.adapters import ADAPTERS
from engine.normalization import normalize
from foundation.runtime import canonical
from .research import aware, approved
from .contracts import Fixture
from .settlement import Pick, settle_pick


SCHEMA = '''
CREATE TABLE IF NOT EXISTS lab_locked_predictions (
  prediction_id TEXT PRIMARY KEY,
  fixture_id TEXT NOT NULL REFERENCES f_fixtures(id),
  captured_at TEXT NOT NULL,
  model_hash TEXT NOT NULL,
  probabilities TEXT NOT NULL,
  pick TEXT,
  referee_task_id TEXT NOT NULL REFERENCES f_tasks(id),
  review_evidence_hash TEXT NOT NULL,
  fixture_contract TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lab_verified_results (
  fixture_id TEXT PRIMARY KEY REFERENCES f_fixtures(id),
  snapshot_id TEXT NOT NULL REFERENCES v2_snapshots(id),
  native_id TEXT NOT NULL,
  result_body TEXT NOT NULL,
  provenance TEXT NOT NULL,
  recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lab_prediction_grades (
  prediction_id TEXT PRIMARY KEY REFERENCES lab_locked_predictions(prediction_id),
  fixture_id TEXT NOT NULL REFERENCES lab_verified_results(fixture_id),
  verdict TEXT,
  log_loss REAL NOT NULL,
  brier REAL NOT NULL,
  recorded_at TEXT NOT NULL
);
'''


def _same_instant(a, b):
    return aware(a) == aware(b)


def _raw_snapshot(runtime, snapshot_id):
    record = runtime.db.execute('''SELECT s.*,j.status job_status,j.kind job_kind,
            j.source job_source,j.params FROM v2_snapshots s
            JOIN v2_jobs j ON j.id=s.job_id WHERE s.id=?''', (snapshot_id,)).fetchone()
    if not record or record['job_status'] != 'done' or record['job_kind'] != 'collect' or record['source'] != record['job_source']:
        raise ValueError('verified_completed_collection_required')
    source = record['source']
    policy = runtime.queue.registry.get(source, {})
    now = aware(runtime.clock())
    observed = aware(record['observed_at'])
    if observed > now or not approved(policy, now):
        raise ValueError('source_policy_or_time_invalid')
    if not record['url'].startswith('https://') or source not in ADAPTERS:
        raise ValueError('unapproved_adapter_or_url')
    adapter = ADAPTERS[source]
    try:
        params = json.loads(record['params'])
        if record['url'] != adapter.url('collect', params):
            raise ValueError('source_url_mismatch')
        dec = zlib.decompressobj()
        raw = dec.decompress(record['body'], 10_000_001)
        if len(raw) > 10_000_000 or not dec.eof or dec.unused_data or dec.unconsumed_tail:
            raise ValueError('oversized_or_trailing_snapshot')
        if digest(raw) != record['sha256']:
            raise ValueError('raw_snapshot_hash_mismatch')
        normalized, _ = normalize(adapter, adapter.decode(raw, 'collect'), params)
    except (zlib.error, KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError('unverifiable_source_snapshot') from exc
    return record, normalized, observed


def verify_result_snapshot(runtime, fixture_id, snapshot_id, native_id):
    """Validate post-match result from recorded *raw* collection, not free text.

    No implicit provider final->regulation conversion. A score without an exact
    kickoff may be used only after matching the known fixture date and teams;
    the result's source precision is preserved, not upgraded to exact.
    """
    if not isinstance(native_id, str) or not native_id:
        raise ValueError('native_id_required')
    fid = str(UUID(str(fixture_id)))
    fixture = runtime.db.execute('SELECT * FROM f_fixtures WHERE id=?', (fid,)).fetchone()
    if fixture is None:
        raise ValueError('unknown_fixture')
    # Foundation stores no competition/season; require a pre-kickoff locked
    # full fixture contract to disambiguate otherwise identical team names.
    locked = runtime.db.execute('''SELECT DISTINCT fixture_contract
        FROM lab_locked_predictions WHERE fixture_id=?''', (fid,)).fetchall()
    if len(locked) != 1:
        raise ValueError('unique_locked_fixture_contract_required')
    full_fixture = Fixture.model_validate_json(locked[0][0])
    if (str(full_fixture.id) != fid or full_fixture.home != fixture['home']
        or full_fixture.away != fixture['away']
        or full_fixture.target != fixture['target']
        or not _same_instant(full_fixture.kickoff_at, fixture['kickoff_at'])):
        raise ValueError('locked_fixture_identity_mismatch')
    record, rows, observed = _raw_snapshot(runtime, snapshot_id)
    kickoff = aware(fixture['kickoff_at'])
    if observed < kickoff + timedelta(minutes=90):
        raise ValueError('final_observed_before_possible_full_time')
    matches = [r for r in rows if r['native_id'] == native_id]
    if len(matches) != 1:
        raise ValueError('native_match_missing_or_ambiguous')
    match = matches[0]
    persisted = runtime.db.execute('''SELECT payload FROM v2_results
        WHERE snapshot_id=? AND source=? AND native_id=?''',
        (snapshot_id, record['source'], native_id)).fetchall()
    if len(persisted) != 1 or json.loads(persisted[0][0]) != match:
        raise ValueError('normalized_row_not_proven')
    if (match['home'] != fixture['home'] or match['away'] != fixture['away']
        or match['competition'] != full_fixture.competition
        or str(match['season']) != full_fixture.season
        or (match['neutral'] is not None and match['neutral'] != full_fixture.neutral)
        or match['target'] != fixture['target']
        or match['date'] != kickoff.date().isoformat()):
        raise ValueError('fixture_or_score_target_mismatch')
    if match.get('kickoff_at') and not _same_instant(match['kickoff_at'], kickoff):
        raise ValueError('fixture_kickoff_mismatch')
    if match['home_goals'] is None or match['away_goals'] is None:
        raise ValueError('official_final_not_available')
    if fixture['target'] != 'regulation90':
        raise ValueError('regulation90_only')
    final = dict(schema_version='1.0',status='final',home=match['home_goals'],
                 away=match['away_goals'],target='regulation90')
    provenance = dict(snapshot_id=snapshot_id, raw_sha256=record['sha256'],
                      source_id=record['source'], native_id=native_id,
                      observed_at=observed.isoformat(), source_url=record['url'],
                      published_at='unknown',
                      kickoff_precision='exact' if match.get('kickoff_at') else 'date_only',
                      neutral_status='verified' if match['neutral'] is not None else 'provider_unspecified')
    return final, provenance


def _probabilities(probs):
    if not isinstance(probs, (tuple, list)) or len(probs) != 3:
        raise ValueError('invalid_1x2_probabilities')
    if any(type(p) not in (float, int) or not math.isfinite(p) or p < 0 or p > 1 for p in probs):
        raise ValueError('invalid_1x2_probabilities')
    if abs(sum(probs)-1) > 1e-8:
        raise ValueError('invalid_probability_mass')
    return tuple(float(p) for p in probs)


class OutcomeJournal:
    """SQLite trusted-process evidence ledger, not Supabase or hosted auth."""
    def __init__(self, runtime):
        self.runtime = runtime
        runtime.db.executescript(SCHEMA)
        for table in ('lab_locked_predictions', 'lab_verified_results', 'lab_prediction_grades'):
            for action in ('UPDATE', 'DELETE'):
                runtime.db.execute(f'''CREATE TRIGGER IF NOT EXISTS {table}_{action}
                    BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'append_only'); END''')
        runtime.db.commit()

    def lock_prediction(self, prediction_id, fixture_id, probabilities, model_hash,
                        referee_task_id, *, pick=None):
        """Capture *at current clock time*; require real approved task evidence.

        A caller cannot supply past 'as_of' time. Research/replay forecasts are
        never admitted retroactively as forward predictions.
        """
        r = self.runtime
        fid = str(UUID(str(fixture_id)))
        probabilities = _probabilities(probabilities)
        if not isinstance(prediction_id, str) or not prediction_id or len(prediction_id) > 200:
            raise ValueError('prediction_id_required')
        if not isinstance(model_hash, str) or not model_hash or len(model_hash) > 200:
            raise ValueError('model_hash_required')
        spec = Pick.model_validate(pick).model_dump(mode='json') if pick is not None else None
        now = aware(r.clock())
        with r.transaction():
            fixture = r.db.execute('SELECT * FROM f_fixtures WHERE id=?',(fid,)).fetchone()
            if not fixture or fixture['target'] != 'regulation90' or now >= aware(fixture['kickoff_at']):
                raise ValueError('forward_prematch_fixture_required')
            task = r.db.execute('''SELECT t.kind,t.status,t.body,o.body output
                FROM f_tasks t JOIN expert_task_outputs o ON o.task_id=t.id
                WHERE t.id=?''',(referee_task_id,)).fetchone()
            if not task or task['kind'] != 'referee' or task['status'] != 'done':
                raise ValueError('completed_referee_required')
            body = json.loads(task['body'])
            review = json.loads(task['output'])
            data = review.get('data',{})
            if (body.get('fixture_id') != fid or review['status'] != 'ready'
                or data.get('stage') != 'referee' or data.get('prediction_id') != prediction_id
                or data.get('verdict',{}).get('status') != 'approved'
                or data.get('verdict',{}).get('risk_action') != 'wait'
                or data.get('publishing_enabled') is not False):
                raise ValueError('referee_not_approved_for_research_lock')
            # The model output must actually carry the probabilities. Reject a
            # disconnected fabricated review task / unrelated model results.
            review_input = r.db.execute('SELECT body FROM expert_task_inputs WHERE task_id=?',
                                        (referee_task_id,)).fetchone()
            model_output = r.db.execute('''SELECT o.body FROM f_task_dependencies d
                JOIN f_tasks red ON red.id=d.depends_on
                JOIN f_task_dependencies rd ON rd.task_id=red.id
                JOIN f_tasks mod ON mod.id=rd.depends_on
                JOIN expert_task_outputs o ON o.task_id=mod.id
                WHERE d.task_id=? AND red.kind='red_team' AND mod.kind='model' ''',
                (referee_task_id,)).fetchall()
            if len(model_output) != 1:
                raise ValueError('model_dependency_not_found')
            model_data = json.loads(model_output[0][0])['data']
            if (model_data.get('prediction_id') != prediction_id
                or model_data.get('input_hash') != data.get('input_hash')
                or tuple(model_data.get('probabilities',())) != probabilities
                or model_data.get('mode') != 'prematch'):
                raise ValueError('referee_model_provenance_mismatch')
            if not review_input:
                raise ValueError('immutable_referee_input_required')
            ref_payload = json.loads(review_input[0])
            full_fixture = Fixture.model_validate(ref_payload.get('fixture'))
            cutoff = aware(ref_payload.get('as_of'))
            if (ref_payload.get('mode') != 'prematch'
                or cutoff > now or cutoff >= full_fixture.kickoff_at
                or str(full_fixture.id) != fid or full_fixture.home != fixture['home']
                or full_fixture.away != fixture['away']
                or full_fixture.target != fixture['target']
                or not _same_instant(full_fixture.kickoff_at, fixture['kickoff_at'])):
                raise ValueError('referee_fixture_or_cutoff_mismatch')
            versions = model_data.get('versions')
            if not isinstance(versions, dict) or not versions or model_hash != digest(versions):
                raise ValueError('model_version_digest_mismatch')
            fixture_body = canonical(full_fixture.model_dump(mode='json'))
            payload = canonical([fid, now.isoformat(), model_hash, probabilities, spec,
                                 referee_task_id, data['input_hash']])
            old = r.db.execute('SELECT * FROM lab_locked_predictions WHERE prediction_id=?',
                               (prediction_id,)).fetchone()
            if old:
                # A retry after kickoff cannot forge a different prediction.
                if (old['fixture_id'], old['model_hash'], old['probabilities'], old['pick'],
                    old['referee_task_id']) != (fid, model_hash, canonical(probabilities),
                                                   canonical(spec) if spec is not None else None, referee_task_id):
                    raise ValueError('prediction_revision_conflict')
                return prediction_id
            r.db.execute('INSERT INTO lab_locked_predictions VALUES(?,?,?,?,?,?,?,?,?)',
                         (prediction_id, fid, now.isoformat(), model_hash, canonical(probabilities),
                          canonical(spec) if spec is not None else None, referee_task_id,
                          hashlib.sha256(payload.encode()).hexdigest(), fixture_body))
            r.audit('forward_prediction_locked', dict(prediction_id=prediction_id,
                fixture_id=fid, referee_task_id=referee_task_id))
        return prediction_id

    def ingest_result(self, fixture_id, snapshot_id, native_id):
        r = self.runtime
        fid = str(UUID(str(fixture_id)))
        with r.transaction():
            final, provenance = verify_result_snapshot(r, fixture_id, snapshot_id, native_id)
            old = r.db.execute('SELECT * FROM lab_verified_results WHERE fixture_id=?', (fid,)).fetchone()
            if old:
                if (old['result_body'] != canonical(final)
                    or old['provenance'] != canonical(provenance)):
                    raise ValueError('result_provenance_conflict_requires_review')
                return final
            r.db.execute('INSERT INTO lab_verified_results VALUES(?,?,?,?,?,?)',
                         (fid, snapshot_id, native_id, canonical(final),
                          canonical(provenance), r.clock()))
            r.audit('verified_final_recorded', dict(fixture_id=fid,
                snapshot_id=snapshot_id, native_id=native_id))
        return final

    def grade(self, prediction_id):
        r = self.runtime
        with r.transaction():
            row = r.db.execute('''SELECT p.*,v.result_body FROM lab_locked_predictions p
                JOIN lab_verified_results v ON v.fixture_id=p.fixture_id
                WHERE p.prediction_id=?''',(prediction_id,)).fetchone()
            if not row:
                raise ValueError('locked_prediction_and_verified_final_required')
            existing = r.db.execute('SELECT * FROM lab_prediction_grades WHERE prediction_id=?',
                                    (prediction_id,)).fetchone()
            if existing:
                return dict(verdict=existing['verdict'], brier=existing['brier'],
                            log_loss=existing['log_loss'])
            result = json.loads(row['result_body'])
            probs = json.loads(row['probabilities'])
            outcome = 0 if result['home'] > result['away'] else 2 if result['away'] > result['home'] else 1
            brier = sum((p-(i==outcome))**2 for i,p in enumerate(probs))
            log_loss = -math.log(max(probs[outcome],1e-15))
            verdict = (settle_pick(json.loads(row['pick']),result)['status']
                       if row['pick'] else None)
            if verdict not in ('won','lost','push',None):
                raise ValueError('unsettleable_pick')
            r.db.execute('INSERT INTO lab_prediction_grades VALUES(?,?,?,?,?,?)',
                         (prediction_id,row['fixture_id'],verdict,log_loss,brier,r.clock()))
            r.audit('forward_prediction_graded', dict(prediction_id=prediction_id,
                fixture_id=row['fixture_id'], verdict=verdict))
        return dict(verdict=verdict, brier=brier, log_loss=log_loss)

    def summary(self):
        """Research-only summary; no inferred odds/CLV/ROI."""
        row = self.runtime.db.execute('''SELECT count(*) n, avg(brier) brier,
            avg(log_loss) log_loss FROM lab_prediction_grades''').fetchone()
        pending = self.runtime.db.execute('''SELECT count(*) FROM lab_locked_predictions p
            WHERE NOT EXISTS (SELECT 1 FROM lab_prediction_grades g
                              WHERE g.prediction_id=p.prediction_id)''').fetchone()[0]
        return dict(settled=row['n'], pending=pending,
                    brier=row['brier'], log_loss=row['log_loss'],
                    roi=None, clv=None, live_pilot=False)
