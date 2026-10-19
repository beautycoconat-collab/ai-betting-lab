"""Supabase durable collection job queue. No network or schema changes."""
import hashlib
import json
from datetime import date
from uuid import uuid4
from dashboard.hosted_source_gate import approved

FIELDS = ("source_id","status","license","permission_url","review_expires",
          "max_daily","min_interval_seconds")
POLICY_SQL = ("SELECT "+",".join(FIELDS)+" FROM lab.source_access_policies "
              "WHERE source_id=%s ORDER BY revision DESC LIMIT 1")


def enqueue(conn, source, kind, params, cycle):
    if kind not in ("collect","discover") or not isinstance(params,dict):
        raise ValueError("invalid_job")
    date.fromisoformat(cycle)
    key=hashlib.sha256(json.dumps([source,kind,params,cycle],sort_keys=True).encode()).hexdigest()
    with conn.transaction():
        row=conn.execute(POLICY_SQL,(source,)).fetchone()
        if not approved(dict(zip(FIELDS,row)) if row else None):
            raise ValueError("hosted_source_not_approved")
        inserted=conn.execute(
            "INSERT INTO lab.collection_jobs(source_id,kind,parameters,dedupe_key) "
            "VALUES (%s,%s,%s::jsonb,%s) ON CONFLICT (dedupe_key) DO NOTHING RETURNING id",
            (source,kind,json.dumps(params),key)).fetchone()
    return {"dedupe_key":key,"created":inserted is not None}


def claim(conn):
    with conn.transaction():
        row=conn.execute(
            "SELECT id,source_id FROM lab.collection_jobs WHERE status='pending' "
            "AND not_before&lt;=clock_timestamp() ORDER BY not_before,id "
            "FOR UPDATE SKIP LOCKED LIMIT 1").fetchone()
        if not row:
            return None
        job_id,source=row
        policy=conn.execute(POLICY_SQL,(source,)).fetchone()
        if not approved(dict(zip(FIELDS,policy)) if policy else None):
            conn.execute("UPDATE lab.collection_jobs SET status='blocked',"
                         "last_error='source_review_missing' WHERE id=%s",(job_id,))
            return {"status":"blocked"}
        token=uuid4()
        conn.execute("UPDATE lab.collection_jobs SET status='running',attempts=attempts+1,"
                     "lease_token=%s,lease_until=clock_timestamp()+interval '5 minutes' "
                     "WHERE id=%s",(token,job_id))
        return {"id":str(job_id),"lease_token":str(token),"source_id":source}


def finish(conn, job_id, token, status):
    if status not in ("done","failed","blocked"):
        raise ValueError("invalid_status")
    with conn.transaction():
        row=conn.execute(
            "UPDATE lab.collection_jobs SET status=%s,lease_token=NULL,lease_until=NULL "
            "WHERE id=%s AND lease_token=%s AND status='running' "
            "AND lease_until&gt;clock_timestamp() RETURNING id",
            (status,job_id,token)).fetchone()
        return row is not None
