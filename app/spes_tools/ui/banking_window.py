from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from spes_tools.banking.parsers import Movement, export_teamsystem_csv, parse_file


class BankingWindow(QWidget):
    HEADERS = [
        "DATA", "VALUTA", "DARE", "AVERE", "CAUSALE", "CAUSALE ABI",
        "desc.causale", "SOGGETTO", "IBAN", "SPUNTATO",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SPES Tools - Convertitore bancario")
        self.resize(1180, 720)
        self.movements: list[Movement] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Convertitore bancario")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #083b72;")
        layout.addWidget(title)

        self.status = QLabel("Apri un estratto Nexi, BCC, Volksbank o BonSepa.")
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        open_btn = QPushButton("Apri file")
        open_btn.clicked.connect(self.open_file)
        buttons.addWidget(open_btn)
        export_btn = QPushButton("Esporta CSV TeamSystem")
        export_btn.clicked.connect(self.export_csv)
        buttons.addWidget(export_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Apri estratto", "",
            "Documenti bancari (*.pdf *.csv *.txt *.xls);;Tutti i file (*.*)",
        )
        if not path:
            return
        try:
            fmt, movements = parse_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Errore importazione", str(exc))
            return
        self.movements = movements
        self._fill_table()
        self.status.setText(f"Formato: {fmt} | Movimenti: {len(movements)} | File: {Path(path).name}")

    def export_csv(self) -> None:
        if not self.movements:
            QMessageBox.warning(self, "Nessun dato", "Apri prima un estratto conto.")
            return
        self._read_table()
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva CSV TeamSystem", "teamsystem_export.csv", "CSV (*.csv)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            export_teamsystem_csv(path, self.movements)
        except Exception as exc:
            QMessageBox.critical(self, "Errore esportazione", str(exc))
            return
        QMessageBox.information(self, "Esportazione completata", f"Creato:\n{path}")

    def _fill_table(self) -> None:
        self.table.setRowCount(len(self.movements))
        for r, m in enumerate(self.movements):
            values = [
                m.data, m.valuta, m.dare, m.avere, m.causale,
                m.causale_abi, m.desc_causale, m.soggetto, m.iban, m.spuntato,
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()

    def _read_table(self) -> None:
        rows: list[Movement] = []
        for r in range(self.table.rowCount()):
            values: list[str] = []
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                values.append(item.text() if item else "")
            rows.append(Movement(*values))
        self.movements = rows
