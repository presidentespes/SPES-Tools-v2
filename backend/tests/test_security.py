from __future__ import annotations

import os

import pytest

from backend.security import TokenError, create_token, verify_token


def test_signed_token(monkeypatch):
    monkeypatch.setenv("SPES_API_SECRET", "test-secret-0123456789-abcdefghijklmnopqrstuvwxyz")
    token = create_token("admin", "admin")
    payload = verify_token(token)
    assert payload.username == "admin"
    assert payload.role == "admin"


def test_rejects_modified_token(monkeypatch):
    monkeypatch.setenv("SPES_API_SECRET", "test-secret-0123456789-abcdefghijklmnopqrstuvwxyz")
    token = create_token("admin", "admin")
    with pytest.raises(TokenError):
        verify_token(token + "x")
