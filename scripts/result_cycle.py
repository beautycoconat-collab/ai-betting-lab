"""Manual/offline post-match result cycle CLI (NO fetch, credentials or deployment).

Examples:
 python -m scripts.result_cycle --db local.sqlite --mode plan --manifest result_plan.json
 python -m scripts.result_cycle --db local.sqlite --mode reconcile
 python -m scripts.result_cycle --db local.sqlite --mode report

Only `plan` creates v2 source queue jobs. A separately permissioned, quota-
controlled source worker must run to populate them; this command never performs
HTTP or schedules itself. It must NOT run from a GitHub runner with ephemeral
SQLite storage and be mistaken for a persistent hosted service.
"""
import argparse
import json
from pathlib import Path

from experts.result_scheduler import ResultScheduler
from foundation.runtime import Runtime


def cycle(runtime, mode, manifest=None):
    scheduler=ResultScheduler(runtime)
    if mode=='plan':
        if manifest is None or not isinstance(manifest,list) or len(manifest)>500:
            raise ValueError('plan_manifest_required_or_too_large')
        if any(not isinstance(x,dict) or set(x) - {'fixture_id','source_id','params','native_id'}
               or set(x)!={'fixture_id','source_id','params','native_id'} for x in manifest):
            raise ValueError('invalid_plan_manifest_entry')
        return {'schema_version':'1.0', 'mode':mode,
                'plans':[{'fixture_id':x['fixture_id'],
                          'plan_id':scheduler.plan(**x)['plan_id']} for x in manifest],
                'live_fetch':False, 'pilot_enabled':False}
    if mode=='reconcile':
        plans=runtime.db.execute('SELECT plan_id FROM lab_result_collection_plans ORDER BY plan_id').fetchall()
        result=[]
        for x in plans:
            try:
                result.append(scheduler.reconcile(x['plan_id']))
            except ValueError as exc:
                result.append({'plan_id':x['plan_id'],'status':'blocked',
                               'reason':str(exc),'graded':0})
        return {'schema_version':'1.0','mode':mode,'results':result,
                'live_fetch':False, 'pilot_enabled':False}
    if mode=='report':
        return {'schema_version':'1.0','mode':mode,'performance':scheduler.performance_windows(),
                'live_fetch':False,'pilot_enabled':False}
    raise ValueError('unknown_cycle_mode')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True,help='existing trusted local SQLite database')
    parser.add_argument('--mode',required=True,choices=['plan','reconcile','report'])
    parser.add_argument('--manifest',help='JSON list of provider+fixture mappings, used only with plan')
    args=parser.parse_args(argv)
    if args.mode=='plan' and not args.manifest:
        parser.error('--manifest is required with --mode plan')
    if args.mode!='plan' and args.manifest:
        parser.error('--manifest is only permitted with --mode plan')
    db=Path(args.db)
    if not db.is_file():
        parser.error('database must exist: refusing to fabricate an empty forward history')
    try:
        payload=None
        if args.manifest:
            path=Path(args.manifest)
            if not path.is_file() or path.stat().st_size>128_000:
                raise ValueError('manifest_missing_or_too_large')
            payload=json.loads(path.read_text(encoding='utf8'))
        runtime=Runtime(db)
        try:
            result=cycle(runtime,args.mode,payload)
        finally:
            runtime.close()
        print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    except (ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__=='__main__':
    main()
