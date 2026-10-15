"""Hosted public-key/Auth reachability and anon API boundary. No user JWT claim."""
import argparse,json,os,re
from pathlib import Path
from .runner import http

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    ref=os.environ.get('LAB_TEST_PROJECT_REF','');key=os.environ.get('LAB_SUPABASE_ANON_KEY','')
    report={'environment':'hosted','status':'blocked','authenticated_user_test':'not_run'}
    code=2
    try:
        if not re.fullmatch('[a-z0-9]{20}',ref) or not key:raise ValueError('missing_configuration')
        base='https://'+ref+'.supabase.co';headers={'apikey':key}
        status,settings=http(base+'/auth/v1/settings',headers)
        if status!=200:raise ValueError('valid_public_key_required')
        report['auth_settings_status']=status
        report['anonymous_enabled']=settings.get('external',{}).get('anonymous_users',False)
        probes=[]
        for table in ('predictions','review_decisions','paper_wallet'):
            url=base+'/rest/v1/'+table+'?id=eq.'+('1' if table=='paper_wallet' else '00000000-0000-0000-0000-000000000000')
            status,result=http(url,{**headers,'Content-Type':'application/json','Content-Profile':'lab'},'PATCH',{'id':1})
            if status not in (403,406) or result.get('code') not in ('42501','PGRST106'):raise ValueError('api_denial_not_proven')
            probes.append({'table':table,'status':status,'code':result.get('code')})
        report['probes']=probes;report['status']='passed';code=0
    except Exception as error:
        report['reason']='probe_failed_or_configuration_missing';report['error_type']=type(error).__name__
    path=Path(a.out);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2))
    print(json.dumps({'status':report['status']}));return code

if __name__=='__main__':raise SystemExit(main())
