"""Source-of-truth store.

Schema (per harness spec):
    chunks(chunk_id PK, doc_id, chunk_idx, source_version, content_hash,
           text, updated_at, deleted)

Backend: PostgreSQL if a server is reachable (see RUNLOG), else SQLite.
The interface is identical; only the placeholder style differs.
"""
from __future__ import annotations

import os
import sqlite3


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id     TEXT PRIMARY KEY,
  doc_id       TEXT NOT NULL,
  chunk_idx    INTEGER NOT NULL,
  source_version INTEGER NOT NULL,
  content_hash TEXT NOT NULL,
  text         TEXT NOT NULL,
  updated_at   REAL NOT NULL,
  deleted      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
"""

SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id     TEXT PRIMARY KEY,
  doc_id       TEXT NOT NULL,
  chunk_idx    INTEGER NOT NULL,
  source_version INTEGER NOT NULL,
  content_hash TEXT NOT NULL,
  text         TEXT NOT NULL,
  updated_at   DOUBLE PRECISION NOT NULL,
  deleted      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
"""


class SourceStore:
    def __init__(self, backend: str = "auto", path: str = "data/source.db",
                 pg_dsn: str | None = None):
        if backend == "auto":
            dsn_set = pg_dsn is not None or "RAGC_PG_DSN" in os.environ
            if self._pg_reachable(pg_dsn):
                backend = "postgres"
            elif dsn_set:
                # Fail loud: an explicit Postgres DSN that cannot be reached
                # must not silently degrade to SQLite (recorded 2026-09-12).
                raise RuntimeError(
                    "RAGC_PG_DSN is set but Postgres is unreachable; "
                    "refusing silent SQLite fallback")
            else:
                backend = "sqlite"
        self.backend = backend
        if backend == "postgres":
            import psycopg
            dsn = pg_dsn or os.environ.get("RAGC_PG_DSN",
                                           "dbname=ragc user=postgres host=localhost")
            self._conn = psycopg.connect(dsn, autocommit=True)
            self._ph = "%s"
            with self._conn.cursor() as cur:
                cur.execute(SCHEMA_PG)
                cur.execute("TRUNCATE chunks")  # fresh store per scenario run
        else:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            if os.path.exists(path):
                os.remove(path)  # fresh store per scenario run
            self._conn = sqlite3.connect(path)
            self._ph = "?"
            self._conn.executescript(SCHEMA_SQLITE)
        self._cur = self._conn.cursor()

    @staticmethod
    def _pg_reachable(dsn) -> bool:
        try:
            import psycopg
            c = psycopg.connect(dsn or os.environ.get(
                "RAGC_PG_DSN", "dbname=ragc user=postgres host=localhost"),
                connect_timeout=2)
            c.close()
            return True
        except Exception:
            return False

    # -- writes ---------------------------------------------------------
    def upsert_chunk(self, chunk_id, doc_id, chunk_idx, text, version,
                     chash, updated_at):
        ph = self._ph
        if self.backend == "postgres":
            sql = (f"INSERT INTO chunks VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},0) "
                   f"ON CONFLICT (chunk_id) DO UPDATE SET doc_id=EXCLUDED.doc_id,"
                   f"chunk_idx=EXCLUDED.chunk_idx,source_version=EXCLUDED.source_version,"
                   f"content_hash=EXCLUDED.content_hash,text=EXCLUDED.text,"
                   f"updated_at=EXCLUDED.updated_at,deleted=0")
        else:
            sql = (f"INSERT INTO chunks VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},0) "
                   f"ON CONFLICT(chunk_id) DO UPDATE SET doc_id=excluded.doc_id,"
                   f"chunk_idx=excluded.chunk_idx,source_version=excluded.source_version,"
                   f"content_hash=excluded.content_hash,text=excluded.text,"
                   f"updated_at=excluded.updated_at,deleted=0")
        self._cur.execute(sql, (chunk_id, doc_id, chunk_idx, version, chash,
                                text, updated_at))
        self._commit()

    def mark_deleted(self, chunk_id, updated_at):
        ph = self._ph
        self._cur.execute(
            f"UPDATE chunks SET deleted=1, updated_at={ph} WHERE chunk_id={ph}",
            (updated_at, chunk_id))
        self._commit()

    def _commit(self):
        if self.backend == "sqlite":
            self._conn.commit()

    def bulk_begin(self):
        """Batch many writes into one transaction (harness speed only;
        no effect on measured numbers)."""
        if self.backend == "postgres":
            self._conn.autocommit = False
        # sqlite3 already defers commit until bulk_end

    def bulk_end(self):
        if self.backend == "postgres":
            self._conn.commit()
            self._conn.autocommit = True
        else:
            self._conn.commit()

    # -- reads ----------------------------------------------------------
    def get_chunk(self, chunk_id):
        ph = self._ph
        self._cur.execute(f"SELECT * FROM chunks WHERE chunk_id={ph}", (chunk_id,))
        row = self._cur.fetchone()
        return self._row(row) if row else None

    def doc_chunks(self, doc_id):
        ph = self._ph
        self._cur.execute(
            f"SELECT * FROM chunks WHERE doc_id={ph} ORDER BY chunk_idx", (doc_id,))
        return [self._row(r) for r in self._cur.fetchall()]

    def all_chunk_ids(self):
        self._cur.execute("SELECT chunk_id FROM chunks")
        return [r[0] for r in self._cur.fetchall()]

    def get_all(self):
        """Bulk snapshot: {chunk_id: row}. The store is immutable during the
        query phase, so one snapshot per scenario replaces thousands of
        per-hit round-trips."""
        self._cur.execute("SELECT * FROM chunks")
        return {r[0]: self._row(r) for r in self._cur.fetchall()}

    def count(self):
        self._cur.execute("SELECT COUNT(*) FROM chunks")
        return self._cur.fetchone()[0]

    @staticmethod
    def _row(r):
        keys = ("chunk_id", "doc_id", "chunk_idx", "source_version",
                "content_hash", "text", "updated_at", "deleted")
        return dict(zip(keys, r))

    def close(self):
        self._conn.close()
