from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from spes_tools.services.storage import data_dir

FGI_VENETO_HOME_URL = "https://www.fgiveneto.it/home.asp"


@dataclass(frozen=True)
class CalendarDocument:
    title: str
    source_url: str
    local_path: str
    published_date: str
    updated_at: str
    changed: bool


def calendar_dir() -> Path:
    path = data_dir() / "fgi_calendario"
    path.mkdir(parents=True, exist_ok=True)
    return path


def metadata_path() -> Path:
    return calendar_dir() / "ultimo_calendario.json"


def load_latest_calendar() -> CalendarDocument | None:
    path = metadata_path()
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return CalendarDocument(**raw)
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def update_fgi_calendar(session: requests.Session | None = None) -> CalendarDocument:
    """Trova dalla homepage FGI Veneto l'ultimo calendario gare e salva il PDF.

    La sezione storica "Calendario Gare" non viene interrogata: la ricerca parte
    esclusivamente dalla homepage e segue gli eventuali comunicati collegati.
    """

    own_session = session is None
    session = session or requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "SPES-Configuratore-Contabile/5.3.5 "
                "(+https://www.spesginnasticamestre.it)"
            )
        }
    )
    try:
        response = session.get(FGI_VENETO_HOME_URL, timeout=45)
        response.raise_for_status()
        candidates = _calendar_candidates(FGI_VENETO_HOME_URL, response.text, session)
        if not candidates:
            raise RuntimeError(
                "Nella homepage FGI Veneto non è stato trovato alcun calendario gare in PDF."
            )

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        _date_key, _priority, title, pdf_url, published_date = candidates[0]
        pdf_response = session.get(pdf_url, timeout=60)
        pdf_response.raise_for_status()
        content = pdf_response.content
        if not content.startswith(b"%PDF"):
            raise RuntimeError("Il documento calendario trovato non è un PDF valido.")

        digest = hashlib.sha256(content).hexdigest()[:12]
        filename = _safe_filename(title) or "calendario_gare_fgi_veneto"
        local_path = calendar_dir() / f"{filename}_{digest}.pdf"
        if not local_path.exists():
            local_path.write_bytes(content)

        previous = load_latest_calendar()
        changed = previous is None or previous.source_url != pdf_url or Path(previous.local_path).name != local_path.name
        document = CalendarDocument(
            title=title,
            source_url=pdf_url,
            local_path=str(local_path),
            published_date=published_date,
            updated_at=datetime.now().isoformat(timespec="seconds"),
            changed=changed,
        )
        metadata_path().write_text(
            json.dumps(asdict(document), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return document
    finally:
        if own_session:
            session.close()


def _calendar_candidates(
    page_url: str,
    html: str,
    session: requests.Session,
) -> list[tuple[str, int, str, str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[tuple[str, int, str, str, str]] = []
    visited_pages: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(page_url, anchor.get("href", ""))
        text = " ".join(anchor.get_text(" ", strip=True).split())
        context = " ".join((anchor.parent.get_text(" ", strip=True) if anchor.parent else text).split())
        haystack = f"{text} {context} {href}".lower()
        if "calendario" not in haystack or not any(word in haystack for word in ("gara", "gare", "agonistico")):
            continue

        suffix = Path(urlparse(href).path).suffix.lower()
        if suffix == ".pdf":
            published = _extract_date(context)
            results.append((_date_key(published), 2, text or context, href, published))
            continue

        if href in visited_pages:
            continue
        visited_pages.add(href)
        try:
            child = session.get(href, timeout=45)
            child.raise_for_status()
        except requests.RequestException:
            continue
        child_soup = BeautifulSoup(child.text, "html.parser")
        page_title = text or context or "Calendario gare FGI Veneto"
        published = _extract_date(child_soup.get_text(" ", strip=True)) or _extract_date(context)
        for child_anchor in child_soup.find_all("a", href=True):
            child_href = urljoin(href, child_anchor.get("href", ""))
            child_text = " ".join(child_anchor.get_text(" ", strip=True).split())
            child_haystack = f"{child_text} {child_href}".lower()
            if Path(urlparse(child_href).path).suffix.lower() != ".pdf":
                continue
            if "calendario" not in child_haystack:
                continue
            title = child_text or page_title
            results.append((_date_key(published), 3, title, child_href, published))

    return results


def _extract_date(value: str) -> str:
    match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", value)
    if not match:
        return ""
    day, month, year = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day).strftime("%d/%m/%Y")
    except ValueError:
        return ""


def _date_key(value: str) -> str:
    try:
        return datetime.strptime(value, "%d/%m/%Y").strftime("%Y%m%d")
    except ValueError:
        return "00000000"


def _safe_filename(value: str) -> str:
    value = value.lower().replace("à", "a").replace("è", "e").replace("é", "e")
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value[:100]
