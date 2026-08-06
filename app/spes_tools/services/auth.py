from __future__ import annotations

import base64
import hashlib
import hmac
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from spes_tools.services.database import Database, default_database_path

DEFAULT_PASSWORD = "gamba"
PBKDF2_ITERATIONS = 240_000

PERMISSIONS: dict[str, str] = {
    "site": "Sito SPES",
    "sportivi": "Sportivi in Cloud",
    "wellness": "Wellness in Cloud",
    "cassa_cloud": "Cassa in Cloud",
    "spes_connect": "SPES Connect",
    "homebank_volksbank": "Home Banking Volksbank",
    "homebank_bcc": "Home Banking BCC",
    "homebank_nexi": "Home Banking Nexi",
    "gmail_admin": "Gmail amministrazione",
    "gmail_segreteria": "Gmail segreteria",
    "gmail_consiglio": "Gmail consiglio",
    "pec": "PEC SPES",
    "drive": "Drive SPES",
    "banking": "Riconciliazione bancaria",
    "compensation": "Convertitore compensi",
    "cash": "Gestione Cassa",
    "csv_archive": "Archivio CSV",
    "fgi_results": "Risultati FGI",
    "fgi_calendar": "Calendario gare FGI Veneto",
    "fgi_regulation": "Regolamento FGI",
    "music_gare": "Musica per gare",
    "music_awards": "Musica premiazioni",
    "settings": "Impostazioni",
    "users_manage": "Gestione utenti e permessi",
    "activity_logs": "Registro attività",
    "backup": "Backup e ripristino",
    "updates": "Aggiornamenti applicazione",
}

ROLE_DEFAULTS: dict[str, set[str]] = {
    "admin": set(PERMISSIONS),
    "segreteria": {"site", "wellness", "gmail_segreteria", "fgi_results", "fgi_calendar", "fgi_regulation"},
    "consiglieri": {
        "site", "sportivi", "wellness", "cassa_cloud", "spes_connect", "gmail_consiglio", "drive",
        "fgi_results", "fgi_calendar", "fgi_regulation", "music_gare", "music_awards",
    },
}


@dataclass(frozen=True)
class SessionUser:
    username: str
    display_name: str
    role: str
    permissions: frozenset[str]

    def can(self, permission: str) -> bool:
        return permission in self.permissions


class UserStore:
    """SQLite-backed user and permission store.

    The optional path is retained for tests and migrations. Existing JSON user files are
    moved aside automatically before the SQLite database is created.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_database_path()
        self.database = Database(self.path)
        self._ensure_defaults()

    @staticmethod
    def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        return base64.b64encode(salt).decode("ascii"), base64.b64encode(digest).decode("ascii")

    def _ensure_defaults(self) -> None:
        with self.database.connect() as db:
            count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if count:
                return
        for username, role, display in (
            ("admin", "admin", "Amministratore"),
            ("segreteria", "segreteria", "Segreteria"),
            ("consiglieri", "consiglieri", "Consiglieri"),
        ):
            self._insert_user(username, display, role, DEFAULT_PASSWORD, ROLE_DEFAULTS[role], True, True)

    def _insert_user(
        self, username: str, display_name: str, role: str, password: str,
        permissions: set[str], active: bool, must_change: bool,
    ) -> None:
        salt, password_hash = self._hash_password(password)
        now = datetime.now().isoformat(timespec="seconds")
        with self.database.connect() as db:
            db.execute(
                "INSERT INTO users(username, display_name, role, active, must_change_password, salt, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (username, display_name, role, int(active), int(must_change), salt, password_hash, now),
            )
            db.executemany(
                "INSERT INTO user_permissions(username, permission) VALUES (?, ?)",
                [(username, permission) for permission in sorted(permissions)],
            )

    def list_users(self) -> list[dict[str, Any]]:
        with self.database.connect() as db:
            rows = db.execute(
                "SELECT username, display_name, role, active, must_change_password, last_login FROM users ORDER BY username"
            ).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                permissions = [item[0] for item in db.execute(
                    "SELECT permission FROM user_permissions WHERE username=? ORDER BY permission", (row["username"],)
                ).fetchall()]
                item = dict(row)
                item["active"] = bool(item["active"])
                item["must_change_password"] = bool(item["must_change_password"])
                item["permissions"] = permissions
                result.append(item)
        return result

    def get_user(self, username: str) -> dict[str, Any] | None:
        key = username.strip().lower()
        return next((user for user in self.list_users() if user["username"] == key), None)

    def authenticate(self, username: str, password: str) -> tuple[SessionUser | None, bool]:
        key = username.strip().lower()
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM users WHERE username=?", (key,)).fetchone()
            if row is None or not bool(row["active"]):
                self.database.log(key or None, "security", "login_failed", "Utente inesistente o disattivato")
                return None, False
            try:
                salt = base64.b64decode(row["salt"])
                expected = base64.b64decode(row["password_hash"])
            except Exception:
                return None, False
            _, supplied_b64 = self._hash_password(password, salt)
            if not hmac.compare_digest(expected, base64.b64decode(supplied_b64)):
                self.database.log(key, "security", "login_failed", "Password errata")
                return None, False
            permissions = frozenset(item[0] for item in db.execute(
                "SELECT permission FROM user_permissions WHERE username=?", (key,)
            ).fetchall())
            now = datetime.now().isoformat(timespec="seconds")
            db.execute("UPDATE users SET last_login=? WHERE username=?", (now, key))
            session = SessionUser(key, row["display_name"], row["role"], permissions)
            must_change = bool(row["must_change_password"])
        self.database.log(key, "security", "login_success", f"Profilo {session.role}")
        return session, must_change

    def set_password(self, username: str, password: str, *, must_change: bool = False) -> None:
        if len(password) < 6:
            raise ValueError("La password deve contenere almeno 6 caratteri.")
        key = username.strip().lower()
        salt, password_hash = self._hash_password(password)
        with self.database.connect() as db:
            cursor = db.execute(
                "UPDATE users SET salt=?, password_hash=?, must_change_password=? WHERE username=?",
                (salt, password_hash, int(must_change), key),
            )
            if cursor.rowcount == 0:
                raise KeyError("Utente non trovato.")
        self.database.log(key, "security", "password_changed", "Cambio o reimpostazione password")

    def save_user(self, *, username: str, display_name: str, role: str, permissions: set[str], active: bool) -> None:
        key = username.strip().lower()
        if not key:
            raise ValueError("Il nome utente è obbligatorio.")
        if role not in ROLE_DEFAULTS:
            raise ValueError("Profilo non valido.")
        permissions = {item for item in permissions if item in PERMISSIONS}
        with self.database.connect() as db:
            exists = db.execute("SELECT 1 FROM users WHERE username=?", (key,)).fetchone()
            if not exists:
                salt, password_hash = self._hash_password(DEFAULT_PASSWORD)
                db.execute(
                    "INSERT INTO users(username, display_name, role, active, must_change_password, salt, password_hash, created_at) VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
                    (key, display_name.strip() or key, role, int(active), salt, password_hash, datetime.now().isoformat(timespec="seconds")),
                )
            else:
                db.execute(
                    "UPDATE users SET display_name=?, role=?, active=? WHERE username=?",
                    (display_name.strip() or key, role, int(active), key),
                )
            db.execute("DELETE FROM user_permissions WHERE username=?", (key,))
            db.executemany(
                "INSERT INTO user_permissions(username, permission) VALUES (?, ?)",
                [(key, permission) for permission in sorted(permissions)],
            )
        self.database.log("admin", "users", "user_saved", key)

    def create_user(self, username: str, display_name: str, role: str) -> None:
        if self.get_user(username):
            raise ValueError("Esiste già un utente con questo nome.")
        self.save_user(username=username, display_name=display_name, role=role, permissions=set(ROLE_DEFAULTS[role]), active=True)

    def delete_user(self, username: str) -> None:
        key = username.strip().lower()
        if key == "admin":
            raise ValueError("L'utente admin principale non può essere eliminato.")
        with self.database.connect() as db:
            db.execute("DELETE FROM users WHERE username=?", (key,))
        self.database.log("admin", "users", "user_deleted", key)

    def reset_permissions_to_role(self, username: str) -> None:
        user = self.get_user(username)
        if not user:
            raise KeyError("Utente non trovato.")
        self.save_user(
            username=user["username"], display_name=user["display_name"], role=user["role"],
            permissions=set(ROLE_DEFAULTS[user["role"]]), active=bool(user["active"]),
        )

    def recent_logs(self, limit: int = 200) -> list[dict[str, object]]:
        return self.database.recent_logs(limit)
