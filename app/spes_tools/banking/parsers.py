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
        if "nexi" in text:
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
        return fmt, parse_nexi(path)
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
    """Legge gli estratti Nexi anche quando il testo PDF spezza le righe.

    Il parser cerca blocchi che iniziano con una data e usa l'ultimo importo
    presente nel blocco come importo del movimento. In questo modo funziona
    sia con righe singole sia con descrizioni distribuite su piu righe.
    """
    text = _read_pdf_text(Path(path))
    normalized = text.replace("\u00a0", " ").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    date_re = r"\d{2}[/-]\d{2}[/-]\d{2,4}"
    block_pattern = re.compile(
        rf"(?ms)(?P<date>{date_re})\s+(?P<body>.*?)(?=(?:^{date_re}\s+)|\Z)"
    )
    amount_pattern = re.compile(
        r"(?<!\d)(?:EUR\s*|€\s*)?(-?\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)",
        re.IGNORECASE,
    )

    cfg = load_abi_config()["NEXI"]
    rows: list[Movement] = []
    seen: set[tuple[str, str, str]] = set()

    for match in block_pattern.finditer(normalized):
        raw_date = match.group("date")
        body = match.group("body")
        amounts = list(amount_pattern.finditer(body))
        if not amounts:
            continue

        amount_match = amounts[-1]
        amount = amount_match.group(1).lstrip("-")
        description = body[:amount_match.start()]
        description = " ".join(description.replace("\n", " ").split())
        upper = description.upper()

        if not description:
            continue
        if any(token in upper for token in (
            "TOTALE SPESE", "TOTALE MOVIMENTI", "SALDO", "IMPORTO ADDEBITATO",
            "PAGAMENTO DA EFFETTUARE", "RIEPILOGO",
        )):
            continue

        date = _normalize_nexi_date(raw_date)
        key = (date, description, amount)
        if key in seen:
            continue
        seen.add(key)

        rows.append(Movement(
            data=date,
            valuta=date,
            dare=amount,
            causale=description,
            causale_abi=cfg["acquisto"],
            desc_causale="Acquisto carta",
        ))

    # Alcuni estratti espongono bollo e spese solo nel riepilogo finale.
    _append_nexi_summary_fee(
        rows, normalized, r"imposta\s+di\s+bollo", cfg.get("bollo", "19 NEXI"),
        "IMPOSTA DI BOLLO", "Imposta di bollo",
    )
    _append_nexi_summary_fee(
        rows, normalized, r"spese\s+(?:di\s+)?invio\s+estratto\s+conto",
        cfg.get("spese", "16 NEXI"), "SPESE INVIO ESTRATTO CONTO",
        "Spese estratto conto",
    )

    if not rows:
        raise ValueError(
            "Il PDF e stato riconosciuto come Nexi, ma non sono stati trovati movimenti. "
            "Verifica che il PDF contenga testo selezionabile e non sia una scansione."
        )
    return rows


def _normalize_nexi_date(value: str) -> str:
    value = value.replace("-", "/")
    parts = value.split("/")
    if len(parts) == 3 and len(parts[2]) == 2:
        parts[2] = "20" + parts[2]
    return "/".join(parts)


def _append_nexi_summary_fee(
    rows: list[Movement],
    text: str,
    label_pattern: str,
    abi: str,
    causale: str,
    desc: str,
) -> None:
    pattern = re.compile(
        rf"{label_pattern}.{{0,80}}?(\d{{1,3}}(?:\.\d{{3}})*,\d{{2}})",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return
    amount = match.group(1)
    if any(r.causale.upper() == causale and r.dare == amount for r in rows):
        return
    date = rows[-1].data if rows else ""
    rows.append(Movement(
        data=date,
        valuta=date,
        dare=amount,
        causale=causale,
        causale_abi=abi,
        desc_causale=desc,
    ))


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
    value = value.strip().replace("€", "").replace(" ", "").lstrip("-")
    if "," in value:
        return value
    try:
        return f"{float(value):.2f}".replace(".", ",")
    except ValueError:
        return value


def _date_yy_to_yyyy(value: str) -> str:
    day, month, year = value.split("/")
    return f"{day}/{month}/20{year}"


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
