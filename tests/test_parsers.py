from pathlib import Path

from spes_tools.banking.parsers import _volksbank_rule, detect_format, parse_bcc, parse_nexi

DATA = Path(__file__).resolve().parents[1] / "tests" / "data"


def test_bcc_sample():
    path = DATA / "bcc_relaxbanking.pdf"
    assert detect_format(path) == "BCC"
    rows = parse_bcc(path)
    assert len(rows) >= 80
    assert any(row.causale_abi.endswith("BCC") for row in rows)


def test_nexi_sample():
    path = DATA / "nexi_febbraio_2025.pdf"
    assert detect_format(path) == "NEXI"
    rows = parse_nexi(path)
    assert len(rows) == 11
    assert sum(float(row.dare.replace(".", "").replace(",", ".")) for row in rows) == 2577.55


def test_volksbank_quota_rule(monkeypatch):
    monkeypatch.setenv("APPDATA", str(DATA / "tmp_appdata"))
    assert _volksbank_rule("Bonifico in entrata quota corso settembre", False) == "99 VOLKSBANK"
    assert _volksbank_rule("Bonifico in entrata rimborso", False) == "47 VOLKSBANK"
