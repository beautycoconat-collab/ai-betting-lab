"""Local, manually driven post-match outcome collection and learning scheduler.

Plan -> existing quota/lease-fenced v2 source Queue -> verify original raw bytes
-> immutable forward outcome journal -> graded locked predictions. No network is
triggered by this module, no live publication, wallet, scheduler activation, or
Supabase writes. The caller must separately run Queue.work_one with an approved
fetcher/worker and can reconcile repeatedly (idempotently).
"""
import json
from datetime import timedelta
from uuid import UUID

from betting_lab.domain import digest
from engine.adapters import ADAPTERS
from foundation.runtime import canonical
from .outcome_journal import OutcomeJournal
from .research import approved, aware
from .result_versions import VersionedResults

SCHEMA = '''
CREATE TABLE IF NOT EXISTS lab_result_collection_plans (
  plan_id TEXT PRIMARY KEY,
  fixture_id TEXT NOT NULL REFERENCES f_fixtures(id),
  source_id TEXT NOT NULL,
  params TEXT NOT NULL,
  native_id TEXT NOT NULL,
  cycle TEXT NOT NULL,
  eligible_at TEXT NOT NULL,
  source_job_id TEXT NOT NULL REFERENCES v2_jobs(id),
  planned_at TEXT NOT NULL,
  UNIQUE(fixture_id,source_id,params,native_id,cycle)
);
'''


class ResultScheduler:
    """Offline trusted-process coordinator; explicitly NOT a hosted worker."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.journal = OutcomeJournal(runtime)
        self.versions = VersionedResults(runtime)
        runtime.db.executescript(SCHEMA)
        for action in ('UPDATE', 'DELETE'):
            runtime.db.execute(f'''CREATE TRIGGER IF NOT EXISTS lab_result_collection_plans_{action}
                BEFORE {action} ON lab_result_collection_plans
                BEGIN SELECT RAISE(ABORT,'append_only'); END''')
        runtime.db.commit()

    def plan(self, fixture_id, source_id, params, native_id, *, cycle=None,
             minimum_after_kickoff_minutes=120):
        """Register one immutable polling plan for a known *locked* fixture.

        Queuing never fetches data. A fixed daily cycle enables a later fresh
        retry if today's snapshot is stale or the provider hasn't published a
        final. `eligible_at` guarantees that requests aren't made too early.
        """
        r = self.runtime
        fid = str(UUID(str(fixture_id)))
        if type(minimum_after_kickoff_minutes) is not int or not 90 <= minimum_after_kickoff_minutes <= 1440:
            raise ValueError('invalid_result_wait')
        if not isinstance(native_id, str) or not native_id or len(native_id) > 240:
            raise ValueError('native_id_required')
        if not isinstance(params, dict) or not params or any(not isinstance(k, str) for k in params):
            raise ValueError('invalid_source_params')
        try:
            params_json = canonical(params)
            if len(params_json) > 4096 or not isinstance(json.loads(params_json), dict):
                raise ValueError('invalid_source_params')
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError('invalid_source_params') from exc
        now = aware(r.clock())
        fixture = r.db.execute('SELECT * FROM f_fixtures WHERE id=?',(fid,)).fetchone()
        if not fixture or fixture['target'] != 'regulation90':
            raise ValueError('registered_regulation_fixture_required')
        locked = r.db.execute('''SELECT COUNT(*) FROM lab_locked_predictions
                                  WHERE fixture_id=?''',(fid,)).fetchone()[0]
        if not locked:
            raise ValueError('pre_kickoff_locked_prediction_required')
        kickoff = aware(fixture['kickoff_at'])
        eligible = kickoff + timedelta(minutes=minimum_after_kickoff_minutes)
        # Use an actual calendar day to identify one poll. No backdating or
        # arbitrarily creating a later polling cycle in the past.
        day = now.date().isoformat() if cycle is None else cycle
        from datetime import date
        if type(day) is not str or date.fromisoformat(day).isoformat() != day or day != now.date().isoformat():
            raise ValueError('cycle_must_equal_current_day')
        policy = r.queue.registry.get(source_id, {})
        if (source_id not in ADAPTERS or not approved(policy, now)
            or not approved(policy, max(now, eligible))):
            raise ValueError('result_source_policy_unapproved')
        try:
            url = ADAPTERS[source_id].url('collect', params)
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise ValueError('invalid_adapter_parameters') from exc
        if not url.startswith('https://'):
            raise ValueError('https_collect_url_required')
        # A second planning attempt must not change the source job or evidence.
        plan_id = digest([fid,source_id,params_json,native_id,day])
        old = r.db.execute('SELECT * FROM lab_result_collection_plans WHERE plan_id=?',(plan_id,)).fetchone()
        if old:
            if old['eligible_at'] != eligible.isoformat():
                raise ValueError('immutable_result_plan_conflict')
            return dict(old)
        # Do not fetch early, and do not enqueue a job whose not_before is now
        # if 120 minutes have not elapsed. Each source request is still subject
        # to the existing worker's per-source request quotas and permissions.
        due = max(now, eligible)
        job_id = r.queue.enqueue(source_id,'collect',params,now=due.isoformat(),cycle=day)
        with r.transaction():
            r.db.execute('''INSERT INTO lab_result_collection_plans VALUES(?,?,?,?,?,?,?,?,?)''',
                (plan_id,fid,source_id,params_json,native_id,day,eligible.isoformat(),job_id,now.isoformat()))
            r.audit('result_collection_planned',{'plan_id':plan_id,'fixture_id':fid,
                    'source_id':source_id,'job_id':job_id,'eligible_at':eligible.isoformat()})
        return dict(r.db.execute('SELECT * FROM lab_result_collection_plans WHERE plan_id=?',(plan_id,)).fetchone())

    def reconcile(self, plan_id):
        """Consume only a finished source job and a fresh verified snapshot.

        If a provider hasn't finalized, return `waiting_for_final` without
        grading. A new daily cycle can request a new snapshot later. A changed
        official score/provenance raises a review requirement; existing results
        are never silently edited.
        """
        r = self.runtime
        plan = r.db.execute('SELECT * FROM lab_result_collection_plans WHERE plan_id=?',(plan_id,)).fetchone()
        if not plan:
            raise ValueError('unknown_result_plan')
        job = r.db.execute('SELECT source,kind,status,params FROM v2_jobs WHERE id=?',
                           (plan['source_job_id'],)).fetchone()
        if not job or job['source'] != plan['source_id'] or job['kind'] != 'collect' or canonical(json.loads(job['params'])) != plan['params']:
            raise ValueError('result_source_job_identity_mismatch')
        if job['status'] != 'done':
            return dict(status='source_'+job['status'],plan_id=plan_id,graded=0)
        snapshots = r.db.execute('''SELECT DISTINCT s.id,s.observed_at FROM v2_snapshots s
            LEFT JOIN v2_job_snapshots link ON link.snapshot_id=s.id
            WHERE (s.job_id=? OR link.job_id=?) AND s.source=?''',
            (plan['source_job_id'],plan['source_job_id'],plan['source_id'])).fetchall()
        if len(snapshots) != 1:
            return dict(status='snapshot_missing_or_ambiguous',plan_id=plan_id,graded=0)
        snapshot = snapshots[0]
        # A same-URL cached pre-final observation cannot attest a full-time
        # result, even though the new source job itself is marked "done".
        if aware(snapshot['observed_at']) < aware(plan['eligible_at']):
            return dict(status='stale_snapshot_repoll_next_cycle',plan_id=plan_id,graded=0)
        try:
            revision = self.versions.observe(plan['fixture_id'],snapshot['id'],plan['native_id'])
            if revision['status'] != 'approved':
                return dict(status='manual_review_required',plan_id=plan_id,graded=0,
                            result_version_id=revision['version_id'])
            final = self.journal.ingest_result(plan['fixture_id'],snapshot['id'],plan['native_id'])
        except ValueError as exc:
            reason = str(exc)
            if reason in ('official_final_not_available','native_match_missing_or_ambiguous'):
                return dict(status='waiting_for_final',plan_id=plan_id,graded=0,reason=reason)
            if reason == 'result_provenance_conflict_requires_review':
                # Preserve the legacy first-result ledger. The new append-only
                # revision service is authoritative for explicitly reviewed
                # corrections and fresh corroborating observations.
                final = revision['final']
            else:
                raise
        predictions = r.db.execute('SELECT prediction_id FROM lab_locked_predictions WHERE fixture_id=? ORDER BY prediction_id',
                                   (plan['fixture_id'],)).fetchall()
        graded = [self.journal.grade(x['prediction_id']) for x in predictions]
        versioned_grades = [self.versions.grade(x['prediction_id']) for x in predictions]
        return dict(status='graded', plan_id=plan_id, graded=len(graded),
                    final=final, performance=self.journal.summary(),
                    result_version_id=revision['version_id'],versioned_grades=len(versioned_grades),
                    current_performance={str(d):self.versions.performance(d) for d in (7,30,90,180)})

    def performance_windows(self, days=(7,30,90,180)):
        """Grade-time research metrics only; no inferred ROI, CLV or coverage.

        `eligible_predictions` means only locked forward predictions, never all
        fixtures or all candidate model predictions.
        """
        now = aware(self.runtime.clock())
        out = {}
        for day in days:
            report = self.versions.performance(day)
            n = report['graded_predictions']
            out[str(day)] = report | {
                'pending_predictions':report['locked_predictions']-n,
                'sample_warning':'small_sample' if n<30 else None}
        return {'schema_version':'1.0','as_of':now.isoformat(),'windows':out,
                'live_pilot':False,'scope':'local_locked_predictions_only'}
