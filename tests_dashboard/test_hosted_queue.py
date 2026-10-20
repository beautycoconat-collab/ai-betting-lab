"""Hosted queue tests: no real database or network calls."""
import unittest
from unittest.mock import MagicMock, patch
from dashboard.hosted_queue import enqueue, claim, finish


class QueueTests(unittest.TestCase):
    def test_unapproved_source_cannot_enqueue(self):
        conn=MagicMock()
        conn.execute.return_value.fetchone.return_value=None
        with self.assertRaisesRegex(ValueError,"hosted_source_not_approved"):
            enqueue(conn,"openliga","collect",{"league":"bl1"},"2026-10-19")
        self.assertEqual(conn.execute.call_count,1)

    def test_invalid_job_kind(self):
        with self.assertRaises(ValueError):
            enqueue(MagicMock(),"openliga","bet",{},"2026-10-19")

    def test_no_pending_job(self):
        conn=MagicMock()
        conn.execute.return_value.fetchone.return_value=None
        self.assertIsNone(claim(conn))

    def test_stale_token_cannot_finish(self):
        conn=MagicMock()
        conn.execute.return_value.fetchone.return_value=None
        self.assertFalse(finish(conn,"id","stale","done"))

    def test_invalid_finish_status(self):
        with self.assertRaises(ValueError):
            finish(MagicMock(),"id","token","paid")

    def test_pending_unapproved_job_blocked(self):
        conn=MagicMock()
        conn.execute.side_effect=[
            MagicMock(fetchone=lambda:("job-id","openliga")),
            MagicMock(fetchone=lambda:None),
            MagicMock()]
        self.assertEqual(claim(conn)["status"],"blocked")


if __name__=="__main__":
    unittest.main()
