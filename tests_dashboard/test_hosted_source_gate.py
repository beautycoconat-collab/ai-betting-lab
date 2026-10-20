"""Hosted source policy acceptance tests (offline, no network)."""
import unittest
from datetime import datetime, timedelta, timezone
from dashboard.hosted_source_gate import approved


class HostedSourceGateTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 19, tzinfo=timezone.utc)
        self.policy = {
            "status": "approved",
            "license": "reviewed",
            "permission_url": "https://example.org/terms",
            "review_expires": self.now + timedelta(days=1),
            "max_daily": 20,
            "min_interval_seconds": 60,
        }

    def test_valid_review(self):
        self.assertTrue(approved(self.policy, self.now))

    def test_missing_policy(self):
        self.assertFalse(approved(None, self.now))

    def test_unapproved(self):
        self.policy["status"] = "pending_review"
        self.assertFalse(approved(self.policy, self.now))

    def test_expired(self):
        self.policy["review_expires"] = self.now
        self.assertFalse(approved(self.policy, self.now))

    def test_missing_license(self):
        self.policy["license"] = ""
        self.assertFalse(approved(self.policy, self.now))

    def test_missing_permission_url(self):
        self.policy["permission_url"] = ""
        self.assertFalse(approved(self.policy, self.now))

    def test_invalid_quota(self):
        self.policy["max_daily"] = 0
        self.assertFalse(approved(self.policy, self.now))

    def test_invalid_interval(self):
        self.policy["min_interval_seconds"] = -1
        self.assertFalse(approved(self.policy, self.now))


if __name__ == "__main__":
    unittest.main()
