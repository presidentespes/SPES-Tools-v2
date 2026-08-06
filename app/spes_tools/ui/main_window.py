from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import webbrowser

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from spes_tools.resources import resource_path
from spes_tools.services.auth import SessionUser, UserStore
from spes_tools.services.fgi_calendar import load_latest_calendar, update_fgi_calendar
from spes_tools.services.storage import archive_root
from spes_tools.ui.abi_window import AbiWindow
from spes_tools.ui.activity_log_window import ActivityLogWindow
from spes_tools.ui.banking_window import BankingWindow
from spes_tools.ui.caf_window import CafWindow
from spes_tools.ui.cash_window import CashWindow
from spes_tools.ui.fgi_results_window import FgiResultsWindow
from spes_tools.ui.history_window import HistoryWindow
from spes_tools.ui.settings_window import SettingsWindow
from spes_tools.version import APP_NAME, APP_VERSION, ORGANIZATION_NAME


APP_STYLE = """
QMainWindow, QWidget#root { background: #f4f7fb; color: #10213d; }
QWidget#sidebar { background: #ffffff; border-right: 1px solid #dce4ef; }
QWidget#header { background: #ffffff; border-bottom: 1px solid #dce4ef; }
QLabel#appTitle { color: #10213d; font-size: 28px; font-weight: 800; }
QLabel#version { color: #1454b8; font-size: 13px; font-weight: 700; }
QLabel#pageTitle { color: #10213d; font-size: 25px; font-weight: 800; }
QLabel#pageSubtitle { color: #53657a; font-size: 14px; }
QPushButton#navButton {
    background: transparent; color: #213653; border: none; border-radius: 9px;
    padding: 10px 12px; text-align: left; font-size: 13px; font-weight: 650;
}
QPushButton#navButton:hover { background: #edf4ff; color: #0a4eae; }
QPushButton#navButton:checked { background: #0f4fb7; color: white; }
QFrame#card {
    background: white; border: 1px solid #dce4ef; border-radius: 14px;
}
QPushButton#actionButton {
    background: #f8fbff; color: #133b74; border: 1px solid #d7e2f0; border-radius: 9px;
    padding: 9px 12px; text-align: left; font-size: 12px; font-weight: 700;
}
QPushButton#actionButton:hover { background: #eaf3ff; border-color: #6fa7ef; }
QPushButton#primaryButton {
    background: #0f4fb7; color: white; border: none; border-radius: 9px;
    padding: 9px 14px; font-size: 12px; font-weight: 750;
}
QPushButton#primaryButton:hover { background: #0b429a; }
QLineEdit {
    background: #f8fafc; border: 1px solid #d7e0ec; border-radius: 10px;
    padding: 9px 12px; color: #213653; font-size: 12px;
}
QStatusBar { background: white; color: #53657a; border-top: 1px solid #dce4ef; }
"""


class MainWindow(QMainWindow):
    """Dashboard principale della Consolle SPES con navigazione laterale."""

    def __init__(self, current_user: SessionUser) -> None:
        super().__init__()
        self.current_user = current_user
        self.user_store = UserStore()

        self.banking_window: BankingWindow | None = None
        self.caf_window: CafWindow | None = None
        self.cash_window: CashWindow | None = None
        self.abi_window: AbiWindow | None = None
        self.history_window: HistoryWindow | None = None
        self.settings_window: SettingsWindow | None = None
        self.fgi_results_window: FgiResultsWindow | None = None
        self.activity_log_window: ActivityLogWindow | None = None

        self.pages: dict[str, QWidget] = {}
        self.nav_buttons: dict[str, QPushButton] = {}

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(1180, 760)
        self.resize(1536, 930)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        shell.addWidget(self._build_sidebar())

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self._build_header())

        self.stack = QStackedWidget()
        self.stack.setContentsMargins(0, 0, 0, 0)
        self._add_page("dashboard", self._build_dashboard_page())
        self._add_page("admin", self._build_admin_page())
        self._add_page("fgi", self._build_fgi_page())
        self._add_page("web", self._build_web_page())
        self._add_page("documents", self._build_documents_page())
        self._add_page("system", self._build_system_page())
        body_layout.addWidget(self.stack, 1)
        shell.addWidget(body, 1)

        status = QStatusBar()
        status.showMessage(
            f"Pronto • {self.current_user.display_name} ({self.current_user.role}) • {APP_NAME} {APP_VERSION}"
        )
        self.setStatusBar(status)
        self._select_page("dashboard")

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(245)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(8)

        logo = QLabel()
        pixmap = QPixmap(str(resource_path("assets/logo_spes.png")))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(165, 125, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)
        layout.addSpacing(12)

        self._add_nav(layout, "dashboard", "🏠  Dashboard")
        if self._can("users_manage") or self._can("activity_logs"):
            self._add_nav(layout, "admin", "👥  Utenti e permessi")
        if any(self._can(p) for p in ("banking", "compensation", "cash", "csv_archive")):
            self._add_nav(layout, "admin", "€   Area amministrativa", alias="amministrazione")
        if any(self._can(p) for p in ("fgi_results", "fgi_calendar", "fgi_regulation")):
            self._add_nav(layout, "fgi", "🏆  Area FGI")
        self._add_nav(layout, "web", "🌐  Servizi web")
        self._add_nav(layout, "documents", "📁  Documenti")
        if self._can("settings") or self._can("activity_logs"):
            self._add_nav(layout, "system", "⚙️  Sistema")

        layout.addStretch()
        quick = self._card()
        quick_layout = QVBoxLayout(quick)
        quick_layout.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Collegamenti rapidi")
        title.setStyleSheet("font-weight: 800; color: #164d9b;")
        quick_layout.addWidget(title)
        for permission, label, url in self._quick_links():
            if self._can(permission):
                quick_layout.addWidget(self._small_link(label, url))
        layout.addWidget(quick)
        return sidebar

    def _add_nav(
        self, layout: QVBoxLayout, page_key: str, text: str, *, alias: str | None = None
    ) -> None:
        key = alias or page_key
        button = QPushButton(text)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda _checked=False, page=page_key: self._select_page(page))
        self.nav_buttons[key] = button
        layout.addWidget(button)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(105)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(28, 18, 28, 18)
        layout.setSpacing(20)

        names = QVBoxLayout()
        title = QLabel("Consolle SPES Ginnastica Mestre")
        title.setObjectName("appTitle")
        names.addWidget(title)
        version = QLabel(f"Versione {APP_VERSION}")
        version.setObjectName("version")
        names.addWidget(version)
        layout.addLayout(names)
        layout.addStretch()

        search = QLineEdit()
        search.setPlaceholderText("Cerca nella Consolle...")
        search.setFixedWidth(255)
        search.returnPressed.connect(lambda: self._handle_search(search.text()))
        layout.addWidget(search)

        date_label = QLabel(datetime.now().strftime("%d/%m/%Y  %H:%M"))
        date_label.setStyleSheet("color: #40546d; font-weight: 650;")
        layout.addWidget(date_label)

        user = QLabel(f"👤  {self.current_user.display_name}\n{self.current_user.role.title()}")
        user.setStyleSheet("color: #10213d; font-weight: 750;")
        layout.addWidget(user)
        return header

    def _add_page(self, key: str, page: QWidget) -> None:
        self.pages[key] = page
        self.stack.addWidget(page)

    def _select_page(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        for button in self.nav_buttons.values():
            button.setChecked(False)
        for nav_key, button in self.nav_buttons.items():
            if nav_key == key or (key == "admin" and nav_key == "amministrazione"):
                button.setChecked(True)
                break

    def _page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        layout.addWidget(heading)
        detail = QLabel(subtitle)
        detail.setObjectName("pageSubtitle")
        layout.addWidget(detail)
        return page, layout

    def _build_dashboard_page(self) -> QWidget:
        page, layout = self._page(
            f"Buonasera, {self.current_user.display_name}",
            "Ecco cosa sta succedendo oggi in SPES.",
        )

        summary = QGridLayout()
        summary.setHorizontalSpacing(16)
        summary.setVerticalSpacing(16)
        cards = [
            ("📅", "Calendario gare", "Archivio locale", "Apri calendario", self.open_fgi_calendar, "fgi_calendar"),
            ("🏆", "Risultati FGI", "Ricerca locale", "Vedi risultati", self.open_fgi_results, "fgi_results"),
            ("📘", "Regolamento FGI", "TUNS 2027", "Apri PDF", self.open_fgi_regulation, "fgi_regulation"),
            ("📂", "Archivio CSV", "Cartelle per banca", "Apri archivio", self.open_csv_archive, "csv_archive"),
        ]
        col = 0
        for icon, title, value, link, callback, permission in cards:
            if not self._can(permission):
                continue
            summary.addWidget(self._metric_card(icon, title, value, link, callback), 0, col)
            col += 1
        layout.addLayout(summary)

        middle = QGridLayout()
        middle.setHorizontalSpacing(16)
        middle.setVerticalSpacing(16)
        middle.addWidget(self._events_card(), 0, 0)
        middle.addWidget(self._admin_activity_card(), 0, 1)
        middle.addWidget(self._system_status_card(), 0, 2)
        middle.setColumnStretch(0, 1)
        middle.setColumnStretch(1, 1)
        middle.setColumnStretch(2, 1)
        layout.addLayout(middle)
        layout.addWidget(self._services_strip())
        layout.addStretch()
        return self._scroll_page(page)

    def _metric_card(
        self, icon: str, title: str, value: str, link: str, callback: Callable[[], None]
    ) -> QWidget:
        card = self._card()
        card.setMinimumHeight(150)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 14)
        top = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 30px;")
        top.addWidget(icon_label)
        names = QVBoxLayout()
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 14px; font-weight: 800; color: #10213d;")
        names.addWidget(heading)
        metric = QLabel(value)
        metric.setStyleSheet("font-size: 20px; font-weight: 850; color: #1754b3;")
        names.addWidget(metric)
        top.addLayout(names)
        top.addStretch()
        layout.addLayout(top)
        layout.addStretch()
        action = QPushButton(f"{link}  ›")
        action.setObjectName("actionButton")
        action.clicked.connect(callback)
        layout.addWidget(action)
        return card

    def _events_card(self) -> QWidget:
        card = self._titled_card("Prossimi eventi")
        layout = card.layout()
        assert isinstance(layout, QVBoxLayout)
        for date, title, detail in (
            ("DOM", "Aggiornamento calendario FGI", "Domenica alle 01:00"),
            ("LUN", "Aggiornamento risultati FGI", "Lunedì alle 01:00"),
            ("OGGI", "Consolle operativa", f"Profilo: {self.current_user.role}"),
        ):
            layout.addWidget(self._info_row(date, title, detail))
        layout.addStretch()
        return card

    def _admin_activity_card(self) -> QWidget:
        card = self._titled_card("Attività amministrative")
        layout = card.layout()
        assert isinstance(layout, QVBoxLayout)
        rows: list[tuple[str, str, Callable[[], None], str]] = [
            ("🏦", "Riconciliazione bancaria", self.open_banking, "banking"),
            ("💶", "Convertitore compensi", self.open_caf, "compensation"),
            ("💰", "Gestione Cassa", self.open_cash, "cash"),
            ("📂", "Archivio CSV", self.open_csv_archive, "csv_archive"),
        ]
        found = False
        for icon, title, callback, permission in rows:
            if self._can(permission):
                layout.addWidget(self._action_row(icon, title, callback))
                found = True
        if not found:
            layout.addWidget(QLabel("Nessun modulo amministrativo autorizzato."))
        layout.addStretch()
        return card

    def _system_status_card(self) -> QWidget:
        card = self._titled_card("Stato sistema")
        layout = card.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.addWidget(self._status_row("🗄️", "Database", "Operativo", "OK"))
        layout.addWidget(self._status_row("🏆", "Archivio FGI", "Ricerca locale attiva", "OK"))
        layout.addWidget(self._status_row("🔐", "Profilo", self.current_user.role.title(), "OK"))
        layout.addWidget(self._status_row("📦", "Versione", APP_VERSION, "OK"))
        layout.addStretch()
        return card

    def _services_strip(self) -> QWidget:
        card = self._titled_card("Servizi web")
        layout = card.layout()
        assert isinstance(layout, QVBoxLayout)
        row = QHBoxLayout()
        row.setSpacing(10)
        for permission, label, url in self._all_web_links():
            if not self._can(permission):
                continue
            button = QPushButton(label)
            button.setObjectName("actionButton")
            button.setMinimumHeight(70)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda _checked=False, address=url: self.open_web_link(address))
            row.addWidget(button)
        layout.addLayout(row)
        return card

    def _build_admin_page(self) -> QWidget:
        page, layout = self._page("Area amministrativa", "Moduli e strumenti autorizzati per il tuo profilo.")
        grid = QGridLayout()
        grid.setSpacing(16)
        items = [
            ("🏦 Riconciliazione bancaria", "Importa e riconcilia i movimenti bancari.", self.open_banking, "banking"),
            ("💶 Convertitore compensi", "Calcolo e preparazione dei compensi.", self.open_caf, "compensation"),
            ("💰 Gestione Cassa", "Registro entrate, uscite ed esportazioni.", self.open_cash, "cash"),
            ("📂 Archivio CSV", "Apre l'archivio organizzato per banca e anno.", self.open_csv_archive, "csv_archive"),
            ("🧾 Registro attività", "Consulta accessi e operazioni registrate.", self.open_activity_logs, "activity_logs"),
            ("⚙️ Impostazioni", "Backup, aggiornamenti e gestione applicazione.", self.open_settings, "settings"),
        ]
        index = 0
        for title, description, callback, permission in items:
            if not self._can(permission):
                continue
            grid.addWidget(self._feature_card(title, description, callback), index // 3, index % 3)
            index += 1
        layout.addLayout(grid)
        layout.addStretch()
        return self._scroll_page(page)

    def _build_fgi_page(self) -> QWidget:
        page, layout = self._page("Area FGI", "Calendari, risultati SPES e regolamenti disponibili localmente.")
        search = QLineEdit()
        search.setPlaceholderText("Cerca un atleta nei risultati FGI...")
        search.returnPressed.connect(self.open_fgi_results)
        layout.addWidget(search)
        grid = QGridLayout()
        grid.setSpacing(16)
        items = [
            ("🏆 Risultati FGI", "Archivio locale della società 000112, filtrabile per atleta.", self.open_fgi_results, "fgi_results"),
            ("📅 Calendario gare", "Aggiornato dalla homepage FGI Veneto.", self.open_fgi_calendar, "fgi_calendar"),
            ("📘 Regolamento FGI", "Apre il PDF TUNS 2027 incluso nell'app.", self.open_fgi_regulation, "fgi_regulation"),
        ]
        index = 0
        for title, description, callback, permission in items:
            if self._can(permission):
                grid.addWidget(self._feature_card(title, description, callback), 0, index)
                index += 1
        layout.addLayout(grid)
        layout.addStretch()
        return self._scroll_page(page)

    def _build_web_page(self) -> QWidget:
        page, layout = self._page("Servizi web", "Accessi rapidi ai portali utilizzati da SPES.")
        grid = QGridLayout()
        grid.setSpacing(14)
        index = 0
        for permission, label, url in self._all_web_links():
            if not self._can(permission):
                continue
            grid.addWidget(
                self._feature_card(label, "Apre il servizio nel browser predefinito.", lambda address=url: self.open_web_link(address)),
                index // 3,
                index % 3,
            )
            index += 1
        layout.addLayout(grid)
        layout.addStretch()
        return self._scroll_page(page)

    def _build_documents_page(self) -> QWidget:
        page, layout = self._page("Documenti", "Archivio locale di regolamenti, calendari e file CSV.")
        grid = QGridLayout()
        grid.setSpacing(16)
        items = [
            ("📘 Regolamento FGI", "Documento TUNS 2027 integrato.", self.open_fgi_regulation, "fgi_regulation"),
            ("📅 Calendario FGI Veneto", "Ultimo calendario disponibile.", self.open_fgi_calendar, "fgi_calendar"),
            ("📂 Archivio CSV", "Documenti contabili organizzati.", self.open_csv_archive, "csv_archive"),
        ]
        index = 0
        for title, description, callback, permission in items:
            if self._can(permission):
                grid.addWidget(self._feature_card(title, description, callback), 0, index)
                index += 1
        layout.addLayout(grid)
        layout.addStretch()
        return self._scroll_page(page)

    def _build_system_page(self) -> QWidget:
        page, layout = self._page("Sistema", "Impostazioni, registro attività e informazioni della Consolle.")
        grid = QGridLayout()
        grid.setSpacing(16)
        items = [
            ("⚙️ Impostazioni", "Backup, aggiornamenti e manutenzione.", self.open_settings, "settings"),
            ("🧾 Registro attività", "Storico degli accessi e delle operazioni.", self.open_activity_logs, "activity_logs"),
            ("ℹ️ Informazioni", "Versione, autore e moduli disponibili.", self.open_info, None),
        ]
        index = 0
        for title, description, callback, permission in items:
            if permission is None or self._can(permission):
                grid.addWidget(self._feature_card(title, description, callback), 0, index)
                index += 1
        layout.addLayout(grid)
        layout.addStretch()
        return self._scroll_page(page)

    @staticmethod
    def _scroll_page(content: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        return card

    def _titled_card(self, title: str) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 15px; font-weight: 850; color: #164d9b;")
        layout.addWidget(heading)
        return card

    def _feature_card(self, title: str, description: str, callback: Callable[[], None]) -> QWidget:
        card = self._card()
        card.setMinimumHeight(160)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 16px; font-weight: 850; color: #10213d;")
        layout.addWidget(heading)
        detail = QLabel(description)
        detail.setWordWrap(True)
        detail.setStyleSheet("color: #596b80; font-size: 12px;")
        layout.addWidget(detail)
        layout.addStretch()
        button = QPushButton("Apri  ›")
        button.setObjectName("primaryButton")
        button.clicked.connect(callback)
        layout.addWidget(button, 0, Qt.AlignRight)
        return card

    @staticmethod
    def _info_row(tag: str, title: str, detail: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 6, 4, 6)
        tag_label = QLabel(tag)
        tag_label.setFixedWidth(44)
        tag_label.setStyleSheet("font-weight: 850; color: #164d9b;")
        layout.addWidget(tag_label)
        text = QVBoxLayout()
        heading = QLabel(title)
        heading.setStyleSheet("font-weight: 750;")
        text.addWidget(heading)
        subtitle = QLabel(detail)
        subtitle.setStyleSheet("color: #64758a; font-size: 11px;")
        text.addWidget(subtitle)
        layout.addLayout(text)
        return row

    def _action_row(self, icon: str, title: str, callback: Callable[[], None]) -> QWidget:
        button = QPushButton(f"{icon}  {title}  ›")
        button.setObjectName("actionButton")
        button.clicked.connect(callback)
        return button

    @staticmethod
    def _status_row(icon: str, title: str, detail: str, status: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(2, 5, 2, 5)
        layout.addWidget(QLabel(icon))
        text = QVBoxLayout()
        heading = QLabel(title)
        heading.setStyleSheet("font-weight: 750;")
        text.addWidget(heading)
        subtitle = QLabel(detail)
        subtitle.setStyleSheet("color: #64758a; font-size: 11px;")
        text.addWidget(subtitle)
        layout.addLayout(text)
        layout.addStretch()
        badge = QLabel(status)
        badge.setStyleSheet(
            "background: #e1f6e8; color: #18733b; border-radius: 10px; padding: 4px 8px; font-weight: 800;"
        )
        layout.addWidget(badge)
        return row

    def _small_link(self, label: str, url: str) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("actionButton")
        button.clicked.connect(lambda _checked=False, address=url: self.open_web_link(address))
        return button

    def _quick_links(self) -> list[tuple[str, str, str]]:
        return [
            ("gmail_admin", "📧 Gmail SPES", "https://mail.google.com/mail/?authuser=0"),
            ("gmail_segreteria", "📧 Gmail Segreteria", "https://mail.google.com/mail/?authuser=segreteria@spesginnasticamestre.it"),
            ("gmail_consiglio", "📧 Gmail Consiglio", "https://mail.google.com/mail/?authuser=consiglio@spesginnasticamestre.it"),
            ("drive", "☁️ Drive SPES", "https://drive.google.com/drive/u/4/home"),
            ("sportivi", "🌐 Sportivi in Cloud", "https://www.cloud32.it/GES/home"),
            ("wellness", "💪 Wellness in Cloud", "https://new.wellness.incloud.it/dashboard"),
            ("spes_connect", "🔗 SPES Connect", "https://connect.spesginnasticamestre.it/dashboard"),
        ]

    def _all_web_links(self) -> list[tuple[str, str, str]]:
        return [
            ("sportivi", "🌐 Sportivi in Cloud", "https://www.cloud32.it/GES/home"),
            ("wellness", "💪 Wellness in Cloud", "https://new.wellness.incloud.it/dashboard"),
            ("cassa_cloud", "💳 Cassa in Cloud", "https://fo.cassanova.com/#/dashboard"),
            ("spes_connect", "🔗 SPES Connect", "https://connect.spesginnasticamestre.it/dashboard"),
            ("gmail_admin", "📧 Gmail SPES", "https://mail.google.com/mail/?authuser=0"),
            ("gmail_segreteria", "📧 Gmail Segreteria", "https://mail.google.com/mail/?authuser=segreteria@spesginnasticamestre.it"),
            ("gmail_consiglio", "📧 Gmail Consiglio", "https://mail.google.com/mail/?authuser=consiglio@spesginnasticamestre.it"),
            ("pec", "✉️ PEC SPES", "https://idp.infocert.it/login?clientName=legalmail_webmail_2023_i4&flowId=39c034a7-6c7e-488e-9abf-7ff15fe352c8&customization=legalmail_webmail_2023_i4&legacy=true&passwordless=true"),
            ("drive", "☁️ Drive SPES", "https://drive.google.com/drive/u/4/home"),
            ("homebank_volksbank", "🏦 Volksbank", "https://cobaweb.volksbank.it/"),
            ("homebank_bcc", "🏦 BCC", "https://www.relaxbanking.it/v3/relaxbanking/"),
            ("homebank_nexi", "💳 Nexi", "https://business.nexi.it/login-business"),
            ("music_gare", "🎵 Musica gare", "https://open.spotify.com/playlist/43fGlA3pU5xsLSRbYg9198"),
            ("music_awards", "🏅 Musica premiazioni", "https://open.spotify.com/playlist/0QjHGc2S4ggUNNjQTXlENa"),
            ("site", "🌐 Sito SPES", "https://www.spesginnasticamestre.it"),
        ]

    def _handle_search(self, query: str) -> None:
        text = query.strip().lower()
        if not text:
            return
        routes = {
            "fgi": "fgi",
            "risultati": "fgi",
            "calendario": "fgi",
            "regolamento": "fgi",
            "banca": "admin",
            "cassa": "admin",
            "csv": "admin",
            "gmail": "web",
            "wellness": "web",
            "drive": "web",
            "documenti": "documents",
            "impostazioni": "system",
        }
        for keyword, page in routes.items():
            if keyword in text:
                self._select_page(page)
                self.statusBar().showMessage(f"Ricerca: {query}", 4000)
                return
        QMessageBox.information(self, "Ricerca", f"Nessun collegamento rapido trovato per: {query}")

    def _can(self, permission: str) -> bool:
        return self.current_user.can(permission)

    def open_csv_archive(self) -> None:
        self.user_store.database.log(self.current_user.username, "navigation", "open_csv_archive")
        path = archive_root()
        path.mkdir(parents=True, exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, "Archivio CSV", "Impossibile aprire la cartella archivio CSV.")

    def open_fgi_calendar(self) -> None:
        self.statusBar().showMessage("Ricerca dell'ultimo calendario FGI Veneto...", 10000)
        try:
            document = update_fgi_calendar()
        except Exception as exc:
            cached = load_latest_calendar()
            if cached and Path(cached.local_path).exists():
                answer = QMessageBox.question(
                    self,
                    "Calendario gare FGI Veneto",
                    f"Aggiornamento non riuscito:\n{exc}\n\nAprire l'ultimo calendario salvato?",
                )
                if answer == QMessageBox.Yes:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(cached.local_path))
                return
            QMessageBox.warning(self, "Calendario gare FGI Veneto", str(exc))
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(document.local_path)):
            QMessageBox.warning(self, "Calendario gare FGI Veneto", "Il PDF è stato scaricato ma non può essere aperto.")

    def open_fgi_regulation(self) -> None:
        pdf_path = resource_path("assets/docs/TUNS_2027.pdf")
        if not pdf_path.exists():
            QMessageBox.warning(self, "Regolamento FGI", "Il PDF TUNS 2027 non è presente nell'installazione.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path))):
            QMessageBox.warning(self, "Regolamento FGI", "Impossibile aprire il PDF.")

    def open_web_link(self, url: str) -> None:
        if not webbrowser.open(url, new=2):
            QMessageBox.warning(self, "Collegamento non aperto", f"Impossibile aprire:\n{url}")
        else:
            self.user_store.database.log(self.current_user.username, "navigation", "open_web_link", url)

    def open_fgi_results(self) -> None:
        self.user_store.database.log(self.current_user.username, "navigation", "open_fgi_results")
        if self.fgi_results_window is None:
            self.fgi_results_window = FgiResultsWindow()
        self.fgi_results_window.refresh()
        self._show(self.fgi_results_window)

    def open_banking(self) -> None:
        self.user_store.database.log(self.current_user.username, "navigation", "open_banking")
        if self.banking_window is None:
            self.banking_window = BankingWindow()
        self._show(self.banking_window)

    def open_caf(self) -> None:
        self.user_store.database.log(self.current_user.username, "navigation", "open_compensation")
        if self.caf_window is None:
            self.caf_window = CafWindow()
        self._show(self.caf_window)

    def open_cash(self) -> None:
        self.user_store.database.log(self.current_user.username, "navigation", "open_cash")
        if self.cash_window is None:
            self.cash_window = CashWindow()
        self._show(self.cash_window)

    def open_activity_logs(self) -> None:
        if self.activity_log_window is None:
            self.activity_log_window = ActivityLogWindow(self.user_store)
        self.activity_log_window.refresh()
        self.user_store.database.log(self.current_user.username, "navigation", "open_activity_logs")
        self._show(self.activity_log_window)

    def open_settings(self) -> None:
        self.user_store.database.log(self.current_user.username, "navigation", "open_settings")
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.current_user)
        self._show(self.settings_window)

    def open_abi(self) -> None:
        if self.abi_window is None:
            self.abi_window = AbiWindow()
        self._show(self.abi_window)

    def open_history(self) -> None:
        if self.history_window is None:
            self.history_window = HistoryWindow()
        self.history_window.refresh()
        self._show(self.history_window)

    @staticmethod
    def _show(window: QWidget) -> None:
        window.show()
        window.raise_()
        window.activateWindow()

    def open_info(self) -> None:
        QMessageBox.information(
            self,
            "Informazioni",
            f"{APP_NAME}\nVersione {APP_VERSION}\nAutore: Cecchinato Simone\n"
            f"Utente: {self.current_user.display_name} ({self.current_user.role})\n\n"
            "Dashboard moderna, profili, permessi, archivio FGI locale e strumenti amministrativi.\n\n"
            f"© {ORGANIZATION_NAME}",
        )
