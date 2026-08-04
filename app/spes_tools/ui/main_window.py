from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from spes_tools.ui.banking_window import BankingWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.banking_window: BankingWindow | None = None
        self.setWindowTitle("SPES Tools")
        self.resize(980, 720)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        title = QLabel("SPES Tools")
        title.setStyleSheet("font-size: 30px; font-weight: bold; color: #083b72;")
        main_layout.addWidget(title)
        subtitle = QLabel("Strumenti per contabilità, conversioni bancarie e CAF")
        subtitle.setStyleSheet("font-size: 15px; color: #53657a;")
        main_layout.addWidget(subtitle)

        grid = QGridLayout()
        main_layout.addLayout(grid)
        modules = [
            ("Convertitore bancario", self.open_banking),
            ("Bonifici SEPA", self.open_banking),
            ("CAF Tools", lambda: self.placeholder("CAF Tools")),
            ("Causali ABI", lambda: self.placeholder("Causali ABI")),
            ("Storico", lambda: self.placeholder("Storico")),
            ("Informazioni", self.open_info),
        ]
        for index, (label, callback) in enumerate(modules):
            grid.addWidget(self._card(label, callback), index // 2, index % 2)

    def _card(self, title: str, callback) -> QWidget:
        card = QWidget()
        card.setStyleSheet("QWidget {background: white; border: 1px solid #d6dde5; border-radius: 12px;}")
        layout = QVBoxLayout(card)
        label = QLabel(title)
        label.setStyleSheet("border: none; font-size: 18px; font-weight: bold; color: #083b72;")
        layout.addWidget(label)
        button = QPushButton("Apri")
        button.clicked.connect(callback)
        button.setStyleSheet(
            "QPushButton {background: #2d6da3; color: white; padding: 10px; border: none; border-radius: 6px;}"
            "QPushButton:hover {background: #245a87;}"
        )
        layout.addWidget(button)
        return card

    def open_banking(self) -> None:
        if self.banking_window is None:
            self.banking_window = BankingWindow()
        self.banking_window.show()
        self.banking_window.raise_()
        self.banking_window.activateWindow()

    def placeholder(self, name: str) -> None:
        QMessageBox.information(self, name, f"Il modulo «{name}» sarà aggiunto nella fase successiva.")

    def open_info(self) -> None:
        QMessageBox.information(self, "Informazioni", "SPES Tools 2.0\nConvertitore bancario attivo.")
