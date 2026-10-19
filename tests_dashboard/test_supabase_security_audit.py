import unittest
from dashboard.supabase_security_audit import assess, AUDIT_SQL

class SecurityAuditTests(unittest.TestCase):
    def test_no_schema_blocks(self):
        self.assertEqual(assess([],[])['status'],'blocked')
    def test_all_rls_still_requires_live_tests(self):
        rows=[{'table_name':'predictions','rls_enabled':True}]
        roles=[{'rolname':name,'wallet_insert':False} for name in ('anon','authenticated')]
        result=assess(rows,roles)
        self.assertEqual(result['rls_enabled_count'],1)
        self.assertIn('live_jwt_rls_worker_and_durable_quota_tests_pending',result['reasons'])
    def test_missing_rls_or_unsafe_wallet_grant(self):
        rows=[{'table_name':'paper_wallet','rls_enabled':False}]
        roles=[{'rolname':'anon','wallet_insert':True},{'rolname':'authenticated','wallet_insert':False}]
        reasons=assess(rows,roles)['reasons']
        self.assertIn('rls_disabled:paper_wallet',reasons)
        self.assertIn('wallet_insert_granted:anon',reasons)
    def test_read_only_sql(self):
        self.assertEqual(AUDIT_SQL.count('SELECT'),6)
        self.assertNotIn('ALTER TABLE',AUDIT_SQL)

if __name__=='__main__':unittest.main()
