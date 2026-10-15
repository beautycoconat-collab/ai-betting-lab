"""Actual SQL usage plus explicitly sourced account-wide usage. Fail closed."""
from datetime import datetime, timezone, timedelta
import math

LIMITS = {'database_bytes':400_000_000, 'storage_bytes':800_000_000,
          'egress_bytes':4_000_000_000, 'connection_ratio':0.75}

def decision(measurement, now=None):
    now = now or datetime.now(timezone.utc)
    reasons=[]
    try:
        timestamp=datetime.fromisoformat(measurement['observed_at'])
        if timestamp.tzinfo is None or not timedelta(0) <= now-timestamp <= timedelta(minutes=15):
            reasons.append('stale_or_future_measurement')
    except (KeyError,TypeError,ValueError):
        reasons.append('missing_measurement_time')
    if measurement.get('plan') != 'free' or measurement.get('billing_scope') != 'organization':
        reasons.append('free_organization_usage_unverified')
    for key,limit in LIMITS.items():
        value=measurement.get(key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
            reasons.append('missing_'+key)
        elif value>=limit:
            reasons.append('limit_'+key)
    return {'allowed':not reasons,'action':'proceed' if not reasons else 'defer','reasons':reasons,
            'automatic_upgrade':False}

def collect(db):
    size,used,maximum=db.execute("select pg_database_size(current_database()),(select count(*) from pg_stat_activity),current_setting('max_connections')::int").fetchone()
    # This is live database usage, not an estimate from the local ZIP.
    result={'observed_at':datetime.now(timezone.utc).isoformat(),'database_bytes':size,
            'connection_ratio':used/maximum,'storage_bytes':None,'egress_bytes':None,
            'plan':None,'billing_scope':None,'source':'live_postgresql'}
    if db.execute("select to_regclass('storage.objects')").fetchone()[0]:
        row=db.execute("select coalesce(sum(case when metadata->>'size' ~ '^[0-9]+$' then (metadata->>'size')::numeric else 0 end),0),count(*) filter(where metadata->>'size' is null or metadata->>'size' !~ '^[0-9]+$') from storage.objects").fetchone()
        if row[1]==0: result['storage_bytes']=int(row[0])
    # Organization egress and billing plan are NOT inferable from project SQL.
    # Missing observations intentionally prevent autonomous data-collection work.
    return result

def guarded_call(measurement, operation, now=None):
    verdict=decision(measurement,now)
    if not verdict['allowed']:
        return verdict
    return operation()
