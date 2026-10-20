"""Read-only inspection of an existing Supabase `lab` schema.

Run the SQL in Supabase SQL editor as a privileged administrator. This module
never changes grants, roles, RLS, migrations, or data.
"""
from pathlib import Path

AUDIT_SQL = r'''
SELECT n.nspname AS schema_name, c.relname AS table_name,
       c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS force_rls,
       (SELECT count(*) FROM pg_policies p
        WHERE p.schemaname=n.nspname AND p.tablename=c.relname) AS policy_count
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind IN ('r','p') AND n.nspname='lab'
ORDER BY c.relname;

SELECT schemaname,tablename,policyname,roles,cmd,qual,with_check
FROM pg_policies WHERE schemaname='lab'
ORDER BY tablename,policyname;

SELECT r.rolname,
       has_schema_privilege(r.rolname,'lab','USAGE') AS schema_usage,
       has_table_privilege(r.rolname,'lab.agent_roles','SELECT') AS roles_select,
       has_table_privilege(r.rolname,'lab.predictions','SELECT') AS predictions_select,
       has_table_privilege(r.rolname,'lab.paper_wallet','INSERT') AS wallet_insert
FROM pg_roles r
WHERE r.rolname IN ('anon','authenticated','service_role','lab_dashboard','lab_worker')
ORDER BY r.rolname;
'''.strip()


def assess(table_rows, role_rows):
    """Conservative assessment; catalog reads alone never prove JWT/RLS E2E."""
    if not table_rows:
        return {'status':'blocked','reasons':['lab_schema_tables_not_found']}
    problems=[]
    for row in table_rows:
        if row['rls_enabled'] is not True:
            problems.append('rls_disabled:'+row['table_name'])
    roles={r['rolname']:r for r in role_rows}
    for name in ('anon','authenticated'):
        if name not in roles:
            problems.append('missing_role_audit:'+name)
        elif roles[name]['wallet_insert'] is True:
            problems.append('wallet_insert_granted:'+name)
    # A catalog audit cannot authenticate as a real client, test API exposure,
    # establish worker least privilege, or prove durable scheduler state.
    problems.append('live_jwt_rls_worker_and_durable_quota_tests_pending')
    return {'status':'blocked','tables':len(table_rows),
            'rls_enabled_count':sum(r['rls_enabled'] is True for r in table_rows),
            'reasons':sorted(set(problems))}


def write_sql(path):
    Path(path).write_text(AUDIT_SQL+'\n',encoding='utf-8')
