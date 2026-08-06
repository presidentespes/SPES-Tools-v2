from pathlib import Path

from spes_tools.services.auth import DEFAULT_PASSWORD, UserStore
from spes_tools.services.database import Database


def test_sqlite_schema_and_activity_log(tmp_path: Path) -> None:
    path = tmp_path / "consolle_spes.db"
    store = UserStore(path)
    assert path.read_bytes().startswith(b"SQLite format 3")
    session, must_change = store.authenticate("admin", DEFAULT_PASSWORD)
    assert session is not None and must_change is True
    logs = store.recent_logs()
    assert any(item["action"] == "login_success" for item in logs)


def test_database_settings_table_exists(tmp_path: Path) -> None:
    database = Database(tmp_path / "settings.db")
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO settings(key, value, updated_at) VALUES('theme', 'dark', '2026-08-06T00:00:00')"
        )
        value = connection.execute("SELECT value FROM settings WHERE key='theme'").fetchone()[0]
    assert value == "dark"
