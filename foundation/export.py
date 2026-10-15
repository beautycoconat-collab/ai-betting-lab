"""Export versioned schemas, role registry, and an integrity checkpoint offline."""
import argparse,json,hashlib
from pathlib import Path
from .contracts import AgentMessage,Evidence,ReviewDecision,JobRequest,UnsupportedMarket
from .roles import registry
from .runtime import Runtime

def export_schemas(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    for cls in (AgentMessage,Evidence,ReviewDecision,JobRequest,UnsupportedMarket):
        (root/(cls.__name__+'.schema.json')).write_text(json.dumps(cls.model_json_schema(),indent=2,ensure_ascii=False))
    (root/'agent-roles.json').write_text(json.dumps(registry(),indent=2,ensure_ascii=False))

def export_audit(db_path,out):
    rt=Runtime(db_path)
    try:
        if not rt.verify_audit():raise ValueError('audit_chain_broken')
        rows=[dict(r) for r in rt.db.execute('SELECT * FROM f_audit ORDER BY seq')]
        body=json.dumps(rows,sort_keys=True,ensure_ascii=False,separators=(',',':'))
        result={'algorithm':'SHA-256','row_count':len(rows),'last_hash':rows[-1]['entry_hash'] if rows else '0'*64,'export_sha256':hashlib.sha256(body.encode()).hexdigest(),'events':rows,'notice':'Keep an independent copy. A database/file administrator can rewrite local records and hashes.'}
        Path(out).write_text(json.dumps(result,indent=2,ensure_ascii=False));return result['export_sha256']
    finally:rt.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--schemas',default='schemas/phase0');p.add_argument('--audit-db');p.add_argument('--audit-out',default='reports/phase0/audit-export.json');a=p.parse_args()
    export_schemas(a.schemas)
    if a.audit_db:print(export_audit(a.audit_db,a.audit_out))
if __name__=='__main__':main()
