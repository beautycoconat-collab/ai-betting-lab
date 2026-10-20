import unittest
from dashboard.security_acceptance import assess, REQUIRED
class AcceptanceTests(unittest.TestCase):
    def test_missing_gates(self):
        x=assess({})
        self.assertEqual(x['status'],'not_accepted')
        self.assertFalse(x['cron_enabled'])
    def test_all_self_attested_still_requires_approval(self):
        x=assess(dict.fromkeys(REQUIRED,True))
        self.assertEqual(x['status'],'requires_human_approval')
        self.assertFalse(x['hosted_verified'])
    def test_nonboolean_rejected(self):
        self.assertIn('hosted_jwt_verified',assess({'hosted_jwt_verified':'true'})['missing'])
if __name__=='__main__':unittest.main()
