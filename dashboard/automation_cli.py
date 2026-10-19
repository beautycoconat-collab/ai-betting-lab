"""Manual, fail-closed entry point for local daily research and results.

No hosted credentials, cron, migrations, or real/virtual wager execution.
Only pre-approved, quota-accounted Queue workers may fetch from providers.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from dashboard.daily_orchestrator import DailyOrchestrator, atomic_write_public_json
from dashboard.daily_performance import forward_metrics


def execute(db_path, out_path, *, collect=False, max_source_jobs=5, days=7):
    from foundation.runtime import Runtime
    from dashboard.daily import run as daily_research
    from experts.result_scheduler import ResultScheduler
    from experts.research import approved
    from engine.adapters import ADAPTERS

    now = datetime.now(timezone.utc)
    runtime = Runtime(str(db_path), clock=lambda:now.isoformat())
    try:
        # The adapter registry and license review, not a hardcoded arbitrary
        # league list, define what may be requested. Currently the dashboard
        # can *predict* Bundesliga only; other leagues remain unsupported.
        if collect and 'openliga' in ADAPTERS and approved(runtime.queue.registry.get('openliga',{}), now):
            season = now.year if now.month >= 7 else now.year - 1
            runtime.queue.enqueue('openliga','collect',
                                  {'league':'bl1','season':str(season)},
                                  now=now.isoformat(),cycle=now.date().isoformat())
        orchestrator = DailyOrchestrator(runtime.db, clock=lambda:now)
        scheduler = ResultScheduler(runtime)
        plans = [row[0] for row in runtime.db.execute('''SELECT plan_id FROM lab_result_collection_plans
            WHERE eligible_at<=? ORDER BY eligible_at LIMIT 100''',(now.isoformat(),))]
        research_artifact = {}

        def research():
            nonlocal research_artifact
            research_artifact = daily_research(str(db_path), collect=False, now=now, days=days)
            return {'fixtures':research_artifact.get('fixtures',[]),
                    'status':'verified' if research_artifact.get('connection')=='verified_source_worker' else 'unverified'}

        outcome = orchestrator.run(source_worker=runtime.queue.work_one if collect else None,
                                   research_worker=research,
                                   result_scheduler=scheduler,
                                   result_plan_ids=plans, max_source_jobs=max_source_jobs, now=now)
        # Only complete runs can replace the public artifact. Failed/partial
        # runs preserve the previous dashboard snapshot (fail closed).
        if research_artifact and outcome['status'] == 'done':
            research_artifact['daily_automation'] = orchestrator.public_status()
            research_artifact['forward_performance'] = forward_metrics(runtime.db, now)
            research_artifact['daily_automation']['publication_status'] = outcome['status']
            research_artifact['daily_automation']['pilot_enabled'] = False
            atomic_write_public_json(out_path, research_artifact)
        return outcome
    finally:
        runtime.queue.close()


def main():
    parser = argparse.ArgumentParser(description='Manual local research; hosted cron disabled')
    parser.add_argument('--database',default='data/dashboard-live.sqlite')
    parser.add_argument('--out',default='public/data/dashboard.json')
    parser.add_argument('--collect',action='store_true')
    parser.add_argument('--max-source-jobs',type=int,default=5)
    parser.add_argument('--days',type=int,default=7)
    args = parser.parse_args()
    result = execute(args.database,args.out,collect=args.collect,
                     max_source_jobs=args.max_source_jobs,days=args.days)
    print(json.dumps(result,sort_keys=True))
    if result['status'] == 'partial':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
