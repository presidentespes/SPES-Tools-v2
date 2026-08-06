from __future__ import annotations

from pathlib import Path

from spes_tools.services import storage


def test_archive_folders_are_separated(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    base = tmp_path / "exports"
    base.mkdir()
    storage.set_export_directory(base)

    assert storage.archive_directory("BCC", 2025) == base / "Storico operazioni" / "BCC" / "2025"
    assert storage.archive_directory("VOLKSBANK", "2026") == base / "Storico operazioni" / "VOLKSBANK" / "2026"
    assert storage.archive_directory("NEXI", 2025) == base / "Storico operazioni" / "NEXI" / "2025"
    assert storage.archive_directory("CASSA", 2026) == base / "Storico operazioni" / "CASSA" / "2026"

    for folder in (
        storage.archive_directory("BCC", 2025),
        storage.archive_directory("VOLKSBANK", 2026),
        storage.archive_directory("NEXI", 2025),
        storage.archive_directory("CASSA", 2026),
    ):
        assert folder.is_dir()
