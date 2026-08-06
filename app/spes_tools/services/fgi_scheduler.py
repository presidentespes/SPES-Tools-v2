from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RESULTS_TASK_NAME = "SPES Aggiornamento Risultati FGI"
CALENDAR_TASK_NAME = "SPES Controllo Calendario FGI Veneto"


def _command(argument: str) -> str:
    executable = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        return f'"{executable}" {argument}'
    launcher = Path(sys.argv[0]).resolve()
    return f'"{executable}" "{launcher}" {argument}'


def _ensure_weekly_task(name: str, day: str, argument: str) -> bool:
    if os.name != "nt":
        return False
    try:
        completed = subprocess.run(
            [
                "schtasks",
                "/Create",
                "/F",
                "/SC",
                "WEEKLY",
                "/D",
                day,
                "/ST",
                "01:00",
                "/TN",
                name,
                "/TR",
                _command(argument),
            ],
            check=False,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        return False
    return completed.returncode == 0


def ensure_weekly_fgi_task() -> bool:
    """Aggiorna i risultati FGI ogni lunedì alle 01:00."""
    return _ensure_weekly_task(RESULTS_TASK_NAME, "MON", "--update-fgi")


def ensure_weekly_fgi_calendar_task() -> bool:
    """Controlla la homepage FGI Veneto ogni domenica alle 01:00."""
    return _ensure_weekly_task(CALENDAR_TASK_NAME, "SUN", "--update-fgi-calendar")


def start_initial_fgi_update_if_needed() -> bool:
    """Avvia subito un aggiornamento in background se l'archivio locale manca o e obsoleto."""
    from spes_tools.services.fgi_results import results_cache_needs_refresh

    if not results_cache_needs_refresh(max_age_days=7):
        return False
    try:
        if getattr(sys, "frozen", False):
            command = [str(Path(sys.executable).resolve()), "--update-fgi"]
        else:
            command = [
                str(Path(sys.executable).resolve()),
                str(Path(sys.argv[0]).resolve()),
                "--update-fgi",
            ]
        kwargs: dict[str, object] = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "close_fds": True,
        }
        if os.name == "nt":
            kwargs["creationflags"] = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
            )
        subprocess.Popen(command, **kwargs)
    except OSError:
        return False
    return True
