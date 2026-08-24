"""
Lightweight SQLite persistence layer.
Stores each processed meeting: original filename, transcript, summary,
action items (JSON), and metadata.
"""
import sqlite3
import json
from datetime import datetime, timezone
from contextlib import contextmanager

from config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing',   -- processing | done | failed
    transcript TEXT,
    summary TEXT,
    key_decisions TEXT,      -- JSON list
    action_items TEXT,       -- JSON list of {owner, task, due_date}
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_meeting(filename: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO meetings (filename, status, created_at, updated_at) "
            "VALUES (?, 'processing', ?, ?)",
            (filename, _now(), _now()),
        )
        return cur.lastrowid


def mark_done(meeting_id: int, transcript: str, summary: str,
              key_decisions: list, action_items: list):
    with get_conn() as conn:
        conn.execute(
            """UPDATE meetings
               SET status='done', transcript=?, summary=?, key_decisions=?,
                   action_items=?, updated_at=?
               WHERE id=?""",
            (
                transcript,
                summary,
                json.dumps(key_decisions),
                json.dumps(action_items),
                _now(),
                meeting_id,
            ),
        )


def mark_failed(meeting_id: int, error: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE meetings SET status='failed', error=?, updated_at=? WHERE id=?",
            (error, _now(), meeting_id),
        )


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for field in ("key_decisions", "action_items"):
        if d.get(field):
            d[field] = json.loads(d[field])
        else:
            d[field] = []
    return d


def get_meeting(meeting_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone()
        return _row_to_dict(row) if row else None


def list_meetings(limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, filename, status, created_at, updated_at FROM meetings "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
