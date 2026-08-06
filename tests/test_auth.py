from pathlib import Path

from spes_tools.services.auth import DEFAULT_PASSWORD, ROLE_DEFAULTS, UserStore


def test_default_users_and_forced_password_change(tmp_path: Path) -> None:
    store = UserStore(tmp_path / "users.json")
    session, must_change = store.authenticate("admin", DEFAULT_PASSWORD)
    assert session is not None
    assert session.role == "admin"
    assert must_change is True
    assert session.can("users_manage")


def test_password_change_and_custom_permissions(tmp_path: Path) -> None:
    store = UserStore(tmp_path / "users.json")
    store.set_password("segreteria", "nuova-password", must_change=False)
    session, must_change = store.authenticate("segreteria", "nuova-password")
    assert session is not None and must_change is False
    assert session.permissions == frozenset(ROLE_DEFAULTS["segreteria"])

    store.save_user(
        username="segreteria",
        display_name="Segreteria prova",
        role="segreteria",
        permissions={"wellness", "cash"},
        active=True,
    )
    session, _ = store.authenticate("segreteria", "nuova-password")
    assert session is not None
    assert session.can("cash")
    assert not session.can("fgi_results")
