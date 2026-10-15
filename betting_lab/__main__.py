import argparse
import json
from pathlib import Path
from betting_lab.store import Store
from betting_lab.collector import collect
from betting_lab.adapters import ADAPTERS
from betting_lab.identity import reconcile

def main():
    p=argparse.ArgumentParser(description='Real football data collector; no betting execution')
    p.add_argument('command',choices=['collect','export','reconcile'])
    p.add_argument('--db',default='data/lab.sqlite')
    p.add_argument('--season',type=int,default=2024)
    p.add_argument('--source',choices=['all',*ADAPTERS],default='all')
    p.add_argument('--output',default='data/export.json')
    a=p.parse_args()
    if not 2010<=a.season<=2100: p.error('season must be 2010..2100')
    root=Path(__file__).resolve().parent.parent
    store=Store(a.db)
    try:
        if a.command=='collect':
            policies=json.loads((root/'config/sources.json').read_text())
            results=[collect(store,s,policies[s],a.season) for s in ADAPTERS if a.source in ('all',s)]
            print(json.dumps(results,ensure_ascii=False,indent=2))
            return 1 if any(r['status'] in ('error','invalid','partial') for r in results) else 0
        rows=store.latest()
        out={'data_kind':'real','observations':rows} if a.command=='export' else reconcile(rows,json.loads((root/'config/aliases.json').read_text()))
        path=Path(a.output); path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(out,ensure_ascii=False,indent=2))
        print(json.dumps({'output':str(path),'observations':len(rows)}))
        return 0
    finally:
        store.close()

if __name__=='__main__':
    raise SystemExit(main())
