from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from spes_tools.resources import resource_path
from spes_tools.ui.abi_window import AbiWindow
from spes_tools.ui.banking_window import BankingWindow
from spes_tools.ui.caf_window import CafWindow
from spes_tools.ui.history_window import HistoryWindow


APP_NAME = "SPES Configuratore Contabile"
APP_VERSION = "4.0"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.banking_window: BankingWindow | None = None
        self.caf_window: CafWindow | None = None
        self.abi_window: AbiWindow | None = None
        self.history_window: HistoryWindow | None = None

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1040, 760)

        central = QWidget()
        central.setStyleSheet("background: #f3f6f9;")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(16)

        header = QWidget()
        header.setStyleSheet(
            "QWidget {background: #073b84; border-radius: 14px;}"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 22, 14)

        logo = QLabel()
        pixmap = QPixmap(str(resource_path("assets/logo_spes.png")))
        if not pixmap.isNull():
            logo.setPixmap(
                pixmap.scaled(
                    112,
                    112,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        logo.setFixedSize(118, 118)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("background: transparent;")
        header_layout.addWidget(logo)

        text_layout = QVBoxLayout()
        title = QLabel(APP_NAME)
        title.setStyleSheet(
            "font-size: 30px; font-weight: 700; color: white; background: transparent;"
        )
        text_layout.addWidget(title)

        subtitle = QLabel(
            "Strumenti professionali per contabilità, riconciliazione bancaria "
            "e gestione compensi"
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "font-size: 15px; color: #f7d447; background: transparent;"
        )
        text_layout.addWidget(subtitle)
        text_layout.addStretch()
        header_layout.addLayout(text_layout, 1)
        main_layout.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        main_layout.addLayout(grid)

        modules = [
            ("Riconciliazione bancaria", "Nexi, BCC, Volksbank e CSV TeamSystem", self.open_banking),
            ("Bonifici SEPA", "Conversione bonifici e beneficiari", self.open_banking),
            ("Convertitore compensi", "Calcolo lordo ↔ netto con anteprima", self.open_caf),
            ("Causali ABI", "Configurazione codici per banca", self.open_abi),
            ("Storico operazioni", "Esportazioni e calcoli effettuati", self.open_history),
            ("Informazioni", "Versione e dati dell'applicazione", self.open_info),
        ]
        for index, (label, description, callback) in enumerate(modules):
            grid.addWidget(
                self._card(label, description, callback),
                index // 2,
                index % 2,
            )

        footer = QLabel(f"{APP_NAME} • Versione {APP_VERSION}")
        footer.setAlignment(Qt.AlignRight)
        footer.setStyleSheet("color: #53657a; padding: 4px;")
        main_layout.addWidget(footer)

    def _card(self, title: str, description: str, callback) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            "QWidget {background: white; border: 1px solid #d6dde5; border-radius: 12px;}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)

        label = QLabel(title)
        label.setStyleSheet(
            "border: none; font-size: 18px; font-weight: 700; color: #073b84;"
        )
        layout.addWidget(label)

        detail = QLabel(description)
        detail.setWordWrap(True)
        detail.setStyleSheet("border: none; color: #53657a; font-size: 13px;")
        layout.addWidget(detail)
        layout.addStretch()

        button = QPushButton("Apri")
        button.clicked.connect(callback)
        button.setStyleSheet(
            "QPushButton {background: #073b84; color: white; padding: 10px; "
            "border: none; border-radius: 7px; font-weight: 600;}"
            "QPushButton:hover {background: #0b56b3;}"
            "QPushButton:pressed {background: #062e66;}"
        )
        layout.addWidget(button)
        return card

    def open_banking(self) -> None:
        if self.banking_window is None:
            self.banking_window = BankingWindow()
        self._show(self.banking_window)

    def open_caf(self) -> None:
        if self.caf_window is None:
            self.caf_window = CafWindow()
        self._show(self.caf_window)

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
            f"{APP_NAME}\nVersione {APP_VERSION}\n\n"
            "Moduli attivi:\n"
            "- Riconciliazione bancaria e Bonifici SEPA\n"
            "- Convertitore compensi\n"
            "- Configurazione causali ABI\n"
            "- Storico operazioni\n\n"
            "© Associazione Sportiva Dilettantistica SPES Mestre Ginnastica",
        )
