from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from spes_tools.services.storage import abi_path, history_path, rules_path, data_dir

BACKUP_FILES = (abi_path, rules_path, history_path, lambda: data_dir() / "consolle_spes.db")


def create_backup(destination: str | Path) -> Path:
    output = Path(destination)
    if output.suffix.lower() != ".zip":
        output = output.with_suffix(".zip")
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "application": "Consolle SPES Ginnastica Mestre",
        "files": [],
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path_factory in BACKUP_FILES:
            path = path_factory()
            if path.exists():
                archive.write(path, path.name)
                manifest["files"].append(path.name)
        archive.writestr("backup_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return output


def restore_backup(source: str | Path) -> list[str]:
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    allowed = {"config_abi.json", "config_regole.json", "history.json", "consolle_spes.db"}
    restored: list[str] = []
    target_dir = data_dir()

    with zipfile.ZipFile(source_path, "r") as archive:
        names = set(archive.namelist())
        if not names.intersection(allowed):
            raise ValueError("Il file selezionato non contiene una configurazione SPES valida.")
        for name in sorted(names.intersection(allowed)):
            target = target_dir / name
            temp = target.with_suffix(target.suffix + ".tmp")
            with archive.open(name) as src, temp.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            temp.replace(target)
            restored.append(name)
    return restored
