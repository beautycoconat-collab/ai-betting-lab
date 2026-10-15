"""Deduplication, lineage and explicitly retrospective time splits."""
import json,hashlib
from collections import defaultdict
from betting_lab.domain import digest

def build(db,source,competition=None,start='2010-01-01',end='2026-01-01'):
    rows=db.execute('''SELECT r.payload,s.observed_at,s.sha256,s.url,s.id snapshot_id FROM v2_results r JOIN v2_snapshots s ON s.id=r.snapshot_id WHERE r.source=? ORDER BY s.observed_at DESC,s.id DESC''',(source,)).fetchall()
    seen_native=set();groups=defaultdict(list);excluded=defaultdict(int)
    for r in rows:
        m=json.loads(r['payload'])
        if m['native_id'] in seen_native:continue
        seen_native.add(m['native_id'])
        if competition and m['competition']!=competition:continue
        if not start<=m['date']<end:continue
        if m['home_goals'] is None:excluded['missing_result']+=1;continue
        if m['neutral'] is None:excluded['unknown_neutral']+=1;continue
        key=digest([source,m['competition'],m['date'],m['home'],m['away'],m['target']])
        m.update(id=key,observed_at=r['observed_at'],snapshot_sha256=r['sha256'],snapshot_id=r['snapshot_id'],source_url=r['url'])
        groups[(m['date'],m['home'],m['away'])].append(m)
    out=[]
    for group in groups.values():
        if len({(r['home_goals'],r['away_goals'],r['target'],r['competition']) for r in group})>1:excluded['conflicting_duplicate']+=len(group);continue
        out.append(group[0]);excluded['duplicate']+=len(group)-1
    out.sort(key=lambda r:(r['date'],r['id']))
    return out,dict(excluded)

def split(rows,train_end,validation_end,test_end,mode='retrospective'):
    if not train_end<validation_end<test_end:raise ValueError('unordered_boundaries')
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('duplicate_id')
    train=[r for r in rows if r['date']<train_end];val=[r for r in rows if train_end<=r['date']<validation_end];test=[r for r in rows if validation_end<=r['date']<test_end]
    if not train or not val or not test:raise ValueError('empty_partition')
    if mode=='point_in_time':
        if any(r['observed_at'][:10]>=train_end for r in train):raise ValueError('archive_not_available_at_training_cutoff')
    elif mode!='retrospective':raise ValueError('unknown_time_mode')
    if max(r['date'] for r in train)>=min(r['date'] for r in val) or max(r['date'] for r in val)>=min(r['date'] for r in test):raise ValueError('time_overlap')
    return train,val,test

def manifest(rows):
    stable=[{k:r[k] for k in ('id','date','home','away','home_goals','away_goals','neutral','target','snapshot_sha256')} for r in rows]
    return {'sha256':digest(stable),'count':len(rows),'first_date':rows[0]['date'] if rows else None,'last_date':rows[-1]['date'] if rows else None,'snapshot_hashes':sorted({r['snapshot_sha256'] for r in rows}),'match_ids':[r['id'] for r in rows]}
