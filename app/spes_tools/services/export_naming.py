from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Protocol


class HasMovementDate(Protocol):
    data: str


MONTH_NAMES = {
    1: "gen", 2: "feb", 3: "mar", 4: "apr", 5: "mag", 6: "giu",
    7: "lug", 8: "ago", 9: "set", 10: "ott", 11: "nov", 12: "dic",
}


def build_export_filename(bank_format: str, movements: list[HasMovementDate]) -> str:
    bank = _bank_slug(bank_format)
    dates = [parsed for movement in movements if (parsed := _parse_movement_date(movement.data))]
    if not dates:
        return f"{bank}_movimenti.csv"

    dates.sort()
    start = dates[0]
    end = dates[-1]
    if start.year == end.year and start.month == end.month:
        period = f"{MONTH_NAMES[start.month]}_{start.year}"
    elif start.year == end.year:
        period = f"{MONTH_NAMES[start.month]}-{MONTH_NAMES[end.month]}_{start.year}"
    else:
        period = (
            f"{MONTH_NAMES[start.month]}_{start.year}-"
            f"{MONTH_NAMES[end.month]}_{end.year}"
        )
    return f"{bank}_{period}.csv"


def available_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _bank_slug(bank_format: str) -> str:
    value = bank_format.strip().lower()
    if "bonifici_sepa" in value:
        return "volksbank_sepa"
    if "volksbank" in value:
        return "volksbank"
    if "bcc" in value:
        return "bcc"
    if "nexi" in value:
        return "nexi"
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value or "banca"


def _parse_movement_date(value: str) -> datetime | None:
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
