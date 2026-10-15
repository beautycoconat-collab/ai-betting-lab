import argparse,json
from pathlib import Path
from .queue import Queue

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['enqueue','work','status','catalog','plan']);p.add_argument('--db',default='data/lab.sqlite');p.add_argument('--source');p.add_argument('--kind',default='collect',choices=['collect','discover']);p.add_argument('--league');p.add_argument('--season');p.add_argument('--max-jobs',type=int,default=8);p.add_argument('--seasons',nargs='*');p.add_argument('--leagues',nargs='*')
 a=p.parse_args();q=Queue(a.db)
 try:
  if a.command=='enqueue':
   params={k:v for k,v in {'league':a.league,'season':a.season}.items() if v is not None}
   print(q.enqueue(a.source,a.kind,params))
  elif a.command=='work':
   results=[]
   for _ in range(min(a.max_jobs,20)):
    r=q.work_one()
    if r is None:break
    results.append(r)
   print(json.dumps(results,indent=2))
  elif a.command=='status':print(json.dumps(q.report(),indent=2))
  else:
   rows=q.db.execute('SELECT * FROM v2_catalog WHERE source=? ORDER BY rowid DESC LIMIT 1',(a.source,)).fetchall()
   if not rows:raise SystemExit('No catalog snapshot. Enqueue discover and let its quota become due.')
   catalog=json.loads(rows[0]['payload'])
   if a.command=='catalog':print(json.dumps(catalog,ensure_ascii=False,indent=2))
   else:
    if a.source not in ('openliga','openfootball','footballcsv'):raise SystemExit('plan applies to league-season sources')
    jobs=[]
    for r in catalog:
     if (not a.seasons or r['season'] in a.seasons) and (not a.leagues or r['league'] in a.leagues):jobs.append(q.enqueue(a.source,'collect',{'league':r['league'],'season':r['season']}))
    print(json.dumps({'enqueued_or_existing':len(jobs),'job_ids':jobs}))
 finally:q.close()
if __name__=='__main__':main()
