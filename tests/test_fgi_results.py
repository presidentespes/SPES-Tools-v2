from datetime import date

from spes_tools.services.fgi_results import (
    _is_spes_row,
    _parse_italian_date,
    current_season,
)


def test_current_season_before_september():
    start, end, label = current_season(date(2026, 8, 6))
    assert start == date(2025, 9, 1)
    assert end == date(2026, 8, 31)
    assert label == "2025/2026"


def test_current_season_from_september():
    start, end, label = current_season(date(2026, 9, 1))
    assert start == date(2026, 9, 1)
    assert end == date(2027, 8, 31)
    assert label == "2026/2027"


def test_spes_detection_by_code_and_name():
    assert _is_spes_row(["1", "Mario Rossi", "000112 SPES MESTRE", "82.500"])
    assert _is_spes_row(["SPES Mestre Ginnastica A.S.D."])
    assert not _is_spes_row(["Altra società", "001234"])


def test_parse_italian_date():
    assert _parse_italian_date("21 Marzo 2026 Individuale") == date(2026, 3, 21)
