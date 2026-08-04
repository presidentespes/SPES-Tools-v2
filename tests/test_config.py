import json
from pathlib import Path


def test_expected_abi_profiles() -> None:
    cfg = json.loads((Path(__file__).parents[1] / "app/spes_tools/config_abi.json").read_text(encoding="utf-8"))
    assert cfg["NEXI"]["acquisto"]["code"] == "26 NEXI"
    assert cfg["BCC"]["bonifico_entrata"]["code"] == "47 BCC"
    assert cfg["BCC"]["bonifico_uscita"]["code"] == "26 BCC"
    assert cfg["VOLKSBANK"]["bonifico_uscita"]["code"] == "26 VOLKSBANK"
