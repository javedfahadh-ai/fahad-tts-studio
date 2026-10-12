"""SQLite history of generated audios."""
import os
import sqlite3
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("TTS_DB_PATH", os.path.join(BASE_DIR, "tts_history.db"))


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at REAL NOT NULL,
                title TEXT NOT NULL,
                text_preview TEXT,
                voice TEXT,
                speed REAL,
                duration REAL,
                chars INTEGER,
                format TEXT,
                filename TEXT
            )
        """)


def add_record(title, text_preview, voice, speed, duration, chars, format, filename):
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO history
               (created_at, title, text_preview, voice, speed, duration, chars, format, filename)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (time.time(), title, text_preview, voice, speed, duration, chars, format, filename),
        )
        return cur.lastrowid


def list_records(limit=100):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_record(rec_id):
    with _conn() as c:
        row = c.execute("SELECT * FROM history WHERE id = ?", (rec_id,)).fetchone()
        return dict(row) if row else None


def delete_record(rec_id):
    with _conn() as c:
        c.execute("DELETE FROM history WHERE id = ?", (rec_id,))
