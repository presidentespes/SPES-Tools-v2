from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from spes_tools.services.storage import clear_history, load_history


class HistoryWindow(QWidget):
    HEADERS = ["Data e ora", "Modulo", "File origine", "File prodotto", "Righe", "Dettagli"]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SPES Tools - Storico")
        self.resize(1100, 620)
        self.records: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Storico elaborazioni")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #083b72;")
        layout.addWidget(title)

        buttons = QHBoxLayout()
        refresh_btn = QPushButton("Aggiorna")
        refresh_btn.clicked.connect(self.refresh)
        buttons.addWidget(refresh_btn)
        open_btn = QPushButton("Apri cartella output")
        open_btn.clicked.connect(self.open_output_folder)
        buttons.addWidget(open_btn)
        clear_btn = QPushButton("Cancella storico")
        clear_btn.clicked.connect(self.clear)
        buttons.addWidget(clear_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        self.records = load_history()
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            values = [
                record.get("timestamp", ""),
                record.get("module", ""),
                record.get("source", ""),
                record.get("output", ""),
                str(record.get("rows", "")),
                record.get("details", ""),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()

    def open_output_folder(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selezione mancante", "Seleziona una riga dello storico.")
            return
        output = self.records[row].get("output", "")
        if not output:
            return
        folder = Path(output).parent
        if not folder.exists():
            QMessageBox.warning(self, "Cartella non trovata", str(folder))
            return
        os.startfile(str(folder))

    def clear(self) -> None:
        answer = QMessageBox.question(self, "Conferma", "Cancellare tutto lo storico?")
        if answer != QMessageBox.Yes:
            return
        clear_history()
        self.refresh()
