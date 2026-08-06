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

# La vecchia sezione Calendario Gare non deve essere interrogata: e' ferma al 2024.
# La ricerca deve partire esclusivamente dai comunicati visibili nella homepage.
_BLOCKED_CALENDAR_SECTION_MARKERS = (
    "calendario.asp",
    "calendario-gare",
    "calendario_gare",
    "/calendario/",
)


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
    """Scarica l'ultimo calendario gare pubblicato nella homepage FGI Veneto.

    La funzione apre soltanto ``https://www.fgiveneto.it/home.asp`` e analizza i
    comunicati presenti nella pagina. Non usa e non segue la sezione storica
    ``Calendario Gare``, che non e' aggiornata.
    """

    own_session = session is None
    session = session or requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Consolle-SPES-Ginnastica-Mestre/6.0.1 "
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
                "Nella homepage FGI Veneto non e' stato trovato alcun calendario gare in PDF."
            )

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        _date_key_value, _priority, title, pdf_url, published_date = candidates[0]
        pdf_response = session.get(pdf_url, timeout=60)
        pdf_response.raise_for_status()
        content = pdf_response.content
        if not content.startswith(b"%PDF"):
            raise RuntimeError("Il documento calendario trovato non e' un PDF valido.")

        digest = hashlib.sha256(content).hexdigest()[:12]
        filename = _safe_filename(title) or "calendario_gare_fgi_veneto"
        local_path = calendar_dir() / f"{filename}_{digest}.pdf"
        if not local_path.exists():
            local_path.write_bytes(content)

        previous = load_latest_calendar()
        changed = (
            previous is None
            or previous.source_url != pdf_url
            or Path(previous.local_path).name != local_path.name
        )
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
    """Estrae candidati partendo esclusivamente dai contenuti della homepage.

    Sono ammessi:
    - PDF collegati direttamente da un comunicato in homepage;
    - pagine/comunicati collegati dalla homepage che contengono un PDF.

    Sono esclusi i link di navigazione verso la vecchia sezione Calendario Gare.
    """

    if _normalise_url(page_url) != _normalise_url(FGI_VENETO_HOME_URL):
        raise ValueError("La ricerca del calendario deve partire dalla homepage FGI Veneto.")

    soup = BeautifulSoup(html, "html.parser")
    results: list[tuple[str, int, str, str, str]] = []
    visited_pages: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(page_url, anchor.get("href", ""))
        text = " ".join(anchor.get_text(" ", strip=True).split())
        context = " ".join(
            (anchor.parent.get_text(" ", strip=True) if anchor.parent else text).split()
        )
        haystack = f"{text} {context} {href}".lower()

        if _is_blocked_calendar_section(href, text):
            continue
        if "calendario" not in haystack or not any(
            word in haystack for word in ("gara", "gare", "agonistico", "competizioni")
        ):
            continue

        suffix = Path(urlparse(href).path).suffix.lower()
        if suffix == ".pdf":
            published = _extract_date(context)
            results.append((_date_key(published), 4, text or context, href, published))
            continue

        # Seguiamo solo il singolo comunicato raggiunto dalla homepage, mai una
        # pagina indice/archivio del calendario.
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
            child_context = " ".join(
                (
                    child_anchor.parent.get_text(" ", strip=True)
                    if child_anchor.parent
                    else child_text
                ).split()
            )
            child_haystack = f"{child_text} {child_context} {child_href}".lower()
            if Path(urlparse(child_href).path).suffix.lower() != ".pdf":
                continue
            if "calendario" not in child_haystack and "calendario" not in page_title.lower():
                continue
            title = child_text or page_title
            results.append((_date_key(published), 3, title, child_href, published))

    return _deduplicate_candidates(results)


def _is_blocked_calendar_section(url: str, link_text: str = "") -> bool:
    # Un PDF calendario collegato direttamente dalla homepage e' valido anche
    # quando il nome file contiene "calendario_gare". Blocchiamo soltanto le
    # pagine indice/archivio della vecchia sezione.
    if Path(urlparse(url).path).suffix.lower() == ".pdf":
        return False

    lowered_url = url.lower()
    if any(marker in lowered_url for marker in _BLOCKED_CALENDAR_SECTION_MARKERS):
        return True

    normalised_text = " ".join(link_text.lower().split())
    return normalised_text in {
        "calendario",
        "calendario gare",
        "calendario gare regionale",
    }


def _deduplicate_candidates(
    candidates: list[tuple[str, int, str, str, str]],
) -> list[tuple[str, int, str, str, str]]:
    best_by_url: dict[str, tuple[str, int, str, str, str]] = {}
    for candidate in candidates:
        existing = best_by_url.get(candidate[3])
        if existing is None or (candidate[0], candidate[1]) > (existing[0], existing[1]):
            best_by_url[candidate[3]] = candidate
    return list(best_by_url.values())


def _normalise_url(value: str) -> str:
    parsed = urlparse(value)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


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
