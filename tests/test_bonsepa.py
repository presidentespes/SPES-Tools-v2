from pathlib import Path

from spes_tools.parsers.banking import load_config, parse_volksbank_bonsepa


def test_bonsepa_mapping(tmp_path: Path) -> None:
    data = (
        "Stato;Data Esecuzione;Importo;Causale;Beneficiario;Conto corrente di addebito\n"
        "Eseguito;30/07/2025;827,00 EUR;compenso giugno;CIRIOTTO GIORGIA;IT16Q0585602000125571498728\n"
    ).encode("utf-8")
    cfg = load_config(Path(__file__).parents[1] / "app/spes_tools/config_abi.json")
    rows, warnings = parse_volksbank_bonsepa(data, cfg)
    assert not warnings
    assert len(rows) == 1
    row = rows[0]
    assert row.causale_abi == "26 VOLKSBANK"
    assert row.soggetto == "CIRIOTTO GIORGIA"
    assert row.desc_causale == "compenso giugno"
    assert row.dare == "827,00"
