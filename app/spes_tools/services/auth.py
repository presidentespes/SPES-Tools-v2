from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from spes_tools.services.storage import data_dir

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
    "backup": "Backup e ripristino",
    "updates": "Aggiornamenti applicazione",
}

ROLE_DEFAULTS: dict[str, set[str]] = {
    "admin": set(PERMISSIONS),
    "segreteria": {
        "site",
        "wellness",
        "gmail_segreteria",
        "fgi_results",
        "fgi_calendar",
        "fgi_regulation",
    },
    "consiglieri": {
        "site",
        "sportivi",
        "wellness",
        "cassa_cloud",
        "spes_connect",
        "gmail_consiglio",
        "drive",
        "fgi_results",
        "fgi_calendar",
        "fgi_regulation",
        "music_gare",
        "music_awards",
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
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else data_dir() / "users.json"
        self._ensure_file()

    def _ensure_file(self) -> None:
        if self.path.exists():
            return
        users = []
        for username, role, display in (
            ("admin", "admin", "Amministratore"),
            ("segreteria", "segreteria", "Segreteria"),
            ("consiglieri", "consiglieri", "Consiglieri"),
        ):
            users.append(self._new_user_record(username, display, role, DEFAULT_PASSWORD))
        self._write({"schema": 1, "users": users})

    def _read(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
        if not isinstance(raw, dict) or not isinstance(raw.get("users"), list):
            raw = {"schema": 1, "users": []}
        return raw

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        return base64.b64encode(salt).decode("ascii"), base64.b64encode(digest).decode("ascii")

    @classmethod
    def _new_user_record(cls, username: str, display_name: str, role: str, password: str) -> dict[str, Any]:
        salt, password_hash = cls._hash_password(password)
        return {
            "username": username.strip().lower(),
            "display_name": display_name.strip() or username.strip(),
            "role": role,
            "permissions": sorted(ROLE_DEFAULTS.get(role, set())),
            "active": True,
            "must_change_password": True,
            "salt": salt,
            "password_hash": password_hash,
        }

    def list_users(self) -> list[dict[str, Any]]:
        users = self._read()["users"]
        return sorted((dict(item) for item in users if isinstance(item, dict)), key=lambda x: str(x.get("username", "")))

    def get_user(self, username: str) -> dict[str, Any] | None:
        key = username.strip().lower()
        return next((user for user in self.list_users() if str(user.get("username", "")).lower() == key), None)

    def authenticate(self, username: str, password: str) -> tuple[SessionUser | None, bool]:
        user = self.get_user(username)
        if not user or not bool(user.get("active", True)):
            return None, False
        try:
            salt = base64.b64decode(str(user["salt"]))
            expected = base64.b64decode(str(user["password_hash"]))
        except Exception:
            return None, False
        _, supplied_b64 = self._hash_password(password, salt)
        supplied = base64.b64decode(supplied_b64)
        if not hmac.compare_digest(expected, supplied):
            return None, False
        permissions = frozenset(str(value) for value in user.get("permissions", []))
        session = SessionUser(
            username=str(user["username"]),
            display_name=str(user.get("display_name") or user["username"]),
            role=str(user.get("role", "consiglieri")),
            permissions=permissions,
        )
        return session, bool(user.get("must_change_password", False))

    def set_password(self, username: str, password: str, *, must_change: bool = False) -> None:
        if len(password) < 6:
            raise ValueError("La password deve contenere almeno 6 caratteri.")
        data = self._read()
        for user in data["users"]:
            if str(user.get("username", "")).lower() == username.strip().lower():
                salt, password_hash = self._hash_password(password)
                user["salt"] = salt
                user["password_hash"] = password_hash
                user["must_change_password"] = bool(must_change)
                self._write(data)
                return
        raise KeyError("Utente non trovato.")

    def save_user(
        self,
        *,
        username: str,
        display_name: str,
        role: str,
        permissions: set[str],
        active: bool,
    ) -> None:
        username = username.strip().lower()
        if not username:
            raise ValueError("Il nome utente è obbligatorio.")
        if role not in ROLE_DEFAULTS:
            raise ValueError("Profilo non valido.")
        permissions = {item for item in permissions if item in PERMISSIONS}
        data = self._read()
        for user in data["users"]:
            if str(user.get("username", "")).lower() == username:
                user.update({
                    "display_name": display_name.strip() or username,
                    "role": role,
                    "permissions": sorted(permissions),
                    "active": bool(active),
                })
                self._write(data)
                return
        data["users"].append(self._new_user_record(username, display_name, role, DEFAULT_PASSWORD))
        data["users"][-1]["permissions"] = sorted(permissions)
        data["users"][-1]["active"] = bool(active)
        self._write(data)

    def create_user(self, username: str, display_name: str, role: str) -> None:
        if self.get_user(username):
            raise ValueError("Esiste già un utente con questo nome.")
        self.save_user(
            username=username,
            display_name=display_name,
            role=role,
            permissions=set(ROLE_DEFAULTS[role]),
            active=True,
        )

    def delete_user(self, username: str) -> None:
        key = username.strip().lower()
        if key == "admin":
            raise ValueError("L'utente admin principale non può essere eliminato.")
        data = self._read()
        data["users"] = [u for u in data["users"] if str(u.get("username", "")).lower() != key]
        self._write(data)

    def reset_permissions_to_role(self, username: str) -> None:
        user = self.get_user(username)
        if not user:
            raise KeyError("Utente non trovato.")
        self.save_user(
            username=str(user["username"]),
            display_name=str(user.get("display_name", "")),
            role=str(user.get("role", "consiglieri")),
            permissions=set(ROLE_DEFAULTS[str(user.get("role", "consiglieri"))]),
            active=bool(user.get("active", True)),
        )
