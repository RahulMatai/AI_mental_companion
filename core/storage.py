"""SQLite storage for sessions and messages.

Decisions:
- WAL mode for safe concurrent reads while Streamlit reruns.
- UUID session ids so we never collide.
- One DB file, two tables, no ORM — this is a 200-line app.
"""
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


def _db_path() -> str:
    path = os.getenv("DB_PATH", "data/sessions.db")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    return path


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and enable WAL. Idempotent."""
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                started_at  TEXT NOT NULL,
                ended_at    TEXT,
                summary     TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);"
        )
    logger.info("Database initialized at %s", _db_path())


def new_session() -> str:
    session_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, started_at) VALUES (?, ?)",
            (session_id, datetime.utcnow().isoformat()),
        )
    logger.info("New session: %s", session_id)
    return session_id


def save_message(session_id: str, role: str, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.utcnow().isoformat()),
        )


def close_session(session_id: str, summary: Optional[str] = None) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE sessions SET ended_at = ?, summary = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), summary, session_id),
        )
    logger.info("Closed session %s", session_id)


def recent_sessions(limit: int = 10) -> list[dict]:
    """Return recent sessions with at least one user message."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.started_at, s.ended_at, s.summary,
                   (SELECT COUNT(*) FROM messages m
                      WHERE m.session_id = s.id AND m.role = 'user') AS user_msgs
              FROM sessions s
             WHERE EXISTS (SELECT 1 FROM messages m
                            WHERE m.session_id = s.id AND m.role = 'user')
             ORDER BY s.started_at DESC
             LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def session_messages(session_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]
