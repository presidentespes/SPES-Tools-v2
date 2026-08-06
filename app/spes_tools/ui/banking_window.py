from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from spes_tools.banking.parsers import Movement, export_teamsystem_csv, parse_file
from spes_tools.services.export_naming import available_path, build_export_filename
from spes_tools.services.storage import (
    add_history,
    get_export_directory,
    set_export_directory,
)


class BankingWindow(QWidget):
    HEADERS = [
        "DATA", "VALUTA", "DARE", "AVERE", "CAUSALE", "CAUSALE ABI",
        "desc.causale", "SOGGETTO", "IBAN", "SPUNTATO",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SPES Configuratore Contabile - Riconciliazione bancaria")
        self.resize(1180, 720)
        self.movements: list[Movement] = []
        self.source_path = ""
        self.current_format = ""
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Riconciliazione bancaria")
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

        open_folder_btn = QPushButton("Apri cartella CSV")
        open_folder_btn.clicked.connect(self.open_export_folder)
        buttons.addWidget(open_folder_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.last_export_label = QLabel("Ultima esportazione: nessuna")
        self.last_export_label.setStyleSheet("color: #53657a;")
        layout.addWidget(self.last_export_label)

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
        self.source_path = path
        self.current_format = fmt
        self._fill_table()
        self.status.setText(f"Formato: {fmt} | Movimenti: {len(movements)} | File: {Path(path).name}")

    def export_csv(self) -> None:
        if not self.movements:
            QMessageBox.warning(self, "Nessun dato", "Apri prima un estratto conto.")
            return

        self._read_table()
        initial_directory = get_export_directory()
        if not initial_directory or not Path(initial_directory).is_dir():
            initial_directory = str(Path.home() / "Documents")

        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleziona la cartella di destinazione del CSV TeamSystem",
            initial_directory,
        )
        if not directory:
            return

        set_export_directory(directory)
        suggested_name = build_export_filename(self.current_format, self.movements)
        output_path = available_path(Path(directory) / suggested_name)

        try:
            export_teamsystem_csv(output_path, self.movements)
        except Exception as exc:
            QMessageBox.critical(self, "Errore esportazione", str(exc))
            return

        add_history(
            module="Riconciliazione bancaria",
            source=self.source_path,
            output=str(output_path),
            rows=len(self.movements),
            details=self.current_format,
        )
        self.last_export_label.setText(f"Ultima esportazione: {output_path.name}")
        self.last_export_label.setToolTip(str(output_path))
        QMessageBox.information(
            self,
            "Esportazione completata",
            f"File creato:\n{output_path}",
        )

    def open_export_folder(self) -> None:
        directory = get_export_directory()
        if not directory or not Path(directory).is_dir():
            initial_directory = str(Path.home() / "Documents")
            directory = QFileDialog.getExistingDirectory(
                self,
                "Seleziona la cartella dei CSV TeamSystem",
                initial_directory,
            )
            if not directory:
                return
            set_export_directory(directory)

        self._open_path(Path(directory))

    @staticmethod
    def _open_path(path: Path) -> None:
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            QMessageBox.critical(None, "Errore apertura cartella", str(exc))

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

