"""
database.py — Gerenciamento de conexão com PostgreSQL via psycopg2.
Sem ORM: todas as queries são SQL puro.
"""

import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://booking:secret@localhost:5432/bookinghub")


def get_connection():
    """Retorna uma conexão com autocommit=False (controle manual de transação)."""
    return psycopg2.connect(DATABASE_URL)


@contextmanager
def get_cursor(commit=True):
    """
    Context manager que fornece um cursor e gerencia a transação.
    Uso:
        with get_cursor() as cur:
            cur.execute(...)
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur, conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
