from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def build_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("SPES_API_SECRET", "test-secret-0123456789-abcdefghijklmnopqrstuvwxyz")
    monkeypatch.setenv("SPES_API_DB", str(tmp_path / "server.db"))
    monkeypatch.setenv("SPES_ALLOWED_ORIGINS", "http://localhost:8080")
    for name in ["backend.main"]:
        sys.modules.pop(name, None)
    module = importlib.import_module("backend.main")
    return TestClient(module.app)


def test_health(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["version"] == "6.0.5"


def test_admin_login_and_modules(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    response = client.post("/api/auth/login", json={"username": "admin", "password": "gamba"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["must_change_password"] is True
    headers = {"Authorization": f"Bearer {payload['token']}"}
    me = client.get("/api/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
    modules = client.get("/api/modules", headers=headers)
    assert modules.status_code == 200
    permissions = {item["permission"] for item in modules.json()["items"]}
    assert "homebank_bcc" in permissions
    assert "users_manage" in permissions


def test_segreteria_cannot_list_users(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    response = client.post("/api/auth/login", json={"username": "segreteria", "password": "gamba"})
    token = response.json()["token"]
    denied = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 403
