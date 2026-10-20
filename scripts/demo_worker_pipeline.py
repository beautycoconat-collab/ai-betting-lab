"""Offline synthetic-evidence demo; never a real pre-match or betting signal.

Run: python -m scripts.demo_worker_pipeline --out reports/experts/worker_pipeline_demo.json
"""
import argparse
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from foundation.runtime import Runtime
from experts.football import ScoreEngine, Synthesizer
from experts.worker_pipeline import ResearchWorkerPipeline, ROLES


def demo(dataset='reports/phase2/bundesliga/dataset.json'):
    rows = json.loads(Path(dataset).read_text())
    engine = ScoreEngine().fit(rows, '2025-01-01T00:00:00+00:00', 'regulation90')
    validation = [r for r in rows if '2025-01-01' <= r['date'] < '2025-03-01']
    synth = Synthesizer().fit(engine.models, validation)
    r = next(x for x in rows if x['date'] >= '2025-03-01')
    # Historic exact kickoff unavailable; these fixture/evidence timestamps are
    # explicitly synthetic and MUST NOT be interpreted as historical observations.
    kickoff = datetime.fromisoformat(r['date']+'T18:00:00+00:00')
    at = kickoff-timedelta(hours=4)
    observed = at-timedelta(hours=1)
    fid = UUID(int=7891)
    fixture = dict(schema_version='1.0', id=str(fid), home=r['home'], away=r['away'],
        competition='synthetic_demo', season='synthetic_time', neutral=r['neutral'],
        target='regulation90', kickoff_at=kickoff.isoformat())
    claim = dict(schema_version='1.0', id='mock-lineup', fixture_id=str(fid),
        source_id='synthetic_demo', snapshot_id='mock-snapshot',
        source_url='https://example.invalid/mock-snapshot',
        observed_at=observed.isoformat(),
        published_at=(observed-timedelta(minutes=15)).isoformat(),
        quality='verified', target='regulation90', topic='lineup',
        subject=r['home'], value='synthetic test-only lineup')
    registry = {'synthetic_demo': dict(status='approved', reviewed_at='2024-01-01',
        review_expires='2027-12-31', license='synthetic-test-only',
        terms_url='https://example.invalid/test-license')}
    snapshots = {'mock-snapshot': dict(source_id='synthetic_demo',
        source_url=claim['source_url'], observed_at=claim['observed_at'])}
    with tempfile.TemporaryDirectory() as folder:
        runtime = Runtime(Path(folder)/'demo.db', clock=lambda: '2026-10-16T12:00:00+00:00')
        try:
            pipeline = ResearchWorkerPipeline(runtime, engine, synth, registry)
            tasks = pipeline.plan(fixture, at, [claim], snapshots, mode='retrospective')
            status = {}
            for stage in ROLES:
                status[stage] = pipeline.dispatcher.work_one('demo-worker', ROLES[stage])['status']
            row = runtime.db.execute('SELECT body FROM expert_task_outputs WHERE task_id=?',
                                     (tasks['referee'],)).fetchone()
            verdict = json.loads(row[0])['data']
            return dict(mode='synthetic_evidence_retrospective_models',
                source_data='306 archived Bundesliga results; NOT kickoff-time verified',
                evidence='synthetic, not a real football news/lineup source',
                tasks=status, audit_chain_valid=runtime.verify_audit(),
                publishing_enabled=verdict['publishing_enabled'],
                review=verdict['verdict'], rounds=len(verdict['review_history']),
                no_portfolio_or_bets=True)
        finally:
            runtime.close()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',default='reports/experts/worker_pipeline_demo.json')
    a=p.parse_args()
    out=demo()
    path=Path(a.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':
    main()
