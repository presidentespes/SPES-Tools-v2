from spes_tools.services.compensation import (
    CATEGORY_PENSIONER, ordinary_from_gross, sport_from_gross, threshold_portion,
)


def test_threshold_below_5000():
    taxable, remaining = threshold_portion(3000, 1500, 5000)
    assert taxable == 0
    assert remaining == 2000


def test_threshold_crosses_5000():
    taxable, remaining = threshold_portion(4800, 1000, 5000)
    assert taxable == 800
    assert remaining == 200


def test_sport_no_withholding_below_threshold():
    result = sport_from_gross(gross=1000, previous=3000, no_other_coverage=True, tax_rate_pct=23)
    assert result.contributory_part == 0
    assert result.previdential == 0
    assert result.other_contrib == 0
    assert result.net == 1000


def test_pensioner_threshold():
    result = ordinary_from_gross(category=CATEGORY_PENSIONER, gross=1000, previous=4800,
                                 total_rate_pct=24, taxable_base_pct=50)
    assert result.contributory_part == 800
    assert result.previdential == 32
    assert result.net == 968
