"""PostgreSQL connection pool for nb_monitor database."""

import os
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool, extras


_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5433")),
            dbname=os.getenv("POSTGRES_DB", "nb_monitor"),
            user=os.getenv("POSTGRES_USER", "nb_admin"),
            password=os.getenv("POSTGRES_PASSWORD", "nb_secret"),
        )
    return _pool


@contextmanager
def get_conn():
    p = get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


@contextmanager
def get_cursor(cursor_factory=None):
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=cursor_factory or extras.DictCursor)
        try:
            yield cur
        finally:
            cur.close()


def execute_sql_file(filepath):
    """Run a .sql file against the database."""
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()
    with get_cursor() as cur:
        cur.execute(sql)


def close_pool():
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
