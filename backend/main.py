from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from spes_tools.services.auth import SessionUser, UserStore  # noqa: E402

from backend.modules import MODULES  # noqa: E402
from backend.security import TokenError, create_token, verify_token  # noqa: E402

API_VERSION = "6.0.6"
DB_PATH = Path(os.environ.get("SPES_API_DB", ROOT / "backend" / "data" / "consolle_spes_server.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
MOBILE_DIR = ROOT / "mobile"
store = UserStore(DB_PATH)

app = FastAPI(title="Consolle SPES API", version=API_VERSION, docs_url="/api/docs", redoc_url=None)
origins = [item.strip() for item in os.environ.get("SPES_ALLOWED_ORIGINS", "http://localhost:8080").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    must_change_password: bool
    user: dict[str, object]


def _session_from_header(authorization: Annotated[str | None, Header()] = None) -> SessionUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Accesso richiesto.")
    try:
        payload = verify_token(authorization.split(" ", 1)[1].strip())
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    user = store.get_user(payload.username)
    if not user or not user["active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utente non disponibile.")
    return SessionUser(
        username=str(user["username"]),
        display_name=str(user["display_name"]),
        role=str(user["role"]),
        permissions=frozenset(str(item) for item in user["permissions"]),
    )


def _user_dict(user: SessionUser) -> dict[str, object]:
    return {
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "permissions": sorted(user.permissions),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": API_VERSION}


@app.post("/api/auth/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    user, must_change = store.authenticate(request.username, request.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide.")
    return LoginResponse(
        token=create_token(user.username, user.role),
        must_change_password=must_change,
        user=_user_dict(user),
    )


@app.post("/api/auth/change-password")
def change_password(request: ChangePasswordRequest, user: Annotated[SessionUser, Depends(_session_from_header)]) -> dict[str, str]:
    verified, _ = store.authenticate(user.username, request.current_password)
    if verified is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password corrente errata.")
    store.set_password(user.username, request.new_password, must_change=False)
    return {"status": "ok"}


@app.get("/api/me")
def me(user: Annotated[SessionUser, Depends(_session_from_header)]) -> dict[str, object]:
    record = store.get_user(user.username) or {}
    result = _user_dict(user)
    result["must_change_password"] = bool(record.get("must_change_password", False))
    return result


@app.get("/api/modules")
def modules(user: Annotated[SessionUser, Depends(_session_from_header)]) -> dict[str, object]:
    visible = []
    for permission in sorted(user.permissions):
        module = MODULES.get(permission)
        if module:
            visible.append({"permission": permission, **module})
    return {"items": visible}


@app.get("/api/dashboard")
def dashboard(user: Annotated[SessionUser, Depends(_session_from_header)]) -> dict[str, object]:
    logs = store.recent_logs(100)
    return {
        "greeting": f"Benvenuto, {user.display_name}",
        "role": user.role,
        "cards": [
            {"key": "modules", "label": "Funzioni disponibili", "value": len(user.permissions), "icon": "🧩"},
            {"key": "activity", "label": "Attività registrate", "value": len(logs), "icon": "📝"},
            {"key": "fgi", "label": "Area FGI", "value": "Attiva" if "fgi_results" in user.permissions else "Non visibile", "icon": "🏅"},
            {"key": "security", "label": "Profilo", "value": user.role.title(), "icon": "🔐"},
        ],
    }


@app.get("/api/admin/users")
def list_users(user: Annotated[SessionUser, Depends(_session_from_header)]) -> dict[str, object]:
    if not user.can("users_manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permesso insufficiente.")
    return {"items": store.list_users()}


# La PWA e le API sono pubblicate dallo stesso dominio.
# Il mount viene aggiunto per ultimo, cosi le rotte /api restano prioritarie.
if MOBILE_DIR.exists():
    app.mount("/", StaticFiles(directory=MOBILE_DIR, html=True), name="mobile")
