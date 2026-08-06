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
