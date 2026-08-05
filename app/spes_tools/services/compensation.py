from __future__ import annotations

from dataclasses import dataclass

CATEGORY_EMPLOYEE = "Lavoratore dipendente"
CATEGORY_PENSIONER = "Pensionato"
CATEGORY_SPORT = "Lavoratore sportivo"

SPORT_NO_OTHER_COVERAGE = "Nessuna altra copertura previdenziale"
SPORT_PENSION_OR_OTHER = "Pensionato / altra copertura previdenziale"

CONTRIBUTION_THRESHOLD = 5_000.0
TAX_THRESHOLD = 15_000.0


@dataclass
class Calculation:
    category: str
    direction: str
    input_amount: float
    gross: float
    net: float
    previdential: float = 0.0
    other_contrib: float = 0.0
    taxes: float = 0.0
    previous_gross: float = 0.0
    cumulative_gross: float = 0.0
    franchise_remaining: float = 0.0
    contributory_part: float = 0.0
    note: str = ""


def threshold_portion(previous: float, current: float, threshold: float) -> tuple[float, float]:
    previous = max(0.0, previous)
    current = max(0.0, current)
    before = max(0.0, previous - threshold)
    after = max(0.0, previous + current - threshold)
    taxable = max(0.0, min(current, after - before))
    remaining = max(0.0, threshold - previous)
    return round(taxable, 2), round(remaining, 2)


def worker_share(total_rate_pct: float, taxable_base_pct: float) -> float:
    return (total_rate_pct / 100.0) * (taxable_base_pct / 100.0) / 3.0


def ordinary_from_gross(*, category: str, gross: float, previous: float,
                        total_rate_pct: float, taxable_base_pct: float) -> Calculation:
    gross = max(0.0, gross)
    if category == CATEGORY_PENSIONER:
        contributory, remaining = threshold_portion(previous, gross, CONTRIBUTION_THRESHOLD)
    else:
        previous = 0.0
        contributory, remaining = gross, 0.0
    previdential = round(contributory * worker_share(total_rate_pct, taxable_base_pct), 2)
    return Calculation(
        category=category, direction="Lordo → Netto", input_amount=gross,
        gross=round(gross, 2), net=round(gross - previdential, 2),
        previdential=previdential, previous_gross=round(previous, 2),
        cumulative_gross=round(previous + gross, 2),
        franchise_remaining=remaining, contributory_part=contributory,
        note=("Simulazione contributiva. Per il profilo Pensionato la franchigia annua "
              "di EUR 5.000 è applicata prima delle trattenute. Verificare con il consulente."),
    )


def sport_from_gross(*, gross: float, previous: float, no_other_coverage: bool,
                     tax_rate_pct: float) -> Calculation:
    gross = max(0.0, gross)
    contributory, remaining = threshold_portion(previous, gross, CONTRIBUTION_THRESHOLD)
    ivs_rate = 0.25 if no_other_coverage else 0.24
    previdential = round(contributory * ivs_rate * 0.50 / 3.0, 2)
    other = round(contributory * 0.0203 / 3.0, 2) if no_other_coverage else 0.0
    current_taxable, _ = threshold_portion(previous, gross, TAX_THRESHOLD)
    taxes = round(current_taxable * tax_rate_pct / 100.0, 2)
    return Calculation(
        category=CATEGORY_SPORT, direction="Lordo → Netto", input_amount=gross,
        gross=round(gross, 2), net=round(gross - previdential - other - taxes, 2),
        previdential=previdential, other_contrib=other, taxes=taxes,
        previous_gross=round(previous, 2), cumulative_gross=round(previous + gross, 2),
        franchise_remaining=remaining, contributory_part=contributory,
        note=("Soglia contributiva annua EUR 5.000; IVS sul 50% dell'imponibile fino al 2027; "
              "quota collaboratore 1/3. Stima fiscale sulla quota oltre EUR 15.000."),
    )


def gross_for_target(target_net: float, calculator) -> Calculation:
    target = round(max(0.0, target_net), 2)
    low = target
    high = max(target + 100.0, target * 1.30)
    while calculator(high).net < target:
        high *= 1.5
        if high > 100_000_000:
            raise ValueError("Impossibile trovare il lordo con i dati inseriti.")
    for _ in range(100):
        mid = (low + high) / 2.0
        if calculator(mid).net < target:
            low = mid
        else:
            high = mid
    gross = round(high, 2)
    result = calculator(gross)
    for cents in range(-15, 16):
        candidate = calculator(round(gross + cents / 100.0, 2))
        if candidate.net == target:
            result = candidate
            break
    result.direction = "Netto → Lordo"
    result.input_amount = target
    return result
