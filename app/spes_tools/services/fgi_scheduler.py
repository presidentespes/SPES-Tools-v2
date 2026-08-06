from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TASK_NAME = "SPES Aggiornamento Risultati FGI"


def ensure_weekly_fgi_task() -> bool:
    """Ensure a Windows task updates FGI results every Monday at 01:00."""
    if os.name != "nt":
        return False
    executable = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        command = f'"{executable}" --update-fgi'
    else:
        launcher = Path(sys.argv[0]).resolve()
        command = f'"{executable}" "{launcher}" --update-fgi'
    try:
        completed = subprocess.run(
            [
                "schtasks",
                "/Create",
                "/F",
                "/SC",
                "WEEKLY",
                "/D",
                "MON",
                "/ST",
                "01:00",
                "/TN",
                TASK_NAME,
                "/TR",
                command,
            ],
            check=False,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        return False
    return completed.returncode == 0
