from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from spes_tools.resources import resource_path
from spes_tools.ui.abi_window import AbiWindow
from spes_tools.ui.banking_window import BankingWindow
from spes_tools.ui.caf_window import CafWindow
from spes_tools.ui.cash_window import CashWindow
from spes_tools.ui.history_window import HistoryWindow
from spes_tools.version import APP_NAME, APP_VERSION, ORGANIZATION_NAME


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.banking_window: BankingWindow | None = None
        self.caf_window: CafWindow | None = None
        self.cash_window: CashWindow | None = None
        self.abi_window: AbiWindow | None = None
        self.history_window: HistoryWindow | None = None

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(980, 720)
        self.resize(1120, 820)
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet("#central {background: #f3f6f9;} QLabel {background: transparent;}")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 14)
        main_layout.setSpacing(16)
        main_layout.addWidget(self._build_header())

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        main_layout.addLayout(grid, 1)

        modules: list[tuple[str, str, str, Callable[[], None]]] = [
            ("🏦", "Riconciliazione bancaria", "Importa Nexi, BCC e Volksbank; controlla e crea il CSV TeamSystem.", self.open_banking),
            ("💳", "Bonifici SEPA", "Gestisci bonifici, beneficiari, causali e dati IBAN.", self.open_banking),
            ("💶", "Convertitore compensi", "Calcolo lordo ↔ netto, franchigie e anteprima immediata.", self.open_caf),
            ("💵", "Gestione cassa", "Registra entrate e uscite; importa ed esporta CSV o Excel.", self.open_cash),
            ("📚", "Causali ABI", "Configura codici e regole per Nexi, BCC, Volksbank e Cassa.", self.open_abi),
            ("📂", "Storico operazioni", "Consulta conversioni, esportazioni, cassa e calcoli effettuati.", self.open_history),
            ("ℹ", "Informazioni", "Versione, identità dell'applicazione e moduli disponibili.", self.open_info),
        ]

        for index, (icon, title, description, callback) in enumerate(modules):
            grid.addWidget(self._card(icon, title, description, callback), index // 2, index % 2)

        status = QStatusBar()
        status.setStyleSheet("QStatusBar {background: #ffffff; color: #53657a; border-top: 1px solid #d6dde5;}")
        status.showMessage(f"Pronto • {APP_NAME} {APP_VERSION}")
        self.setStatusBar(status)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setStyleSheet("QWidget {background: #073b84; border-radius: 15px;}")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 16, 24, 16)
        layout.setSpacing(18)

        logo = QLabel()
        pixmap = QPixmap(str(resource_path("assets/logo_spes.png")))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(116, 116, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setFixedSize(122, 122)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        texts = QVBoxLayout()
        texts.setSpacing(6)
        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 31px; font-weight: 750; color: white;")
        texts.addWidget(title)
        subtitle = QLabel("Contabilità • riconciliazione bancaria • compensi • cassa")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 15px; color: #f7d447;")
        texts.addWidget(subtitle)
        version = QLabel(f"Versione {APP_VERSION}")
        version.setStyleSheet("font-size: 12px; color: #dce8f8;")
        texts.addWidget(version)
        texts.addStretch()
        layout.addLayout(texts, 1)
        return header

    def _card(self, icon: str, title: str, description: str, callback: Callable[[], None]) -> QWidget:
        card = QWidget()
        card.setMinimumHeight(164)
        card.setStyleSheet("QWidget {background: white; border: 1px solid #d6dde5; border-radius: 13px;}")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        top = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFixedWidth(38)
        icon_label.setStyleSheet("border: none; font-size: 26px;")
        top.addWidget(icon_label)
        label = QLabel(title)
        label.setWordWrap(True)
        label.setStyleSheet("border: none; font-size: 18px; font-weight: 700; color: #073b84;")
        top.addWidget(label, 1)
        layout.addLayout(top)
        detail = QLabel(description)
        detail.setWordWrap(True)
        detail.setStyleSheet("border: none; color: #53657a; font-size: 13px;")
        layout.addWidget(detail)
        layout.addStretch()
        button = QPushButton("Apri modulo")
        button.clicked.connect(callback)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(
            "QPushButton {background: #073b84; color: white; padding: 10px; border: none; border-radius: 7px; font-weight: 650;}"
            "QPushButton:hover {background: #0b56b3;} QPushButton:pressed {background: #062e66;}"
        )
        layout.addWidget(button)
        return card

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
            "• Riconciliazione bancaria e Bonifici SEPA\n"
            "• Convertitore compensi\n"
            "• Gestione cassa CSV/Excel\n"
            "• Configurazione causali ABI e regole automatiche\n"
            "• Storico operazioni\n\n"
            f"© {ORGANIZATION_NAME}",
        )
