"""Supabase-backed source request reservation.

The database function is the authoritative cross-run/cross-worker gate. This
client never modifies policies or grants and never falls back to an unmetered
HTTP request when the database is unavailable.
"""
from __future__ import annotations

from cloudcheck.config import settings


class HostedQuotaUnavailable(OSError):
    pass


class HostedQuotaGate:
    def __init__(self, env=None):
        self.env=env

    @staticmethod
    def _connect(config):
        import psycopg
        return psycopg.connect(**config)

    def reserve(self, source: str) -> bool:
        if not isinstance(source,str) or not source:
            raise ValueError('source_required')
        try:
            config=settings('hosted',self.env,require_auth=False)
            with self._connect(config) as connection:
                with connection.transaction():
                    connection.execute("SET LOCAL ROLE lab_source_hunter")
                    row=connection.execute(
                        'SELECT lab.reserve_source_request(%s)',(source,)).fetchone()
                    return bool(row and row[0] is True)
        except (ValueError,TypeError):
            raise
        except Exception as exc:
            raise HostedQuotaUnavailable('hosted_quota_unavailable') from exc

