"""Quota-protected real fixture projection; no portfolio or betting execution.

Collection is explicit. Vercel serves the small generated artifact; training runs
in the worker. Unknown neutral status yields two conditional scenarios, never an
invented venue or a silently weighted final forecast.
"""
import argparse
import json
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo
from betting_lab.domain import digest
from engine.adapters import ADAPTERS
from engine.normalization import normalize
from engine.queue import Queue
from experts.research import aware, approved
from experts.football import ScoreEngine, Synthesizer, MarketSpecialist
from experts.multiseason import snapshot_rows
from experts.contracts import AuditContext
from experts.review import RedTeam, ScientificReferee
from dashboard.contracts import summarize
from dashboard.export import build as archive_projection

ROOT=Path(__file__).resolve().parents[1]


def fit_models(now, root=ROOT):
    rows=json.loads((root/'reports/phase2/bundesliga/dataset.json').read_text())
    fresh,_=snapshot_rows(root/'evidence/phase2/raw/openfootball-2025-26.json',
                          root/'reports/experts/source_acceptance_20261016.json')
    rows=sorted(rows+fresh,key=lambda r:(r['date'],r['id']))
    if len({r['id'] for r in rows})!=len(rows): raise ValueError('duplicate_training_match')
    if any(r['target']!='regulation90' or r['competition']!='de.1'
        or aware(r['observed_at'])>now or r['date']>=now.date().isoformat() for r in rows):
        raise ValueError('training_target_or_time_mismatch')
    split=int(len(rows)*.8)
    # Keep the entire same-day block out of training when the split hits it.
    while split>0 and rows[split-1]['date']==rows[split]['date']:split-=1
    engine=ScoreEngine().fit(rows[:split],now,'regulation90',mode='prematch')
    synth=Synthesizer().fit(engine.models,rows[split:])
    if synth.validation_observed_end is None or synth.validation_observed_end>now:
        raise ValueError('validation_not_available')
    return engine,synth


def fixtures(q, now, days=7):
    if type(days) is not int or not 1<=days<=14:raise ValueError('invalid_window')
    output=[]; rejected=0; seen=set()
    # One latest immutable snapshot per source URL. Corrections replace the view,
    # never mutate the old evidence. Native IDs are source+scope bound.
    snapshots=q.db.execute('''SELECT s.*,j.params FROM v2_snapshots s JOIN v2_jobs j
        ON j.id=s.job_id WHERE j.status='done' AND j.kind='collect'
        AND s.observed_at=(SELECT max(s2.observed_at) FROM v2_snapshots s2
          JOIN v2_jobs j2 ON j2.id=s2.job_id WHERE s2.source=s.source
          AND s2.url=s.url AND j2.status='done') ORDER BY s.observed_at DESC''').fetchall()
    for s in snapshots:
        if s['source']!='openliga' or not approved(q.registry.get(s['source'],{}),now):continue
        observed=aware(s['observed_at'])
        if observed>now or now-observed>timedelta(hours=24):continue
        params=json.loads(s['params']);adapter=ADAPTERS[s['source']]
        if s['url']!=adapter.url('collect',params):raise ValueError('snapshot_url_mismatch')
        dec=zlib.decompressobj();raw=dec.decompress(s['body'],2_000_001)
        if len(raw)>2_000_000 or not dec.eof or dec.unused_data or dec.unconsumed_tail or digest(raw)!=s['sha256']:
            raise ValueError('snapshot_integrity_failure')
        rows,bad=normalize(adapter,adapter.decode(raw,'collect'),params);rejected+=len(bad)
        for r in rows:
            if not r['kickoff_at'] or r['home_goals'] is not None:continue
            kickoff=aware(r['kickoff_at'])
            if kickoff<=now or kickoff.astimezone(ZoneInfo('Europe/Istanbul')).date()>now.astimezone(ZoneInfo('Europe/Istanbul')).date()+timedelta(days=days):continue
            key=(s['source'],r['competition'],r['season'],r['native_id'])
            if key in seen:continue
            seen.add(key)
            f={k:r[k] for k in ('home','away','competition','season','kickoff_at','target','neutral')}
            f.update(id=str(uuid5(NAMESPACE_URL,'ai-betting-lab:'+':'.join(key))),
                mode='verified_fixture', fixture_status='scheduled', models={},markets={},roles=[],findings=[],reviews=[],
                source_id=s['source'],native_id=r['native_id'],source_url=s['url'],
                snapshot_id=s['id'],snapshot_sha256=s['sha256'],observed_at=s['observed_at'],
                published_at=None,date=kickoff.astimezone(ZoneInfo('Europe/Istanbul')).date().isoformat(),
                source_license='ODbL-1.0',attribution='OpenLigaDB contributors — https://www.openligadb.de/lizenz',
                reliability='Kaynak fikstürü doğrulandı. Kadro, oran ve saha durumu ayrıca doğrulanmalıdır.')
            output.append(f)
    return sorted(output,key=lambda r:(r['kickoff_at'],r['id'])),rejected


def role_analysis(f, engine, synth):
    cases=f.get('scenarios',[])
    done={
      'coordinator':{'fixture_id':f['id'],'kickoff_at':f['kickoff_at'],'execution_enabled':False},
      'source_hunter':{'source':f['source_id'],'url':f['source_url'],'observed_at':f['observed_at'],'license':'ODbL-1.0'},
      'data_validator':{'snapshot_sha256':f['snapshot_sha256'],'target':f['target'],'native_id':f.get('native_id'),'neutral_status':'unknown' if f['neutral'] is None else 'provided'},
      'team_strength':{side:{'team':f[side],'elo':engine.models['elo'].ratings[f[side]],'attack':engine.models['poisson'].attack[f[side]],'defence':engine.models['poisson'].defence[f[side]],'xg':None} for side in ('home','away')},
      'score_engine':{'model_versions':engine.versions,'training_end':max(m.training_end for m in engine.models.values()),'conditional_scenarios':[s['id'] for s in cases]},
      'market_specialist':{'model':'ensemble','unsupported':['half1'],'conditional_venue':f['neutral'] is None},
      'synthesizer':synth.report(),
      'red_team':{'scenarios':[{k:s[k] for k in ('id','findings')} for s in cases]},
      'scientific_referee':{'scenarios':[{k:s[k] for k in ('id','reviews')} for s in cases]}}
    roles=[dict(id=r,status='done',analysis=value) for r,value in done.items()]
    reasons={'lineup_researcher':'verified_lineup_or_injury_source_missing',
        'external_researcher':'approved_external_forecast_missing','odds_analyst':'verified_market_price_missing',
        'learning_auditor':'fixture_not_finished_no_forward_metrics'}
    roles += [dict(id=r,status='insufficient_data',analysis={'reason':reason}) for r,reason in reasons.items()]
    roles += [dict(id='risk_manager',status='blocked',analysis={'reason':'pilot_disabled','stake':0,'execution_enabled':False})]
    return roles


def analyze(f, engine, synth, now):
    def insufficient(reason):
        from foundation.roles import registry
        roles=[dict(id=r['id'],status='done' if r['id'] in ('coordinator','source_hunter','data_validator') else 'insufficient_data',analysis={'reason':reason,'source_snapshot':f['snapshot_sha256']}) for r in registry()]
        return f|{'prediction_status':'insufficient_data','prediction_reason':reason,'roles':roles}
    if f['competition']!='bl1' or f['target']!='regulation90':
        return insufficient('unvalidated_league_or_target')
    if any(f[t] not in getattr(m,'attack',getattr(m,'ratings',{})) for m in engine.models.values()
           if m.name!='baseline' for t in ('home','away')):
        return insufficient('unmapped_or_untrained_team')
    cases=[False,True] if f['neutral'] is None else [f['neutral']]
    scenarios=[]
    for neutral in cases:
        numerical=dict(home=f['home'],away=f['away'],date=aware(f['kickoff_at']).date().isoformat(),
                       neutral=neutral,target=f['target'])
        forecasts=engine.forecast(numerical);mixture=synth.forecast(numerical)
        models={n:summarize(p['distribution'],p['training_end'],engine.versions[n]) for n,p in forecasts.items()}
        pid=digest([f['id'],f['snapshot_sha256'],engine.versions,synth.report(),now.isoformat(),neutral])
        models['ensemble']=summarize(mixture.export(),max(m.training_end for m in engine.models.values()),digest([engine.versions,synth.report()]))
        markets={'btts':MarketSpecialist().calculate(mixture,'btts'),'half1':{'status':'insufficient_data'}}
        for kind in ('over','under','home_over','away_over'):
            for line in (.5,1.5,2.5,3.5,4.5,5.5):markets[f'{kind}_{line}']=MarketSpecialist().calculate(mixture,kind,line)
        import numpy as np
        spread=float(np.ptp([v['distribution']['p_1x2'] for v in forecasts.values()],axis=0).max())
        context=AuditContext(schema_version='1.0',fixture_id=f['id'],as_of=now,kickoff_at=f['kickoff_at'],
            training_end=max(m.training_end for m in engine.models.values()),mode='prematch',
            observations={f['snapshot_id']:f['observed_at']},lineup_evidence_ids=[],
            upstream_groups={f['source_id']:[f['snapshot_id']]},training_matches=min(m.n_train for m in engine.models.values()),
            probabilities=tuple(mixture.outcome()),model_spread=spread,prediction_id=pid)
        findings=RedTeam().inspect(context);reviews=[]
        for round_no in (1,2):
            verdict=ScientificReferee().decide(context,findings,round_no)
            reviews.append(verdict.model_dump(mode='json'))
            if verdict.status!='needs_reanalysis':break
        scenarios.append(dict(id=pid,neutral=neutral,label='Nötr saha varsayımı' if neutral else 'Ev sahibi avantajı varsayımı',
            models=models,markets=markets,market_model='ensemble',findings=[x.model_dump(mode='json') for x in findings],
            reviews=reviews,training_dataset_sha256=engine.dataset_hash,ensemble_validation=synth.report()))
    base=f|dict(prediction_status='conditional_scenarios' if len(cases)>1 else 'calculated',as_of=now.isoformat(),
        scenarios=scenarios,execution_enabled=False,model_data_last_match=engine.models['poisson'].training_end)
    # Never pick/average a venue scenario without evidence or weights.
    if len(cases)==1:base.update({k:scenarios[0][k] for k in ('models','markets','market_model','findings','reviews')})
    base['roles']=role_analysis(base,engine,synth)
    return base


def run(db_path,collect=False,now=None,days=7):
    now=aware(now or datetime.now(timezone.utc));q=Queue(db_path)
    try:
        collection={'status':'not_requested'}
        if collect:
            season=now.year if now.month>=7 else now.year-1
            q.enqueue('openliga','collect',{'league':'bl1','season':str(season)},now=now.isoformat(),cycle=now.date().isoformat())
            collection=q.work_one()
        rows,rejected=fixtures(q,now,days)
        engine,synth=fit_models(now) if rows else (None,None)
        matches=[analyze(f,engine,synth,now) for f in rows]
        output=archive_projection(now=now)
        from hashlib import sha256
        code_sha=sha256(b''.join((ROOT/p).read_bytes() for p in ('engine/models.py','experts/football.py','dashboard/daily.py'))).hexdigest()
        output.update(engine_code_sha256=code_sha,fixtures=matches,connection='verified_source_worker',collection=collection,
            fixture_scope='OpenLigaDB Bundesliga only; other leagues are not yet enabled',rejected_rows=rejected,
            source_attribution='OpenLigaDB contributors · ODbL 1.0 · https://www.openligadb.de/lizenz')
        return output
    finally:q.close()


def main():
    p=argparse.ArgumentParser();p.add_argument('--database',default='data/dashboard-live.sqlite');p.add_argument('--collect',action='store_true');p.add_argument('--out',default='public/data/dashboard.json');p.add_argument('--days',type=int,default=7)
    a=p.parse_args();data=run(a.database,a.collect,days=a.days)
    path=Path(a.out);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n');tmp.replace(path)
    print(json.dumps({'fixtures':len(data['fixtures']),'collection':data['collection'],'pilot':False}))
if __name__=='__main__':main()
