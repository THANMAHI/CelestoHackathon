import os
import re
import sqlite3
from typing import List, Dict, Any, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    HAS_PSYCOPG2 = False

def serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(row)
    if "created_at" in d and hasattr(d["created_at"], "isoformat"):
        d["created_at"] = d["created_at"].isoformat()
    return d

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ledger:ledger@ledger:5432/ledger")

class Database:
    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url
        self.is_postgres = (db_url.startswith("postgres://") or db_url.startswith("postgresql://")) and HAS_PSYCOPG2
        self._sqlite_conn: Optional[sqlite3.Connection] = None

    def _get_postgres_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _get_sqlite_conn(self) -> sqlite3.Connection:
        if self._sqlite_conn is None:
            # In-memory or file-based sqlite for offline testing
            self._sqlite_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._sqlite_conn.row_factory = sqlite3.Row
            self._init_sqlite(self._sqlite_conn)
        return self._sqlite_conn

    def _init_sqlite(self, conn: sqlite3.Connection):
        # Create table and insert seed row if seed file exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                sandbox_name TEXT NOT NULL UNIQUE,
                problem_id TEXT NOT NULL,
                state TEXT NOT NULL,
                execution_target TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Seed row
        conn.execute("""
            INSERT OR IGNORE INTO runs (run_id, sandbox_name, problem_id, state, execution_target)
            VALUES ('run-seed001', 'sbx-seeddemo1', 'web-qa-detonation-seed', 'deleted', 'celesto_sandbox');
        """)
        conn.commit()

    def get_runs(self) -> List[Dict[str, Any]]:
        if self.is_postgres:
            try:
                with self._get_postgres_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT run_id, sandbox_name, problem_id, state, execution_target, created_at FROM runs ORDER BY created_at ASC;")
                        rows = cur.fetchall()
                        return [serialize_row(row) for row in rows]
            except Exception:
                # Fallback to sqlite if postgres is unreachable in test mode
                return self._get_sqlite_runs()
        return self._get_sqlite_runs()

    def _get_sqlite_runs(self) -> List[Dict[str, Any]]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("SELECT run_id, sandbox_name, problem_id, state, execution_target, created_at FROM runs ORDER BY created_at ASC;")
        rows = cur.fetchall()
        return [serialize_row(row) for row in rows]

    def insert_run(self, run: Dict[str, Any]) -> Dict[str, Any]:
        if self.is_postgres:
            try:
                with self._get_postgres_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target)
                            VALUES (%(run_id)s, %(sandbox_name)s, %(problem_id)s, %(state)s, %(execution_target)s)
                            ON CONFLICT (run_id) DO UPDATE SET
                                state = EXCLUDED.state,
                                execution_target = EXCLUDED.execution_target
                            RETURNING run_id, sandbox_name, problem_id, state, execution_target, created_at;
                        """, run)
                        conn.commit()
                        inserted = cur.fetchone()
                        return serialize_row(inserted)
            except Exception:
                return self._insert_sqlite_run(run)
        return self._insert_sqlite_run(run)

    def _insert_sqlite_run(self, run: Dict[str, Any]) -> Dict[str, Any]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (run_id) DO UPDATE SET
                state = excluded.state,
                execution_target = excluded.execution_target;
        """, (run["run_id"], run["sandbox_name"], run["problem_id"], run["state"], run["execution_target"]))
        conn.commit()
        cur.execute("SELECT run_id, sandbox_name, problem_id, state, execution_target, created_at FROM runs WHERE run_id = ?;", (run["run_id"],))
        row = cur.fetchone()
        return serialize_row(row)

db = Database()
