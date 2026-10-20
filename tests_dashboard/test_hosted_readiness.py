import unittest
from datetime import datetime, timedelta, timezone
from dashboard.hosted_readiness import REQUIRED, inspect

NOW = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


class ReadinessTests(unittest.TestCase):
    def valid(self):
        return {'schema_version':'1.0', 'owner_approved':True,
                'checks':{k:{'passed':True,'verified_at':NOW.isoformat(),
                             'evidence_sha256':'a'*64,'reviewer':'independent-auditor'}
                          for k in REQUIRED}}

    def test_empty_is_blocked(self):
        result = inspect({}, NOW)
        self.assertEqual(result['status'],'blocked')
        self.assertFalse(result['schedule_enabled'])

    def test_complete_evidence_is_review_only(self):
        result = inspect(self.valid(), NOW)
        self.assertEqual(result['status'],'review_ready')
        self.assertFalse(result['schedule_enabled'])

    def test_boolean_only_is_not_evidence(self):
        m = self.valid()
        m['checks']['hosted_jwt_verified'] = True
        self.assertIn('hosted_jwt_verified',inspect(m,NOW)['missing'])

    def test_stale_evidence_rejected(self):
        m=self.valid()
        m['checks']['hosted_rls_verified']['verified_at']=(NOW-timedelta(days=8)).isoformat()
        self.assertIn('hosted_rls_verified',inspect(m,NOW)['missing'])

    def test_future_evidence_rejected(self):
        m=self.valid()
        m['checks']['hosted_rls_verified']['verified_at']=(NOW+timedelta(minutes=1)).isoformat()
        self.assertIn('hosted_rls_verified',inspect(m,NOW)['missing'])

    def test_invalid_digest_rejected(self):
        m=self.valid()
        m['checks']['hosted_rls_verified']['evidence_sha256']='not-a-digest'
        self.assertIn('hosted_rls_verified',inspect(m,NOW)['missing'])

    def test_owner_approval_independent(self):
        m=self.valid()
        m['owner_approved']=False
        self.assertIn('owner_approval',inspect(m,NOW)['missing'])

    def test_naive_clock_rejected(self):
        with self.assertRaises(ValueError):
            inspect(self.valid(),datetime(2026,10,19))

if __name__=='__main__': unittest.main()
