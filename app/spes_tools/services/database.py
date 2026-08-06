from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from spes_tools.services.storage import data_dir

SCHEMA_VERSION = 1


def default_database_path() -> Path:
    return data_dir() / "consolle_spes.db"


class Database:
    """SQLite persistence for users, permissions, settings, logs and notifications."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._prepare_path()
        self.initialize()

    def _prepare_path(self) -> None:
        """Move a legacy JSON file aside before creating the SQLite database."""
        if not self.path.exists():
            return
        try:
            header = self.path.read_bytes()[:16]
        except OSError:
            return
        if header.startswith(b"SQLite format 3"):
            return
        try:
            json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return
        backup = self.path.with_suffix(self.path.suffix + ".legacy.json")
        if not backup.exists():
            self.path.replace(backup)
        else:
            self.path.unlink()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    must_change_password INTEGER NOT NULL DEFAULT 1,
                    salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT
                );
                CREATE TABLE IF NOT EXISTS user_permissions (
                    username TEXT NOT NULL,
                    permission TEXT NOT NULL,
                    PRIMARY KEY (username, permission),
                    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    username TEXT,
                    category TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    audience TEXT NOT NULL DEFAULT 'all',
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    read_at TEXT
                );
                """
            )
            db.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    def log(self, username: str | None, category: str, action: str, details: str = "") -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO activity_logs(timestamp, username, category, action, details) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().isoformat(timespec="seconds"), username, category, action, details),
            )

    def recent_logs(self, limit: int = 200) -> list[dict[str, object]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, timestamp, username, category, action, details FROM activity_logs ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        return [dict(row) for row in rows]
