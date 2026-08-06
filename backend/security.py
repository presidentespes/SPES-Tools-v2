from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any


class TokenError(ValueError):
    pass


@dataclass(frozen=True)
class TokenPayload:
    username: str
    role: str
    expires_at: int


def _secret() -> bytes:
    value = os.environ.get("SPES_API_SECRET", "").strip()
    if len(value) < 32:
        raise RuntimeError("SPES_API_SECRET deve contenere almeno 32 caratteri.")
    return value.encode("utf-8")


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_token(username: str, role: str, lifetime_seconds: int = 8 * 60 * 60) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": int(time.time()) + max(300, lifetime_seconds),
        "iat": int(time.time()),
    }
    body = _encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _encode(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{signature}"


def verify_token(token: str) -> TokenPayload:
    try:
        body, supplied_signature = token.split(".", 1)
    except ValueError as exc:
        raise TokenError("Token non valido.") from exc
    expected = _encode(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, supplied_signature):
        raise TokenError("Firma del token non valida.")
    try:
        data: dict[str, Any] = json.loads(_decode(body))
        username = str(data["sub"])
        role = str(data["role"])
        expires_at = int(data["exp"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TokenError("Contenuto del token non valido.") from exc
    if expires_at <= int(time.time()):
        raise TokenError("Sessione scaduta.")
    return TokenPayload(username=username, role=role, expires_at=expires_at)
