from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

APP_NAME = "SPES_Configuratore_Contabile"

DEFAULT_RULES = {
    "VOLKSBANK": {
        "quota_corso_keywords": ["quota", "mensile", "mensilita", "mensilità", "corso"],
    }
}

DEFAULT_ABI: dict[str, dict[str, str]] = {
    "NEXI": {
        "acquisto": "26 NEXI",
        "bollo": "19 NEXI",
        "spese": "16 NEXI",
    },
    "BCC": {
        "pos": "09 BCC",
        "commissioni": "16 BCC",
        "bollo": "19 BCC",
        "bonifico_uscita": "26 BCC",
        "bonifico_entrata": "47 BCC",
        "sdd": "50 BCC",
        "canone": "66 BCC",
        "altro_uscita": "66 BCC",
        "altro_entrata": "47 BCC",
    },
    "VOLKSBANK": {
        "pos": "09 VOLKSBANK",
        "commissioni": "16 VOLKSBANK",
        "bonifico_uscita": "26 VOLKSBANK",
        "bonifico_entrata": "47 VOLKSBANK",
        "quota_corso_entrata": "99 VOLKSBANK",
        "sdd": "50 VOLKSBANK",
        "altro_uscita": "66 VOLKSBANK",
        "altro_entrata": "09 VOLKSBANK",
        "bonifico_sepa": "26 VOLKSBANK",
    },
    "CASSA": {
        "incasso_quota": "35CASSA",
        "incasso_generico": "36CASSA",
        "rimborso_ricevuto": "37CASSA",
        "banca_a_cassa": "38CASSA",
        "cassa_a_banca": "39CASSA",
        "spesa_generica": "40CASSA",
        "rimborso_spese": "41CASSA",
        "anticipo_cassa": "42CASSA",
        "restituzione_anticipo": "43CASSA",
        "giroconto_interno": "44CASSA",
        "rettifica_entrata": "45CASSA",
        "rettifica_uscita": "46CASSA",
    },
}


def data_dir() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / ".spes_tools"
    path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def abi_path() -> Path:
    return data_dir() / "config_abi.json"


def history_path() -> Path:
    return data_dir() / "history.json"


def rules_path() -> Path:
    return data_dir() / "config_regole.json"


def load_rules_config() -> dict[str, dict[str, list[str]]]:
    path = rules_path()
    if not path.exists():
        save_rules_config(DEFAULT_RULES)
        return {bank: {key: list(values) for key, values in cfg.items()} for bank, cfg in DEFAULT_RULES.items()}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = {}
    result = {bank: {key: list(values) for key, values in cfg.items()} for bank, cfg in DEFAULT_RULES.items()}
    for bank, cfg in raw.items():
        if not isinstance(cfg, dict):
            continue
        for key, values in cfg.items():
            if isinstance(values, list):
                result.setdefault(str(bank), {})[str(key)] = [str(v).strip() for v in values if str(v).strip()]
    return result


def save_rules_config(config: dict[str, dict[str, list[str]]]) -> None:
    rules_path().write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def reset_rules_config() -> dict[str, dict[str, list[str]]]:
    save_rules_config(DEFAULT_RULES)
    return {bank: {key: list(values) for key, values in cfg.items()} for bank, cfg in DEFAULT_RULES.items()}


def load_abi_config() -> dict[str, dict[str, str]]:
    path = abi_path()
    if not path.exists():
        save_abi_config(DEFAULT_ABI)
        return _deepcopy(DEFAULT_ABI)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _deepcopy(DEFAULT_ABI)

    result = _deepcopy(DEFAULT_ABI)
    for bank, values in raw.items():
        if isinstance(values, dict):
            result.setdefault(bank, {}).update({str(k): str(v) for k, v in values.items()})
    return result


def save_abi_config(config: dict[str, dict[str, str]]) -> None:
    abi_path().write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def reset_abi_config() -> dict[str, dict[str, str]]:
    save_abi_config(DEFAULT_ABI)
    return _deepcopy(DEFAULT_ABI)


def load_history() -> list[dict[str, Any]]:
    path = history_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def add_history(
    *,
    module: str,
    source: str,
    output: str,
    rows: int,
    details: str = "",
) -> None:
    history = load_history()
    history.insert(0, {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "module": module,
        "source": source,
        "output": output,
        "rows": int(rows),
        "details": details,
    })
    del history[500:]
    history_path().write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_history() -> None:
    history_path().write_text("[]", encoding="utf-8")


def _deepcopy(value: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    return {bank: dict(items) for bank, items in value.items()}
