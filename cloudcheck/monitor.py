"""Read-only project usage collection. No billing API writes or upgrades."""
import argparse,json
from pathlib import Path
from .config import settings,ConfigError
from .capacity import collect,decision

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    report={'status':'blocked','measurement':None,'gate':decision({})};code=2
    try:
        import psycopg
        config=settings('hosted',require_auth=False)
        with psycopg.connect(**config) as db:
            db.execute('set transaction read only')
            observation=collect(db)
            report={'status':'measured','measurement':observation,'gate':decision(observation)}
            code=0 if report['gate']['allowed'] else 2
    except ConfigError as error:report['reason']=str(error)
    except Exception as error:report['reason']='measurement_failed';report['error_type']=type(error).__name__
    path=Path(a.out);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2))
    print(json.dumps({'status':report['status'],'allowed':report['gate']['allowed']}));return code

if __name__=='__main__':raise SystemExit(main())
