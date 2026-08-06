from __future__ import annotations

from collections.abc import Callable
import webbrowser
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from spes_tools.resources import resource_path
from spes_tools.services.fgi_calendar import load_latest_calendar, update_fgi_calendar
from spes_tools.services.storage import archive_root
from spes_tools.ui.abi_window import AbiWindow
from spes_tools.ui.banking_window import BankingWindow
from spes_tools.ui.caf_window import CafWindow
from spes_tools.ui.cash_window import CashWindow
from spes_tools.ui.history_window import HistoryWindow
from spes_tools.ui.fgi_results_window import FgiResultsWindow
from spes_tools.ui.settings_window import SettingsWindow
from spes_tools.version import APP_NAME, APP_VERSION, ORGANIZATION_NAME


class DashboardBackground(QWidget):
    """Widget che disegna lo sfondo della dashboard adattandolo alla finestra."""

    def __init__(self) -> None:
        super().__init__()
        self._background = QPixmap(str(resource_path("assets/dashboard_bg.png")))

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if not self._background.isNull():
            scaled = self._background.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.fillRect(self.rect(), QColor("#061c38"))

        # Velo scuro per mantenere sempre leggibili pulsanti e testi.
        painter.fillRect(self.rect(), QColor(2, 17, 42, 105))
        super().paintEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.banking_window: BankingWindow | None = None
        self.caf_window: CafWindow | None = None
        self.cash_window: CashWindow | None = None
        self.abi_window: AbiWindow | None = None
        self.history_window: HistoryWindow | None = None
        self.settings_window: SettingsWindow | None = None
        self.fgi_results_window: FgiResultsWindow | None = None

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(1180, 760)
        self.resize(1450, 920)
        self._build_ui()

    def _build_ui(self) -> None:
        background = DashboardBackground()
        self.setCentralWidget(background)

        outer = QVBoxLayout(background)
        outer.setContentsMargins(22, 14, 22, 10)
        outer.setSpacing(10)

        outer.addWidget(self._build_title())

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(0)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 4)
        grid.setColumnStretch(2, 3)

        grid.addWidget(self._build_left_panel(), 0, 0)
        grid.addWidget(self._build_center_panel(), 0, 1)
        grid.addWidget(self._build_right_panel(), 0, 2)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea {background: transparent;} QScrollArea > QWidget > QWidget {background: transparent;}")
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        outer.addWidget(self._build_bottom_bar())

        status = QStatusBar()
        status.setStyleSheet(
            "QStatusBar {background: rgba(3, 20, 48, 220); color: #dcecff; "
            "border-top: 1px solid rgba(80, 190, 255, 120); padding-left: 6px;}"
        )
        status.showMessage(f"Pronto • {APP_NAME} {APP_VERSION}")
        self.setStatusBar(status)

    def _build_title(self) -> QWidget:
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("SPES")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color: white; font-size: 46px; font-weight: 900; letter-spacing: 4px;"
        )
        layout.addWidget(title)

        subtitle = QLabel("CONFIGURATORE CONTABILE")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: white; font-size: 23px; font-weight: 750;")
        layout.addWidget(subtitle)

        version = QLabel(APP_VERSION)
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #ff4aa2; font-size: 20px; font-weight: 800;")
        layout.addWidget(version)
        return header

    def _build_left_panel(self) -> QWidget:
        panel = self._panel("#08bdf7")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(7)

        layout.addWidget(self._section_title("GESTIONALI", "#23d3ff"))
        for text, url in (
            ("🌐  Sportivi in Cloud", "https://www.cloud32.it/GES/home"),
            ("💪  Wellness in Cloud", "https://new.wellness.incloud.it/dashboard"),
            ("💳  Cassa in Cloud", "https://fo.cassanova.com/#/dashboard"),
            ("☁️  SPES Connect", "https://connect.spesginnasticamestre.it/dashboard"),
        ):
            layout.addWidget(self._web_button(text, url, accent="#0bbbf0"))

        layout.addSpacing(5)
        layout.addWidget(self._section_title("HOME BANKING", "#23d3ff"))
        for text, url in (
            ("🏦  Volksbank", "https://cobaweb.volksbank.it/"),
            ("🏦  BCC", "https://www.relaxbanking.it/v3/relaxbanking/"),
            ("💳  Nexi", "https://business.nexi.it/login-business"),
        ):
            layout.addWidget(self._web_button(text, url, accent="#0bbbf0"))

        layout.addStretch()
        return panel

    def _build_center_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        logo_path = resource_path("assets/logo_spes_3d.png")
        logo_button = QPushButton()
        logo_button.setCursor(Qt.PointingHandCursor)
        logo_button.setToolTip("Apri il sito SPES Ginnastica Mestre")
        logo_button.setAccessibleName("Apri il sito SPES Ginnastica Mestre")
        logo_button.setIcon(QIcon(str(logo_path)))
        logo_button.setIconSize(QSize(310, 310))
        logo_button.setFixedSize(330, 330)
        logo_button.setStyleSheet(
            "QPushButton {background: transparent; border: none;}"
            "QPushButton:hover {background: rgba(255, 255, 255, 18); border: 2px solid #f2c84b; border-radius: 165px;}"
            "QPushButton:pressed {background: rgba(255, 255, 255, 35);}"
        )
        logo_button.clicked.connect(
            lambda: self.open_web_link("https://www.spesginnasticamestre.it")
        )
        layout.addWidget(logo_button, 0, Qt.AlignCenter)

        hint = QLabel("CLICCA SUL LOGO PER ACCEDERE AL SITO")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: white; font-size: 12px; font-weight: 750;")
        layout.addWidget(hint)

        name = QLabel("SPES")
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("color: white; font-size: 42px; font-weight: 900; letter-spacing: 3px;")
        layout.addWidget(name)

        subtitle = QLabel("GINNASTICA MESTRE")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: white; font-size: 22px; font-weight: 750;")
        layout.addWidget(subtitle)
        layout.addStretch()
        return panel

    def _build_right_panel(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        modules = self._panel("#ff4aa2")
        module_layout = QVBoxLayout(modules)
        module_layout.setContentsMargins(14, 14, 14, 14)
        module_layout.setSpacing(8)
        module_layout.addWidget(self._section_title("MODULI SPES", "#ff62b2"))
        module_layout.addWidget(self._module_button("🏦  Riconciliazione bancaria", self.open_banking))
        module_layout.addWidget(self._module_button("💶  Convertitore compensi", self.open_caf))
        module_layout.addWidget(self._module_button("💰  Gestione Cassa", self.open_cash))
        layout.addWidget(modules)

        communication = self._panel("#ff4aa2")
        communication_layout = QVBoxLayout(communication)
        communication_layout.setContentsMargins(14, 14, 14, 14)
        communication_layout.setSpacing(8)
        communication_layout.addWidget(self._section_title("COMUNICAZIONE", "#ff62b2"))
        for text, url in (
            ("📧  Gmail", "https://mail.google.com/"),
            (
                "✉️  PEC SPES",
                "https://idp.infocert.it/login?clientName=legalmail_webmail_2023_i4&flowId=39c034a7-6c7e-488e-9abf-7ff15fe352c8&customization=legalmail_webmail_2023_i4&legacy=true&passwordless=true",
            ),
            ("☁️  Drive SPES", "https://drive.google.com/drive/u/4/home"),
        ):
            communication_layout.addWidget(self._web_button(text, url, accent="#ff4aa2"))
        layout.addWidget(communication)
        layout.addStretch()
        return wrapper

    def _build_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            "QWidget {background: rgba(3, 25, 58, 220); border: 1px solid rgba(64, 188, 255, 140); border-radius: 12px;}"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(7)

        buttons: tuple[tuple[str, Callable[[], None]], ...] = (
            ("📂 Archivio CSV", self.open_csv_archive),
            ("📅 Calendario gare", self.open_fgi_calendar),
            ("🏆 Risultati FGI", self.open_fgi_results),
            ("📘 Regolamento FGI", self.open_fgi_regulation),
            (
                "🎵 Musica gare",
                lambda: self.open_web_link(
                    "https://open.spotify.com/playlist/43fGlA3pU5xsLSRbYg9198"
                ),
            ),
            (
                "🏅 Musica premiazioni",
                lambda: self.open_web_link(
                    "https://open.spotify.com/playlist/0QjHGc2S4ggUNNjQTXlENa"
                ),
            ),
            ("⚙️ Impostazioni", self.open_settings),
        )
        for text, callback in buttons:
            button = QPushButton(text)
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(42)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(callback)
            button.setStyleSheet(
                "QPushButton {background: rgba(4, 34, 76, 235); color: white; border: 1px solid #1b8fc6; "
                "border-radius: 8px; padding: 6px 10px; font-size: 12px; font-weight: 700;}"
                "QPushButton:hover {background: #0a4a87; border-color: #4ad0ff;}"
                "QPushButton:pressed {background: #062d58;}"
            )
            layout.addWidget(button)
        return bar

    @staticmethod
    def _panel(accent: str) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(
            "QWidget {background: rgba(2, 25, 58, 218); border: 1px solid "
            f"{accent}; border-radius: 14px;}}"
        )
        return panel

    @staticmethod
    def _section_title(text: str, color: str) -> QLabel:
        title = QLabel(text)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"border: none; color: {color}; font-size: 15px; font-weight: 800; padding: 4px;"
        )
        return title

    def _web_button(self, text: str, url: str, accent: str) -> QPushButton:
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedHeight(40)
        button.setToolTip(f"Apri {url} nel browser predefinito")
        button.clicked.connect(lambda _checked=False, address=url: self.open_web_link(address))
        button.setStyleSheet(
            "QPushButton {background: rgba(250, 252, 255, 245); color: #092653; border: 1px solid #d8e2ef; "
            "border-radius: 8px; padding: 5px 9px; font-size: 12px; font-weight: 700; text-align: left;}"
            f"QPushButton:hover {{background: white; border: 2px solid {accent};}}"
            "QPushButton:pressed {background: #dce9f6;}"
        )
        return button

    @staticmethod
    def _module_button(text: str, callback: Callable[[], None]) -> QPushButton:
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedHeight(54)
        button.clicked.connect(callback)
        button.setStyleSheet(
            "QPushButton {background: rgba(250, 252, 255, 245); color: #092653; border: 1px solid #d8e2ef; "
            "border-radius: 9px; padding: 7px 10px; font-size: 13px; font-weight: 750; text-align: left;}"
            "QPushButton:hover {background: white; border: 2px solid #ff4aa2;}"
            "QPushButton:pressed {background: #f4ddea;}"
        )
        return button

    def open_csv_archive(self) -> None:
        path = archive_root()
        path.mkdir(parents=True, exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, "Archivio CSV", "Impossibile aprire la cartella archivio CSV.")
        else:
            self.statusBar().showMessage("Aperto: Archivio CSV", 4000)

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
            QMessageBox.warning(
                self,
                "Calendario gare FGI Veneto",
                "Il calendario è stato scaricato, ma Windows non riesce ad aprire il PDF.",
            )
            return
        self.statusBar().showMessage(f"Aperto: {document.title}", 5000)

    def open_fgi_regulation(self) -> None:
        """Apre il regolamento FGI 2027 incluso nell'applicazione."""
        pdf_path = resource_path("assets/docs/TUNS_2027.pdf")
        if not pdf_path.exists():
            QMessageBox.warning(
                self,
                "Regolamento FGI",
                "Il PDF del Regolamento FGI 2027 non è presente nell'installazione.",
            )
            return

        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path))):
            QMessageBox.warning(
                self,
                "Regolamento FGI",
                "Impossibile aprire il PDF. Verifica che sul PC sia installato un lettore PDF.",
            )

    def open_web_link(self, url: str) -> None:
        if not webbrowser.open(url, new=2):
            QMessageBox.warning(
                self,
                "Collegamento non aperto",
                f"Impossibile aprire il collegamento:\n{url}",
            )
        else:
            self.statusBar().showMessage("Collegamento aperto nel browser", 4000)

    def open_fgi_results(self) -> None:
        if self.fgi_results_window is None:
            self.fgi_results_window = FgiResultsWindow()
        self.fgi_results_window.refresh()
        self.statusBar().showMessage("Aperto: Risultati FGI SPES", 5000)
        self._show(self.fgi_results_window)

    def open_banking(self) -> None:
        if self.banking_window is None:
            self.banking_window = BankingWindow()
        self.statusBar().showMessage("Aperto: Riconciliazione bancaria", 5000)
        self._show(self.banking_window)

    def open_caf(self) -> None:
        if self.caf_window is None:
            self.caf_window = CafWindow()
        self.statusBar().showMessage("Aperto: Convertitore compensi", 5000)
        self._show(self.caf_window)

    def open_cash(self) -> None:
        if self.cash_window is None:
            self.cash_window = CashWindow()
        self.statusBar().showMessage("Aperto: Gestione cassa", 5000)
        self._show(self.cash_window)

    def open_settings(self) -> None:
        if self.settings_window is None:
            self.settings_window = SettingsWindow()
        self.statusBar().showMessage("Aperto: Impostazioni", 5000)
        self._show(self.settings_window)

    def open_abi(self) -> None:
        if self.abi_window is None:
            self.abi_window = AbiWindow()
        self.statusBar().showMessage("Aperto: Causali ABI", 5000)
        self._show(self.abi_window)

    def open_history(self) -> None:
        if self.history_window is None:
            self.history_window = HistoryWindow()
        self.history_window.refresh()
        self.statusBar().showMessage("Aperto: Storico operazioni", 5000)
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
            f"{APP_NAME}\nVersione {APP_VERSION}\n\n"
            "Moduli attivi:\n"
            "• Riconciliazione bancaria\n"
            "• Convertitore compensi\n"
            "• Gestione cassa CSV/Excel\n"
            "• Configurazione causali ABI e regole automatiche\n"
            "• Storico operazioni\n"
            "• Risultati FGI SPES con filtro atleta\n"
            "• Backup, ripristino e aggiornamenti\n\n"
            f"© {ORGANIZATION_NAME}",
        )
