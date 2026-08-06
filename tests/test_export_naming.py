from spes_tools.banking.parsers import Movement
from spes_tools.services.export_naming import build_export_filename


def test_single_month_bcc_filename():
    rows = [Movement(data="01/02/2025"), Movement(data="28/02/2025")]
    assert build_export_filename("BCC", rows) == "bcc_feb_2025.csv"


def test_month_range_volksbank_filename():
    rows = [Movement(data="01/11/2025"), Movement(data="31/12/2025")]
    assert build_export_filename("VOLKSBANK", rows) == "volksbank_nov-dic_2025.csv"


def test_nexi_filename_from_short_year():
    rows = [Movement(data="06/02/25"), Movement(data="27/02/25")]
    assert build_export_filename("NEXI", rows) == "nexi_feb_2025.csv"
