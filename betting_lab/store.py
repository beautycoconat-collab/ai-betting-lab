import sqlite3
import json
import zlib
from pathlib import Path
from datetime import datetime, timedelta
from betting_lab.domain import digest

SCHEMA = '''
CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY, source TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, source TEXT, started_at TEXT, ended_at TEXT, status TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS blobs(hash TEXT PRIMARY KEY, body BLOB NOT NULL, bytes INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY, source TEXT NOT NULL, url TEXT NOT NULL, observed_at TEXT NOT NULL, hash TEXT NOT NULL REFERENCES blobs(hash), http_status INTEGER, headers TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS observations(snapshot_id TEXT NOT NULL REFERENCES snapshots(id), source TEXT NOT NULL, source_match_id TEXT NOT NULL, observed_at TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(snapshot_id,source_match_id));
CREATE TABLE IF NOT EXISTS quarantine(snapshot_id TEXT, row_index INTEGER, reason TEXT, PRIMARY KEY(snapshot_id,row_index));
CREATE TABLE IF NOT EXISTS cooldowns(source TEXT PRIMARY KEY, until_at TEXT NOT NULL);
'''

class StopCollection(Exception):
    pass

class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = Path(path)
        self.db = sqlite3.connect(path, timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript(SCHEMA)
    def close(self):
        self.db.close()
    def reserve(self, source, policy, now):
        """Count attempts before HTTP, transaction-safe across processes sharing this DB."""
        dt = datetime.fromisoformat(now)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT until_at FROM cooldowns WHERE source=?', (source,)).fetchone()
            if row and row[0] > now:
                raise StopCollection('cooldown')
            for start, cap in [((dt-timedelta(days=1)).isoformat(), policy['requests_per_24h']),
                               ((dt-timedelta(days=31)).isoformat(), policy['requests_per_31d'])]:
                n = self.db.execute('SELECT COUNT(*) FROM requests WHERE source=? AND at>?',(source,start)).fetchone()[0]
                if n >= cap:
                    raise StopCollection('quota_exhausted')
            last = self.db.execute('SELECT MAX(at) FROM requests WHERE source=?',(source,)).fetchone()[0]
            if last and (dt-datetime.fromisoformat(last)).total_seconds() < policy['min_interval_seconds']:
                raise StopCollection('minimum_interval')
            if self.path.stat().st_size > 40_000_000:
                raise StopCollection('local_storage_budget')
            self.db.execute('INSERT INTO requests(source,at) VALUES (?,?)',(source,now))
            self.db.commit()
        except Exception:
            self.db.rollback(); raise
    def cooldown(self, source, until):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO cooldowns VALUES (?,?)',(source,until))
    def fresh(self, source, url, now, ttl):
        row = self.db.execute('SELECT MAX(observed_at) FROM snapshots WHERE source=? AND url=?',(source,url)).fetchone()
        return bool(row[0] and 0 <= (datetime.fromisoformat(now)-datetime.fromisoformat(row[0])).total_seconds() < ttl)
    def run(self, source, at, status, detail):
        with self.db:
            self.db.execute('INSERT INTO runs(source,started_at,ended_at,status,detail) VALUES (?,?,?,?,?)', (source, at, at, status, json.dumps(detail)))
    def save(self, source, url, observed, body, headers, matches, rejected):
        h = digest(body)
        sid = digest([source,url,observed,h])
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO blobs VALUES (?,?,?)',(h,zlib.compress(body),len(body)))
            self.db.execute('INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?,?,?)',(sid,source,url,observed,h,200,json.dumps(headers)))
            for m in matches:
                self.db.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?)', (sid,source,m.source_match_id,observed,json.dumps(m.to_dict(),ensure_ascii=False)))
            for i, reason in rejected:
                self.db.execute('INSERT OR IGNORE INTO quarantine VALUES (?,?,?)',(sid,i,reason))
        return sid
    def latest(self):
        rows = self.db.execute('''SELECT data,observed_at,snapshot_id FROM (
          SELECT *,ROW_NUMBER() OVER(PARTITION BY source,source_match_id ORDER BY observed_at DESC,snapshot_id DESC) AS rn FROM observations
        ) WHERE rn=1 ORDER BY source,source_match_id''').fetchall()
        return [dict(json.loads(r['data']),observed_at=r['observed_at'],snapshot_id=r['snapshot_id'],data_kind='real') for r in rows]
