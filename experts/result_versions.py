"""Append-only local result revisions and forward-prediction regrading.

Snapshot verification is reused verbatim. A corrected score is quarantined
until a fixture-bound scientific-referee run records a review. This is a
trusted-process SQLite service, not hosted authentication or wallet execution.
"""
import json
import math
from typing import Literal
from pydantic import Field
from foundation.contracts import Contract
from foundation.runtime import canonical
from betting_lab.domain import digest
from .outcome_journal import OutcomeJournal, verify_result_snapshot
from .research import aware


class ResultReview(Contract):
    version_id: str = Field(min_length=1)
    reviewer_run_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=8, max_length=200)
    decision: Literal['approved', 'rejected']
    reason: str = Field(min_length=12, max_length=2000)
    evidence_snapshot_ids: list[str] = Field(min_length=1)
    numeric_override: None = None


SCHEMA = '''
CREATE TABLE IF NOT EXISTS lab_result_versions (
 id TEXT PRIMARY KEY, fixture_id TEXT NOT NULL REFERENCES f_fixtures(id),
 snapshot_id TEXT NOT NULL REFERENCES v2_snapshots(id), native_id TEXT NOT NULL,
 previous_id TEXT REFERENCES lab_result_versions(id), result_body TEXT NOT NULL,
 provenance TEXT NOT NULL, observed_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
 UNIQUE(fixture_id,snapshot_id,native_id)
);
CREATE TABLE IF NOT EXISTS lab_result_version_decisions (
 seq INTEGER PRIMARY KEY, request_key TEXT NOT NULL UNIQUE, request_body TEXT NOT NULL,
 version_id TEXT NOT NULL REFERENCES lab_result_versions(id),
 reviewer_run_id TEXT REFERENCES f_runs(id), status TEXT NOT NULL
 CHECK(status IN ('approved','rejected','conflicting')), reason TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lab_prediction_grade_versions (
 prediction_id TEXT NOT NULL REFERENCES lab_locked_predictions(prediction_id),
 result_version_id TEXT NOT NULL REFERENCES lab_result_versions(id),
 brier REAL NOT NULL CHECK(brier>=0 AND brier<=2.00000001),
 log_loss REAL NOT NULL CHECK(log_loss>=0), recorded_at TEXT NOT NULL,
 PRIMARY KEY(prediction_id,result_version_id)
);
CREATE INDEX IF NOT EXISTS lab_result_version_fixture ON lab_result_versions(fixture_id,observed_at);
CREATE INDEX IF NOT EXISTS lab_result_decision_version ON lab_result_version_decisions(version_id,seq);
'''


class VersionedResults:
    def __init__(self, runtime):
        self.runtime = runtime
        self.journal = OutcomeJournal(runtime)
        runtime.db.executescript(SCHEMA)
        for table in ('lab_result_versions', 'lab_result_version_decisions', 'lab_prediction_grade_versions'):
            for action in ('UPDATE', 'DELETE'):
                runtime.db.execute(f'''CREATE TRIGGER IF NOT EXISTS {table}_{action} BEFORE {action} ON {table}
                    BEGIN SELECT RAISE(ABORT,'append_only'); END''')
        runtime.db.commit()

    def current(self, fixture_id):
        # A later observation cannot silently supersede an approved correction.
        row = self.runtime.db.execute('''SELECT v.* FROM lab_result_version_decisions d
            JOIN lab_result_versions v ON v.id=d.version_id
            WHERE v.fixture_id=? AND d.status='approved' ORDER BY d.seq DESC LIMIT 1''',
            (str(fixture_id),)).fetchone()
        return dict(row) if row else None

    def observe(self, fixture_id, snapshot_id, native_id):
        r = self.runtime
        with r.transaction():
            final, provenance = verify_result_snapshot(r, fixture_id, snapshot_id, native_id)
            fid = str(fixture_id)
            key = digest(['result-v1', fid, snapshot_id, native_id])
            old = r.db.execute('SELECT * FROM lab_result_versions WHERE id=?', (key,)).fetchone()
            if old:
                if old['result_body'] != canonical(final) or old['provenance'] != canonical(provenance):
                    raise ValueError('immutable_result_revision_conflict')
                status = r.db.execute('SELECT status FROM lab_result_version_decisions WHERE version_id=? ORDER BY seq DESC LIMIT 1', (key,)).fetchone()[0]
                return dict(version_id=key, status=status, final=final)
            current = self.current(fid)
            r.db.execute('INSERT INTO lab_result_versions VALUES(?,?,?,?,?,?,?,?,?)',
                (key,fid,snapshot_id,native_id,current['id'] if current else None,
                 canonical(final),canonical(provenance),provenance['observed_at'],r.clock()))
            # Same score from a new snapshot is corroboration, not a correction.
            # A stale observation or a different score always requires review.
            clean = not current or (current['result_body'] == canonical(final)
                and aware(provenance['observed_at']) >= aware(current['observed_at']))
            status = 'approved' if clean else 'conflicting'
            r.db.execute('''INSERT INTO lab_result_version_decisions
                (request_key,request_body,version_id,status,reason,created_at) VALUES(?,?,?,?,?,?)''',
                ('observe:'+key,canonical(provenance),key,status,
                 'verified_observed_final' if clean else 'changed_or_older_result_requires_review',r.clock()))
            r.audit('result_revision_observed',dict(version_id=key,fixture_id=fid,status=status))
            return dict(version_id=key,status=status,final=final)

    def review(self, value):
        request = ResultReview.model_validate(value)
        body = canonical(request.model_dump(mode='json'))
        r = self.runtime
        with r.transaction():
            old = r.db.execute('SELECT * FROM lab_result_version_decisions WHERE request_key=?', (request.idempotency_key,)).fetchone()
            if old:
                if old['request_body'] != body:
                    raise ValueError('review_idempotency_conflict')
                return old['status']
            version = r.db.execute('SELECT * FROM lab_result_versions WHERE id=?', (request.version_id,)).fetchone()
            run = r.db.execute('SELECT * FROM f_runs WHERE id=?', (request.reviewer_run_id,)).fetchone()
            if not version or not run or run['role'] != 'scientific_referee' or run['fixture_id'] != version['fixture_id']:
                raise ValueError('fixture_bound_referee_required')
            latest = r.db.execute('SELECT status FROM lab_result_version_decisions WHERE version_id=? ORDER BY seq DESC LIMIT 1', (request.version_id,)).fetchone()
            if latest[0] != 'conflicting':
                raise ValueError('result_review_already_decided')
            if version['snapshot_id'] not in request.evidence_snapshot_ids:
                raise ValueError('candidate_snapshot_evidence_required')
            for sid in set(request.evidence_snapshot_ids):
                # Every cited snapshot must independently match this fixture.
                _, provenance = verify_result_snapshot(r, version['fixture_id'], sid, version['native_id'])
                if aware(provenance['observed_at']) > aware(run['as_of']):
                    raise ValueError('future_review_evidence')
            r.db.execute('''INSERT INTO lab_result_version_decisions
                (request_key,request_body,version_id,reviewer_run_id,status,reason,created_at)
                VALUES(?,?,?,?,?,?,?)''', (request.idempotency_key,body,request.version_id,
                    request.reviewer_run_id,request.decision,request.reason,r.clock()))
            r.audit('result_revision_reviewed', request.model_dump(mode='json'))
            return request.decision

    def grade(self, prediction_id):
        r = self.runtime
        with r.transaction():
            p = r.db.execute('SELECT * FROM lab_locked_predictions WHERE prediction_id=?', (prediction_id,)).fetchone()
            current = self.current(p['fixture_id']) if p else None
            if not current:
                raise ValueError('locked_prediction_and_approved_result_required')
            old = r.db.execute('SELECT * FROM lab_prediction_grade_versions WHERE prediction_id=? AND result_version_id=?', (prediction_id,current['id'])).fetchone()
            if old:
                return dict(old)
            final = json.loads(current['result_body'])
            probs = json.loads(p['probabilities'])
            outcome = 0 if final['home']>final['away'] else 2 if final['home']<final['away'] else 1
            brier = sum((prob-(i==outcome))**2 for i,prob in enumerate(probs))
            loss = -math.log(max(probs[outcome],1e-15))
            r.db.execute('INSERT INTO lab_prediction_grade_versions VALUES(?,?,?,?,?)',
                (prediction_id,current['id'],brier,loss,r.clock()))
            r.audit('prediction_revision_graded',dict(prediction_id=prediction_id,result_version_id=current['id']))
            return dict(r.db.execute('SELECT * FROM lab_prediction_grade_versions WHERE prediction_id=? AND result_version_id=?', (prediction_id,current['id'])).fetchone())

    def performance(self, days=7):
        """Prediction-capture window; latest approved result only, no duplicates.

        Coverage denominator is explicitly locked predictions. Unrecorded
        candidates/abstentions and monetary/closing-price evidence are unknown.
        """
        from datetime import timedelta
        if type(days) is not int or not 1 <= days <= 3650:
            raise ValueError('invalid_performance_window')
        now = aware(self.runtime.clock()); since = now-timedelta(days=days)
        eligible = [dict(p) for p in self.runtime.db.execute('SELECT * FROM lab_locked_predictions')
            if since <= aware(p['captured_at']) <= now]
        rows = []
        for p in eligible:
            current = self.current(p['fixture_id'])
            if not current: continue
            grade = self.runtime.db.execute('''SELECT * FROM lab_prediction_grade_versions
                WHERE prediction_id=? AND result_version_id=?''',(p['prediction_id'],current['id'])).fetchone()
            if not grade or aware(grade['recorded_at']) > now: continue
            final = json.loads(current['result_body'])
            outcome = 0 if final['home']>final['away'] else 2 if final['home']<final['away'] else 1
            rows.append((p,dict(grade),outcome))
        calibration = []
        for lower in range(10):
            events = [(prob,int(i==outcome)) for p,g,outcome in rows
                for i,prob in enumerate(json.loads(p['probabilities']))
                if min(int(prob*10),9)==lower]
            calibration.append(dict(lower=lower/10,upper=(lower+1)/10,count=len(events),
                predicted=sum(p for p,y in events)/len(events) if events else None,
                observed=sum(y for p,y in events)/len(events) if events else None))
        by_model = {}
        for p,g,outcome in rows:
            by_model.setdefault(p['model_hash'],[]).append((p,g))
        shared = set.intersection(*[{p['fixture_id'] for p,g in group} for group in by_model.values()]) if by_model else set()
        comparison = {}
        for model,group in by_model.items():
            matched = [g for p,g in group if p['fixture_id'] in shared]
            # Multiple predictions of one model/fixture require a declared
            # selection policy; do not silently weight that match twice.
            fids = [p['fixture_id'] for p,g in group if p['fixture_id'] in shared]
            comparison[model] = dict(status='insufficient_data' if len(fids)!=len(set(fids)) else 'evaluated',
                paired_fixtures=len(shared), log_loss=sum(g['log_loss'] for g in matched)/len(matched) if matched and len(fids)==len(set(fids)) else None)
        n=len(rows)
        return dict(schema_version='1.0',days=days,as_of=now.isoformat(),mode='locked_forward_only',
            locked_predictions=len(eligible),graded_predictions=n,
            resolved_fraction=n/len(eligible) if eligible else None,
            coverage=None,abstain_rate=None,
            unavailable_reason='all_candidate_fixtures_and_abstentions_not_recorded',
            brier=sum(g['brier'] for p,g,y in rows)/n if n else None,
            log_loss=sum(g['log_loss'] for p,g,y in rows)/n if n else None,
            calibration=calibration,model_comparison=comparison,
            champion_promotion=False,roi=None,clv=None,live_pilot=False)
