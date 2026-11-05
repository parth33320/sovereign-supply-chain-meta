"""
db.py - Unified Database Access Layer.
Supports PostgreSQL (via POSTGRES_DB_URI) with transparent SQLite fallback (mock_sap.db).
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import psycopg
    from psycopg.rows import dict_row
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False


def is_postgres_configured() -> bool:
    """Return True if POSTGRES_DB_URI is set and psycopg is available."""
    uri = os.environ.get("POSTGRES_DB_URI")
    return bool(uri and uri.strip() and HAS_PSYCOPG)


def get_db_connection():
    """
    Returns an active database connection and engine type ('postgres' or 'sqlite').
    If POSTGRES_DB_URI is set, returns a psycopg connection.
    Otherwise, returns an sqlite3 connection to mock_sap.db.
    """
    if is_postgres_configured():
        db_uri = os.environ.get("POSTGRES_DB_URI")
        conn = psycopg.connect(db_uri, autocommit=True, row_factory=dict_row)
        return conn, "postgres"
    else:
        conn = sqlite3.connect("mock_sap.db", timeout=20.0)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"


def execute_query(query: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
    """Execute a SELECT query and return rows as list of dicts."""
    conn, engine = get_db_connection()
    try:
        if engine == "postgres":
            pg_query = query.replace("?", "%s")
            with conn.cursor() as cur:
                cur.execute(pg_query, params or ())
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        else:
            cur = conn.cursor()
            cur.execute(query, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def execute_mutation(query: str, params: Optional[Sequence[Any]] = None) -> int:
    """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
    conn, engine = get_db_connection()
    try:
        if engine == "postgres":
            pg_query = query.replace("?", "%s")
            with conn.cursor() as cur:
                cur.execute(pg_query, params or ())
                return cur.rowcount
        else:
            cur = conn.cursor()
            cur.execute(query, params or ())
            conn.commit()
            return cur.rowcount
    finally:
        conn.close()
