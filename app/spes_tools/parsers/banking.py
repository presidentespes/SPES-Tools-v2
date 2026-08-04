import csv
import hashlib
import io
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List

import pdfplumber


@dataclass
class Movimento:
    data: str
    valuta: str
    dare: str
    avere: str
    causale: str
    causale_abi: str
    desc_causale: str
    soggetto: str
    iban: str
    spuntato: str

    def to_dict(self):
        return asdict(self)


EXPORT_COLUMNS = [
    "DATA", "VALUTA", "DARE", "AVERE", "CAUSALE", "CAUSALE ABI",
    "desc.causale", "SOGGETTO", "IBAN", "SPUNTATO",
]


def _resource_path(filename: str) -> Path:
    import sys
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidate = base / filename
    if candidate.exists():
        return candidate
    return Path(__file__).resolve().parents[1] / filename


def _app_data_dir() -> Path:
    import os
    base = Path(os.environ.get("APPDATA", Path.home())) / "SpesConverter"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _user_config_path() -> Path:
    return _app_data_dir() / "config_abi.json"


def history_path() -> Path:
    return _app_data_dir() / "history.json"


def load_config(path=None):
    target = Path(path) if path else _user_config_path()
    defaults = json.loads(_resource_path("config_abi.json").read_text(encoding="utf-8"))
    if not target.exists():
        target.write_text(json.dumps(defaults, ensure_ascii=False, indent=2), encoding="utf-8")
        return defaults

    try:
        current = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        current = {}

    # Migrazione automatica alla configurazione con profili ABI distinti per banca.
    if current.get("_version", 0) < defaults.get("_version", 0):
        for bank in ("NEXI", "BCC", "VOLKSBANK"):
            current.setdefault(bank, {})
            for key, item in defaults[bank].items():
                current[bank].setdefault(key, {})
                current[bank][key]["code"] = item["code"]
                current[bank][key].setdefault("desc", item["desc"])
        current["_version"] = defaults["_version"]
        target.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def save_config(cfg, path=None):
    target = Path(path) if path else _user_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def load_history(limit=30):
    p = history_path()
    if not p.exists():
        return []
    try:
        values = json.loads(p.read_text(encoding="utf-8"))
        return values[:limit] if isinstance(values, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def append_history(filename, filetype, rows, total_dare, total_avere):
    history = load_history(limit=200)
    history.insert(0, {
        "elaborato_il": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "file": filename,
        "tipo": filetype,
        "movimenti": len(rows),
        "totale_dare": total_dare,
        "totale_avere": total_avere,
    })
    history_path().write_text(json.dumps(history[:100], ensure_ascii=False, indent=2), encoding="utf-8")


def clear_history():
    history_path().write_text("[]", encoding="utf-8")


def _dec(v):
    s = str(v or "").strip().replace("€", "").replace(" ", "")
    if not s:
        return Decimal("0")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"Importo non valido: {v}") from exc


def money(v):
    amount = v if isinstance(v, Decimal) else _dec(v)
    return f"{abs(amount):.2f}".replace(".", ",")


def date4(v):
    v = str(v or "").strip()
    for f in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, f).strftime("%d/%m/%Y")
        except ValueError:
            pass
    return v


def extract_text(b):
    with pdfplumber.open(io.BytesIO(b)) as pdf:
        return "\n".join((p.extract_text(x_tolerance=2, y_tolerance=3) or "") for p in pdf.pages)


def _decode_text(b):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8-sig", errors="replace")


def detect(name, b):
    ext = Path(name).suffix.lower()
    if ext in (".xls", ".csv", ".txt"):
        head = _decode_text(b[:15000]).upper()
        if all(x in head for x in ("DATA ESECUZIONE", "IMPORTO", "BENEFICIARIO", "CONTO CORRENTE DI ADDEBITO")):
            return "VOLKSBANK_BONSEPA"
        if "DATA CONTABILE" in head and ("DARE" in head or "AVERE" in head):
            return "VOLKSBANK"
    if ext == ".pdf":
        t = extract_text(b)
        n = re.sub(r"\s+", "", t.upper())
        if "DETTAGLIODEISUOIMOVIMENTI" in n and "NEXI" in n:
            return "NEXI"
        if "RELAXBANKING" in n or ("DATA CONTABILE" in t.upper() and "DATA VALUTA" in t.upper()):
            return "BCC"
    return "SCONOSCIUTO"


def _nexi_desc(raw):
    x = re.sub(r"(?<=[a-zà-ÿ])(?=[A-Z])", " ", raw)
    x = re.sub(r"\s+", " ", x).strip().upper()
    for a, b in {"SPOTIFYIT STOCKHOLM": "SPOTIFY", "AMAZON PRIME AMAZON.IT/PRM": "AMAZON PRIME"}.items():
        x = x.replace(a, b)
    return x


def parse_nexi(b, cfg, iban="", spuntato="0"):
    t = extract_text(b)
    compact = re.sub(r"\s+", "", t)
    m = re.search(r"DETTAGLIODEISUOIMOVIMENTI.*?Cambio(.*?)TOTALESPESE", compact, re.S)
    if not m:
        raise ValueError("Dettaglio movimenti Nexi non trovato.")
    pat = re.compile(r"(\d{2}/\d{2}/\d{2})(.+?)(\d{1,3}(?:\.\d{3})*,\d{2})(?=\d{2}/\d{2}/\d{2}|$)")
    rows = []
    for d, desc, amt in pat.findall(m.group(1)):
        c = cfg["NEXI"]["acquisto"]
        rows.append(Movimento(date4(d), date4(d), money(amt), "", _nexi_desc(desc), c["code"], c["desc"], "", iban, spuntato))
    sm = re.search(r"Debitoresiduoal(\d{2}/\d{2}/\d{4})", compact)
    sd = sm.group(1) if sm else (rows[-1].data if rows else "")
    extras = [
        ("bollo", "IMPOSTA DI BOLLO", r"Impostadibollo(\d{1,3}(?:\.\d{3})*,\d{2})"),
        ("spese", "SPESE INVIO ESTRATTO CONTO", r"Speseinvioestrattoconto(\d{1,3}(?:\.\d{3})*,\d{2})"),
    ]
    for key, label, rx in extras:
        q = re.search(rx, compact)
        if q:
            c = cfg["NEXI"][key]
            rows.append(Movimento(sd, sd, money(q.group(1)), "", label, c["code"], c["desc"], "", iban, spuntato))
    return rows, []


def bcc_cat(desc):
    u = desc.upper()
    if "INCASSI PAGOBANCOMAT" in u or "INCASSI INTERNAZIONALI" in u:
        return "incassi_pos"
    if "BONIFICO A VS FAVORE" in u:
        return "bonifico_entrata"
    if "BONIFICO TRAMITE INTERNET BANKING" in u:
        return "bonifico_uscita"
    if "SDD" in u or "RICHIESTA INCASSO SEPA" in u:
        return "sdd"
    if "COMMISSION" in u:
        return "commissioni"
    if "BOLLO" in u:
        return "bollo"
    if "CANONE" in u:
        return "canone"
    return "altro"


def parse_bcc(b, cfg, iban="", spuntato="0"):
    all_rows, full_text = [], []
    with pdfplumber.open(io.BytesIO(b)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=2, y_tolerance=2)
            full_text.append(page.extract_text() or "")
            lines = {}
            for w in words:
                lines.setdefault(round(float(w["top"]), 1), []).append(w)
            line_list = [(top, sorted(ws, key=lambda x: x["x0"])) for top, ws in sorted(lines.items())]
            dates = []
            for top, ws in line_list:
                left = " ".join(w["text"] for w in ws if w["x0"] < 230)
                m = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})", left)
                amount = " ".join(w["text"] for w in ws if 245 <= w["x0"] < 303)
                am = re.search(r"-?\d+(?:\.\d{3})*,\d{2}", amount)
                if m and am:
                    dates.append((top, m.group(1), m.group(2), am.group(0)))
            for i, (top, d, v, a) in enumerate(dates):
                prev_top = dates[i - 1][0] if i else top - 16
                next_top = dates[i + 1][0] if i + 1 < len(dates) else top + 18
                low, high = (prev_top + top) / 2, (top + next_top) / 2
                desc = []
                for lt, ws in line_list:
                    if low <= lt < high:
                        txt = " ".join(w["text"] for w in ws if w["x0"] >= 300)
                        if txt and txt.upper() not in ("DESCRIZIONE", "SALDO FINALE AL -", "SALDO INIZIALE AL -"):
                            desc.append(txt)
                all_rows.append((d, v, a, re.sub(r"\s+", " ", " ".join(desc)).strip()))
    text = "\n".join(full_text)
    miban = re.search(r"IT\d{2}[A-Z]\d{22}", re.sub(r"\s+", "", text))
    iban = iban or (miban.group(0) if miban else "")
    rows = []
    for d, v, a, desc in all_rows:
        val = _dec(a)
        c = cfg["BCC"][bcc_cat(desc)]
        rows.append(Movimento(d, v, money(val) if val < 0 else "", money(val) if val > 0 else "", desc, c["code"], c["desc"], "", iban, spuntato))
    return rows, []


def volks_cat(causale, desc):
    u = (causale + " " + desc).upper()
    if "COMMISSION" in u:
        return "commissioni"
    if "BONIFICO" in u and ("A VS FAVORE" in u or "ACCREDITO" in u):
        return "bonifico_entrata"
    if "BONIFICO" in u:
        return "bonifico_uscita"
    if "SDD" in u or "SEPA" in u:
        return "sdd"
    if "PAGOBANCOMAT" in u or "POS" in u or "INCASSI" in u:
        return "pos"
    return "altro"


def parse_volksbank(b, cfg, iban="", spuntato="0"):
    text = _decode_text(b)
    delim = "\t" if "\t" in text[:2000] else ";"
    rows0 = list(csv.reader(io.StringIO(text), delimiter=delim))
    if not rows0:
        raise ValueError("File vuoto.")
    header = [x.strip() for x in rows0[0]]
    idx = {h.lower(): i for i, h in enumerate(header) if h}
    out = []
    for r in rows0[1:]:
        if not any(x.strip() for x in r):
            continue
        def g(k):
            i = idx.get(k.lower())
            return r[i].strip() if i is not None and i < len(r) else ""
        d, v, dare, avere = g("Data contabile"), g("Data valuta"), g("Dare"), g("Avere")
        caus = g("Causale")
        desc = " ".join(x for x in [g("Descrizione"), g("Note")] if x).strip()
        if not d:
            continue
        c = cfg["VOLKSBANK"][volks_cat(caus, desc)]
        out.append(Movimento(date4(d), date4(v or d), money(dare) if dare else "", money(avere) if avere else "", " ".join([caus, desc]).strip(), c["code"], c["desc"], "", iban, spuntato))
    return out, []


def _bonsepa_date(value):
    value = (value or "").strip().split("T", 1)[0]
    return date4(value)


def parse_volksbank_bonsepa(b, cfg, iban="", spuntato="0"):
    text = _decode_text(b)
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames:
        raise ValueError("Intestazione bonifici SEPA Volksbank non trovata.")
    fields = {(h or "").strip().lower(): h for h in reader.fieldnames}
    required = ("data esecuzione", "importo", "causale", "beneficiario", "conto corrente di addebito")
    missing = [x for x in required if x not in fields]
    if missing:
        raise ValueError("Colonne mancanti nel file bonifici SEPA Volksbank: " + ", ".join(missing))
    c = cfg["VOLKSBANK"]["bonifico_uscita"]
    out, warnings = [], []
    for line_no, row in enumerate(reader, start=2):
        def g(name):
            return (row.get(fields.get(name.lower(), "")) or "").strip()
        if not any((v or "").strip() for v in row.values()):
            continue
        d = _bonsepa_date(g("data esecuzione"))
        if not d:
            warnings.append(f"Riga {line_no}: data esecuzione mancante, riga ignorata.")
            continue
        amount = _dec(g("importo").upper().replace("EUR", ""))
        status = g("stato")
        beneficiario = g("beneficiario")
        causale = g("causale")
        source_iban = g("conto corrente di addebito").replace(" ", "")
        row_iban = (iban or source_iban).strip()
        if status and status.upper() not in ("PAGATO", "ESEGUITO"):
            warnings.append(f"Riga {line_no}: stato \"{status}\"; verificare prima dell'importazione.")
        out.append(Movimento(
            d, d, money(amount), "", "Bonifico SEPA", c["code"],
            causale, beneficiario, row_iban, spuntato,
        ))
    if not out:
        raise ValueError("Nessun bonifico SEPA Volksbank valido trovato.")
    return out, warnings


def parse_auto(name, b, cfg, iban="", spuntato="0"):
    typ = detect(name, b)
    if typ == "NEXI":
        rows, warnings = parse_nexi(b, cfg, iban, spuntato)
    elif typ == "BCC":
        rows, warnings = parse_bcc(b, cfg, iban, spuntato)
    elif typ == "VOLKSBANK":
        rows, warnings = parse_volksbank(b, cfg, iban, spuntato)
    elif typ == "VOLKSBANK_BONSEPA":
        rows, warnings = parse_volksbank_bonsepa(b, cfg, iban, spuntato)
    else:
        raise ValueError("Formato non riconosciuto. Caricare PDF Nexi/BCC, export movimenti Volksbank oppure bonifici SEPA Volksbank CSV.")
    return typ, rows, warnings


def validate_rows(rows: List[Movimento]):
    issues = []
    seen = {}
    for i, r in enumerate(rows, start=1):
        if not r.data:
            issues.append(("Errore", i, "DATA mancante"))
        elif date4(r.data) != r.data:
            issues.append(("Avviso", i, f"DATA non standard: {r.data}"))
        if not r.dare and not r.avere:
            issues.append(("Errore", i, "Importo DARE/AVERE mancante"))
        if r.dare and r.avere:
            issues.append(("Errore", i, "DARE e AVERE entrambi valorizzati"))
        if not str(r.causale_abi).strip():
            issues.append(("Errore", i, "CAUSALE ABI mancante"))
        if r.causale == "Bonifico SEPA" and not r.soggetto.strip():
            issues.append(("Errore", i, "SOGGETTO/beneficiario mancante"))
        key = hashlib.sha1("|".join([r.data, r.valuta, r.dare, r.avere, r.causale, r.desc_causale, r.soggetto, r.iban]).encode("utf-8")).hexdigest()
        if key in seen:
            issues.append(("Avviso", i, f"Possibile duplicato della riga {seen[key]}"))
        else:
            seen[key] = i
    return issues


def to_csv(rows):
    s = io.StringIO(newline="")
    w = csv.writer(s, delimiter=";", lineterminator="\r\n")
    w.writerow(EXPORT_COLUMNS)
    for r in rows:
        w.writerow([r.data, r.valuta, r.dare, r.avere, r.causale, r.causale_abi, r.desc_causale, r.soggetto, r.iban, r.spuntato])
    return ("\ufeff" + s.getvalue()).encode("utf-8")
