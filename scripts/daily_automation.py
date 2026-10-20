"""Run the fail-closed daily research cycle; never executes a portfolio."""
import argparse
import json
from dashboard.automation import cycle


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--database',default='data/dashboard-live.sqlite')
    p.add_argument('--out',default='public/data/dashboard.json')
    p.add_argument('--status-out',default='public/data/automation-status.json')
    p.add_argument('--days',type=int,default=7)
    p.add_argument('--no-collect',action='store_true')
    p.add_argument('--persist-supabase',action='store_true')
    a=p.parse_args(argv)
    _,status=cycle(a.database,a.out,a.status_out,collect=not a.no_collect,
                   persist=a.persist_supabase,days=a.days)
    print(json.dumps(status,ensure_ascii=False,sort_keys=True))


if __name__=='__main__':main()
