from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from spes_tools.services.auth import UserStore


class ActivityLogWindow(QWidget):
    def __init__(self, store: UserStore | None = None) -> None:
        super().__init__()
        self.store = store or UserStore()
        self.setWindowTitle("Registro attività")
        self.resize(980, 620)
        layout = QVBoxLayout(self)
        title = QLabel("Registro attività Consolle SPES")
        title.setStyleSheet("font-size: 23px; font-weight: 800; color: #073b84;")
        layout.addWidget(title)
        toolbar = QHBoxLayout()
        refresh = QPushButton("Aggiorna")
        refresh.clicked.connect(self.refresh)
        toolbar.addWidget(refresh)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Data e ora", "Utente", "Categoria", "Operazione", "Dettagli", "ID"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.refresh()

    def refresh(self) -> None:
        rows = self.store.recent_logs(500)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row.get("timestamp", "")).replace("T", " "),
                str(row.get("username") or "-"),
                str(row.get("category", "")),
                str(row.get("action", "")),
                str(row.get("details", "")),
                str(row.get("id", "")),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
