from __future__ import annotations

from dataclasses import dataclass

import pytest

from spes_tools.services.fgi_calendar import (
    FGI_VENETO_HOME_URL,
    _calendar_candidates,
)


@dataclass
class FakeResponse:
    text: str = ""
    content: bytes = b""

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self, pages: dict[str, FakeResponse]):
        self.pages = pages
        self.requested: list[str] = []

    def get(self, url: str, timeout: int):
        self.requested.append(url)
        return self.pages[url]


def test_calendar_search_ignores_old_calendar_section_and_uses_home_news():
    news_url = "https://www.fgiveneto.it/comunicato-calendario-2026.asp"
    pdf_url = "https://www.fgiveneto.it/allegati/calendario_gare_2026.pdf"
    old_section_url = "https://www.fgiveneto.it/calendario.asp"

    home_html = f"""
    <html><body>
      <nav><a href="{old_section_url}">Calendario Gare</a></nav>
      <article>
        <span>05/08/2026</span>
        <a href="{news_url}">Aggiornamento calendario gare 2026</a>
      </article>
    </body></html>
    """
    news_html = f"""
    <html><body>
      <h1>Aggiornamento calendario gare 2026</h1>
      <a href="{pdf_url}">Scarica calendario gare aggiornato</a>
    </body></html>
    """
    session = FakeSession({news_url: FakeResponse(text=news_html)})

    candidates = _calendar_candidates(FGI_VENETO_HOME_URL, home_html, session)

    assert [item[3] for item in candidates] == [pdf_url]
    assert old_section_url not in session.requested
    assert session.requested == [news_url]


def test_calendar_search_rejects_non_homepage_start_url():
    with pytest.raises(ValueError, match="homepage FGI Veneto"):
        _calendar_candidates(
            "https://www.fgiveneto.it/calendario.asp",
            "<html></html>",
            FakeSession({}),
        )


def test_calendar_search_accepts_direct_pdf_from_homepage():
    pdf_url = "https://www.fgiveneto.it/allegati/calendario_gare_2026.pdf"
    home_html = f"""
    <html><body>
      <article>
        <span>03/08/2026</span>
        <a href="{pdf_url}">Calendario gare aggiornato</a>
      </article>
    </body></html>
    """

    candidates = _calendar_candidates(FGI_VENETO_HOME_URL, home_html, FakeSession({}))

    assert len(candidates) == 1
    assert candidates[0][3] == pdf_url
    assert candidates[0][4] == "03/08/2026"
