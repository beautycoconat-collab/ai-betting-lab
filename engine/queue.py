"""Persistent source-isolated queue; uses unchanged phase-1 request budget ledger."""
import json,uuid,zlib
from pathlib import Path
from datetime import datetime,timedelta,timezone
from urllib.error import HTTPError,URLError
from betting_lab.store import Store,StopCollection
from betting_lab.domain import digest,utcnow
from betting_lab.collector import fetch
from .adapters import ADAPTERS

SCHEMA='''
CREATE TABLE IF NOT EXISTS v2_jobs(id TEXT PRIMARY KEY,source TEXT NOT NULL,kind TEXT NOT NULL,params TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,not_before TEXT NOT NULL,lease_until TEXT,lease_token TEXT,last_error TEXT);
CREATE TABLE IF NOT EXISTS v2_snapshots(id TEXT PRIMARY KEY,job_id TEXT NOT NULL,source TEXT NOT NULL,url TEXT NOT NULL,observed_at TEXT NOT NULL,sha256 TEXT NOT NULL,body BLOB NOT NULL,headers TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS v2_results(snapshot_id TEXT NOT NULL,source TEXT NOT NULL,native_id TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(snapshot_id,native_id));
CREATE TABLE IF NOT EXISTS v2_catalog(snapshot_id TEXT NOT NULL,source TEXT NOT NULL,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS v2_rejected(snapshot_id TEXT NOT NULL,row_index INTEGER NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(snapshot_id,row_index));
CREATE TABLE IF NOT EXISTS v2_health(source TEXT PRIMARY KEY,successes INTEGER NOT NULL DEFAULT 0,failures INTEGER NOT NULL DEFAULT 0,consecutive_failures INTEGER NOT NULL DEFAULT 0,last_success TEXT,last_error TEXT);
'''

class Queue:
    def __init__(self,path,registry=None):
        self.store=Store(path);self.db=self.store.db;self.db.executescript(SCHEMA)
        if registry is None:
            from .bootstrap import merge_budget
            merge_budget(self.db)
        self.registry=registry or json.loads((Path(__file__).resolve().parents[1]/'config/source_registry_v2.json').read_text())
    def enqueue(self,source,kind,params,now=None):
        if source not in self.registry:raise ValueError('unknown_source')
        if kind not in ('discover','collect'):raise ValueError('unknown_job_kind')
        key=digest([source,kind,params]);now=now or utcnow()
        with self.db:self.db.execute('INSERT OR IGNORE INTO v2_jobs(id,source,kind,params,not_before) VALUES(?,?,?,?,?)',(key,source,kind,json.dumps(params,sort_keys=True),now))
        return key
    def claim(self,now):
        until=(datetime.fromisoformat(now)+timedelta(minutes=5)).isoformat();token=str(uuid.uuid4())
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.db.execute("SELECT * FROM v2_jobs WHERE (status='pending' AND not_before<=?) OR (status='running' AND lease_until<?) ORDER BY not_before,id LIMIT 1",(now,now)).fetchone()
            if row:self.db.execute("UPDATE v2_jobs SET status='running',lease_until=?,lease_token=? WHERE id=?",(until,token,row['id']))
            self.db.commit()
            return (dict(row)|{'lease_token':token}) if row else None
        except Exception:self.db.rollback();raise
    def finish(self,j,status,reason=None,when=None,at=None):
        at=at or utcnow()
        with self.db:self.db.execute('UPDATE v2_jobs SET status=?,last_error=?,not_before=coalesce(?,not_before),lease_until=NULL,lease_token=NULL WHERE id=? AND lease_token=? AND lease_until>?',(status,reason,when,j['id'],j['lease_token'],at))
    def defer_time(self,source,policy,now):
        t=datetime.fromisoformat(now);candidates=[t+timedelta(minutes=5)]
        req=[datetime.fromisoformat(r[0]) for r in self.db.execute('SELECT at FROM requests WHERE source=? ORDER BY at',(source,))]
        if req:candidates.append(req[-1]+timedelta(seconds=policy['min_interval_seconds']+1))
        for days,limit in [(1,policy['requests_per_24h']),(31,policy['requests_per_31d'])]:
            window=[x for x in req if x>t-timedelta(days=days)]
            if len(window)>=limit:candidates.append(window[len(window)-limit]+timedelta(days=days,seconds=1))
        r=self.db.execute('SELECT until_at FROM cooldowns WHERE source=?',(source,)).fetchone()
        if r:candidates.append(datetime.fromisoformat(r[0]))
        return max(candidates).isoformat()
    def health(self,source,success,now,reason=None):
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO v2_health(source) VALUES(?)',(source,))
            if success:self.db.execute('UPDATE v2_health SET successes=successes+1,consecutive_failures=0,last_success=?,last_error=NULL WHERE source=?',(now,source))
            else:self.db.execute('UPDATE v2_health SET failures=failures+1,consecutive_failures=consecutive_failures+1,last_error=? WHERE source=?',(reason,source))
    def work_one(self,fetcher=fetch,clock=utcnow):
        now=clock();j=self.claim(now)
        if not j:return None
        source=j['source'];policy=self.registry[source];result={'job_id':j['id'],'source':source}
        try:
            if policy['status']!='approved':raise StopCollection('source_not_approved')
            if now[:10]>policy['review_expires']:raise StopCollection('source_review_expired')
            adapter=ADAPTERS[source];p=json.loads(j['params']);url=adapter.url(j['kind'],p)
            cached=self.db.execute('SELECT id,observed_at FROM v2_snapshots WHERE source=? AND url=? AND (EXISTS(SELECT 1 FROM v2_results WHERE snapshot_id=v2_snapshots.id) OR EXISTS(SELECT 1 FROM v2_catalog WHERE snapshot_id=v2_snapshots.id)) ORDER BY observed_at DESC LIMIT 1',(source,url)).fetchone()
            if cached and 0<=(datetime.fromisoformat(now)-datetime.fromisoformat(cached['observed_at'])).total_seconds()<policy.get('cache_seconds',21600):
                self.finish(j,'done',at=now)
                return result|{'status':'cached','snapshot_id':cached['id'],'network_requests':0}
            self.store.reserve(policy.get('quota_group',source),policy,now)
            with self.db:self.db.execute('UPDATE v2_jobs SET attempts=attempts+1 WHERE id=? AND lease_token=?',(j['id'],j['lease_token']))
            body,headers=fetcher(url);observed=clock();sid=digest([source,url,observed,digest(body)])
            with self.db:self.db.execute('INSERT OR IGNORE INTO v2_snapshots VALUES(?,?,?,?,?,?,?,?)',(sid,j['id'],source,url,observed,digest(body),zlib.compress(body),json.dumps(headers)))
            payload=adapter.decode(body,j['kind'])
            if j['kind']=='discover':
                catalog=adapter.catalog(payload)
                if not catalog:raise ValueError('empty_catalog')
                with self.db:self.db.execute('INSERT INTO v2_catalog VALUES(?,?,?)',(sid,source,json.dumps(catalog)))
                result['catalog_entries']=len(catalog)
            else:
                from .normalization import normalize
                good,bad=normalize(adapter,payload,p)
                with self.db:
                    for r in good:self.db.execute('INSERT OR IGNORE INTO v2_results VALUES(?,?,?,?)',(sid,source,r['native_id'],json.dumps(r,ensure_ascii=False)))
                    for i,reason in bad:self.db.execute('INSERT INTO v2_rejected VALUES(?,?,?)',(sid,i,reason))
                    if source=='international':self.db.execute('INSERT INTO v2_catalog VALUES(?,?,?)',(sid,source,json.dumps(adapter.catalog(payload))))
                if not good:raise ValueError('no_valid_results')
                result.update(accepted=len(good),rejected=len(bad))
            self.finish(j,'done',at=observed);self.health(source,True,observed)
            return result|{'status':'done'}
        except StopCollection as e:
            reason=str(e);terminal=reason in ('source_not_approved','source_review_expired','local_storage_budget')
            self.finish(j,'blocked' if terminal else 'pending',reason,None if terminal else self.defer_time(policy.get('quota_group',source),policy,now),at=now)
            return result|{'status':'blocked' if terminal else 'deferred','reason':reason}
        except (HTTPError,URLError,OSError,TimeoutError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as e:
            reason=f'http_{e.code}' if isinstance(e,HTTPError) else type(e).__name__
            if isinstance(e,HTTPError) and e.code in (401,403,429):
                from email.utils import parsedate_to_datetime
                until=datetime.fromisoformat(now)+timedelta(hours=24);retry=e.headers.get('Retry-After') if e.headers else None
                if retry:
                    try:until=max(until,datetime.fromisoformat(now)+timedelta(seconds=int(retry)) if retry.isdigit() else parsedate_to_datetime(retry))
                    except (ValueError,TypeError,OverflowError):pass
                self.store.cooldown(policy.get('quota_group',source),until.isoformat())
            self.health(source,False,now,reason)
            terminal=j['attempts']>=2 or isinstance(e,(ValueError,KeyError,TypeError))
            self.finish(j,'failed' if terminal else 'pending',reason,self.defer_time(policy.get('quota_group',source),policy,now),at=now)
            return result|{'status':'failed' if terminal else 'deferred','reason':reason}
    def report(self):
        return {'jobs':[dict(r) for r in self.db.execute('SELECT id,source,kind,params,status,attempts,not_before,last_error FROM v2_jobs ORDER BY source,id')], 'health':[dict(r) for r in self.db.execute('SELECT * FROM v2_health')]}
    def close(self):self.store.close()

import zipfile
