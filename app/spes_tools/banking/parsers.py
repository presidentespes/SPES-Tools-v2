from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from spes_tools.services.storage import load_abi_config


@dataclass
class Movement:
    data: str = ""
    valuta: str = ""
    dare: str = ""
    avere: str = ""
    causale: str = ""
    causale_abi: str = ""
    desc_causale: str = ""
    soggetto: str = ""
    iban: str = ""
    spuntato: str = ""


HEADERS = [
    "DATA", "VALUTA", "DARE", "AVERE", "CAUSALE", "CAUSALE ABI",
    "desc.causale", "SOGGETTO", "IBAN", "SPUNTATO",
]


def detect_format(path: str | Path) -> str:
    p = Path(path)
    suffix = p.suffix.lower()
    name = p.name.lower()
    if suffix == ".pdf":
        text = _read_pdf_text(p).lower()
        if "nexi" in text or "dettagliodeisuoimovimenti" in _compact(text):
            return "NEXI"
        if "relaxbanking" in text or "credito cooperativo" in text:
            return "BCC"
        return "PDF"
    if suffix in {".csv", ".txt", ".xls"}:
        sample = p.read_text(encoding="utf-8-sig", errors="ignore")[:5000].lower()
        if "beneficiario" in sample and ("bonsepa" in name or "data esecuzione" in sample):
            return "BONIFICI_SEPA_VOLKSBANK"
        if "data contabile" in sample and "data valuta" in sample:
            return "VOLKSBANK"
        return "CSV"
    return "SCONOSCIUTO"


def parse_file(path: str | Path) -> tuple[str, list[Movement]]:
    fmt = detect_format(path)
    if fmt == "NEXI":
        rows = parse_nexi(path)
        if not rows:
            raise ValueError(
                "Il PDF e stato riconosciuto come Nexi, ma non sono stati trovati movimenti. "
                "Verificare che sia un estratto conto con testo selezionabile."
            )
        return fmt, rows
    if fmt == "BCC":
        return fmt, parse_bcc(path)
    if fmt == "BONIFICI_SEPA_VOLKSBANK":
        return fmt, parse_bonsepa(path)
    if fmt == "VOLKSBANK":
        return fmt, parse_volksbank(path)
    raise ValueError(f"Formato non supportato: {fmt}")


def export_teamsystem_csv(path: str | Path, rows: Iterable[Movement]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";", lineterminator="\n")
        writer.writerow(HEADERS)
        for m in rows:
            writer.writerow([
                m.data, m.valuta, m.dare, m.avere, m.causale,
                m.causale_abi, m.desc_causale, m.soggetto,
                m.iban, m.spuntato,
            ])


def parse_nexi(path: str | Path) -> list[Movement]:
    """Parse Nexi statements even when PDF extraction removes most spaces.

    Nexi PDFs commonly expose the detail page as one long text run, e.g.
    ``06/02/25Eni... 948,3208/02/25Hotel...``.  The parser therefore
    searches between successive dates rather than relying on line breaks.
    """
    text = _read_pdf_text(Path(path))
    compact = _compact(text)
    cfg = load_abi_config()["NEXI"]

    detail_marker = "DETTAGLIODEISUOIMOVIMENTI"
    start = compact.upper().find(detail_marker)
    detail = compact[start + len(detail_marker):] if start >= 0 else compact

    # Remove the table heading, preserving the movement dates that follow it.
    detail = re.sub(
        r"^DataDescrizioneImportoinEuro(?:ImportoinaltrevaluteCambio)?",
        "",
        detail,
        flags=re.IGNORECASE,
    )

    movement_pattern = re.compile(
        r"(\d{2}/\d{2}/\d{2})"                 # transaction date
        r"(.*?)"                                # description
        r"(\d{1,3}(?:\.\d{3})*,\d{2})"       # amount
        r"(?=\d{2}/\d{2}/\d{2}|TOTALESPESE|$)",
        flags=re.IGNORECASE | re.DOTALL,
    )

    rows: list[Movement] = []
    for date, raw_description, amount in movement_pattern.findall(detail):
        description = _humanize_nexi_description(raw_description)
        if not description or description.upper().startswith("TOTALE"):
            continue
        rows.append(Movement(
            data=_date_yy_to_yyyy(date),
            valuta=_date_yy_to_yyyy(date),
            dare=amount,
            causale=description,
            causale_abi=cfg["acquisto"],
            desc_causale="Acquisto carta",
        ))

    # Add statement charges from the summary page.  These are not listed on
    # the card-detail page but are needed to reconcile the bank debit.
    statement_date = _nexi_statement_end_date(compact)
    stamp = _find_compact_amount(compact, "Impostadibollo")
    if stamp:
        rows.append(Movement(
            data=statement_date,
            valuta=statement_date,
            dare=stamp,
            causale="IMPOSTA DI BOLLO",
            causale_abi=cfg["bollo"],
            desc_causale="Imposta di bollo",
        ))
    delivery = _find_compact_amount(compact, "Speseinvioestrattoconto")
    if delivery:
        rows.append(Movement(
            data=statement_date,
            valuta=statement_date,
            dare=delivery,
            causale="SPESE INVIO ESTRATTO CONTO",
            causale_abi=cfg["spese"],
            desc_causale="Spese estratto conto",
        ))
    return rows


def parse_bcc(path: str | Path) -> list[Movement]:
    text = _read_pdf_text(Path(path))
    compact = text.replace(" ", "")
    iban_match = re.search(r"\bIT\d{2}[A-Z]\d{22}\b", compact)
    iban = iban_match.group(0) if iban_match else ""
    pattern = re.compile(
        r"(?m)^(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+"
        r"(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+(.+)$"
    )
    rows: list[Movement] = []
    for data, valuta, raw, description in pattern.findall(text):
        negative = raw.startswith("-")
        amount = raw.lstrip("-")
        abi, label = _bcc_rule(description, negative)
        rows.append(Movement(
            data=data, valuta=valuta,
            dare=amount if negative else "",
            avere=amount if not negative else "",
            causale=" ".join(description.split()),
            causale_abi=abi, desc_causale=label, iban=iban,
        ))
    return rows


def parse_bonsepa(path: str | Path) -> list[Movement]:
    rows = _read_delimited(Path(path))
    result: list[Movement] = []
    for row in rows:
        n = {str(k).strip().lower(): (v or "").strip() for k, v in row.items()}
        amount = _first(n, "importo", "importo disposizione")
        if not amount:
            continue
        date = _normalize_date(_first(n, "data esecuzione", "data", "data disposizione"))
        result.append(Movement(
            data=date, valuta=date, dare=_normalize_amount(amount),
            causale="Bonifico SEPA", causale_abi=load_abi_config()["VOLKSBANK"]["bonifico_sepa"],
            desc_causale=_first(n, "causale", "descrizione", "motivo pagamento"),
            soggetto=_first(n, "beneficiario", "nome beneficiario", "ordinante"),
            iban=_first(n, "iban beneficiario", "iban"),
        ))
    return result


def parse_volksbank(path: str | Path) -> list[Movement]:
    rows = _read_delimited(Path(path))
    result: list[Movement] = []
    for row in rows:
        n = {str(k).strip().lower(): (v or "").strip() for k, v in row.items()}
        raw = _first(n, "importo")
        if not raw:
            continue
        negative = raw.startswith("-")
        amount = _normalize_amount(raw)
        description = _first(n, "descrizione", "causale")
        result.append(Movement(
            data=_normalize_date(_first(n, "data contabile", "data")),
            valuta=_normalize_date(_first(n, "data valuta", "valuta")),
            dare=amount if negative else "", avere=amount if not negative else "",
            causale=description,
            causale_abi=_volksbank_rule(description, negative),
            desc_causale=description,
        ))
    return result


def _read_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_delimited(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    lines = text.splitlines()
    first = lines[0] if lines else ""
    delimiter = "\t" if "\t" in first else ";" if ";" in first else ","
    return list(csv.DictReader(lines, delimiter=delimiter))


def _first(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        if row.get(key):
            return row[key]
    return ""


def _normalize_date(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        year, month, day = value.split("-")
        return f"{day}/{month}/{year}"
    return value


def _normalize_amount(value: str) -> str:
    value = value.strip().replace("EUR", "").replace("€", "").replace(" ", "").lstrip("-")
    if "," in value:
        return value
    try:
        return f"{float(value):.2f}".replace(".", ",")
    except ValueError:
        return value


def _date_yy_to_yyyy(value: str) -> str:
    day, month, year = value.split("/")
    return f"{day}/{month}/20{year}"


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _humanize_nexi_description(value: str) -> str:
    # The PDF often removes all spaces. Preserve known punctuation and add
    # limited spacing around common merchant tokens without guessing names.
    value = value.strip(" -")
    value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    value = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", value)
    value = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _find_compact_amount(compact: str, label: str) -> str:
    match = re.search(re.escape(label) + r"(\d{1,3}(?:\.\d{3})*,\d{2})", compact, re.IGNORECASE)
    return match.group(1) if match else ""


def _nexi_statement_end_date(compact: str) -> str:
    match = re.search(r"Debitoresiduoal(\d{2}/\d{2}/\d{4})", compact, re.IGNORECASE)
    if match:
        return match.group(1)
    # Fallback to the statement heading, e.g. Milano,28Febbraio2025.
    month_names = {
        "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
        "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
        "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12",
    }
    match = re.search(r"Milano,?(\d{1,2})([A-Za-z]+)(\d{4})", compact, re.IGNORECASE)
    if match:
        day, month_name, year = match.groups()
        month = month_names.get(month_name.lower())
        if month:
            return f"{int(day):02d}/{month}/{year}"
    return ""


def _bcc_rule(description: str, negative: bool) -> tuple[str, str]:
    d = description.lower()
    cfg = load_abi_config()["BCC"]
    if "incassi pagobancomat" in d or "incassi internazionali" in d:
        return cfg["pos"], "Incasso POS"
    if "commission" in d:
        return cfg["commissioni"], "Commissioni"
    if "bollo" in d:
        return cfg["bollo"], "Bollo"
    if "sdd" in d:
        return cfg["sdd"], "Addebito diretto"
    if "canone" in d:
        return cfg["canone"], "Canone"
    if "bonifico a vs favore" in d and not negative:
        return cfg["bonifico_entrata"], "Bonifico in entrata"
    if "bonifico" in d and negative:
        return cfg["bonifico_uscita"], "Bonifico in uscita"
    return (cfg["altro_uscita"], "Altro movimento") if negative else (cfg["altro_entrata"], "Entrata")


def _volksbank_rule(description: str, negative: bool) -> str:
    d = description.lower()
    cfg = load_abi_config()["VOLKSBANK"]
    if "commission" in d:
        return cfg["commissioni"]
    if "sdd" in d:
        return cfg["sdd"]
    if "bonifico" in d:
        return cfg["bonifico_uscita"] if negative else cfg["bonifico_entrata"]
    return cfg["altro_uscita"] if negative else cfg["altro_entrata"]
