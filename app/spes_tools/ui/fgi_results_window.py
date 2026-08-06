from __future__ import annotations

import webbrowser
from datetime import date
from pathlib import Path

from PySide6.QtCore import QObject, QDate, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from spes_tools.services.fgi_results import (
    FGI_CLUB_CODE,
    FgiResult,
    current_season,
    export_results_csv,
    export_results_xlsx,
    load_results,
    last_results_update,
    update_fgi_results,
)


class FgiUpdateWorker(QObject):
    progress = Signal(str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, start_date: date, end_date: date) -> None:
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date

    @Slot()
    def run(self) -> None:
        try:
            report = update_fgi_results(
                self.start_date,
                self.end_date,
                progress=self.progress.emit,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.completed.emit(report)


class FgiResultsWindow(QWidget):
    COLUMNS = (
        "Data",
        "Disciplina",
        "Gara",
        "Atleta",
        "Categoria",
        "Posizione",
        "Punteggio",
        "Attrezzo",
        "Fonte",
    )

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SPES - Risultati FGI")
        self.resize(1280, 760)
        self._all_results: list[FgiResult] = []
        self._visible_results: list[FgiResult] = []
        self._thread: QThread | None = None
        self._worker: FgiUpdateWorker | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Risultati FGI - SPES Mestre")
        title.setStyleSheet("font-size: 25px; font-weight: 800; color: #073b84;")
        layout.addWidget(title)
        subtitle = QLabel(
            f"Società FGI {FGI_CLUB_CODE} • ricerca immediata nell'archivio locale • "
            "aggiornamento automatico ogni lunedì alle 01:00"
        )
        subtitle.setStyleSheet("color: #53657a;")
        layout.addWidget(subtitle)

        controls = QHBoxLayout()
        start, end, _ = current_season()
        self.start_date = QDateEdit(QDate(start.year, start.month, start.day))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        self.end_date = QDateEdit(QDate(end.year, end.month, end.day))
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd/MM/yyyy")
        controls.addWidget(QLabel("Dal"))
        controls.addWidget(self.start_date)
        controls.addWidget(QLabel("Al"))
        controls.addWidget(self.end_date)

        self.athlete_filter = QLineEdit()
        self.athlete_filter.setPlaceholderText("Cerca atleta per nome o cognome")
        self.athlete_filter.textChanged.connect(self.apply_filters)
        controls.addWidget(self.athlete_filter, 1)

        self.discipline_filter = QComboBox()
        self.discipline_filter.addItem("Tutte le discipline")
        self.discipline_filter.currentTextChanged.connect(self.apply_filters)
        controls.addWidget(self.discipline_filter)
        layout.addLayout(controls)

        actions = QHBoxLayout()
        self.update_button = QPushButton("Aggiorna ora archivio FGI")
        self.update_button.clicked.connect(self.update_now)
        actions.addWidget(self.update_button)
        open_source = QPushButton("Apri classifica originale")
        open_source.clicked.connect(self.open_selected_source)
        actions.addWidget(open_source)
        export_csv = QPushButton("Esporta CSV")
        export_csv.clicked.connect(self.export_csv)
        actions.addWidget(export_csv)
        export_xlsx = QPushButton("Esporta Excel")
        export_xlsx.clicked.connect(self.export_xlsx)
        actions.addWidget(export_xlsx)
        refresh = QPushButton("Ricarica archivio")
        refresh.clicked.connect(self.refresh)
        actions.addWidget(refresh)
        layout.addLayout(actions)

        self.progress_label = QLabel("Pronto")
        self.progress_label.setStyleSheet("color: #53657a;")
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 95)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(2, 320)
        self.table.setColumnWidth(3, 210)
        self.table.setColumnWidth(4, 130)
        layout.addWidget(self.table, 1)

        self.count_label = QLabel()
        layout.addWidget(self.count_label)

    def refresh(self) -> None:
        self._all_results = load_results()
        last_update = last_results_update()
        if last_update is None:
            self.progress_label.setText(
                "Archivio locale non ancora aggiornato: il primo download è in esecuzione o va avviato manualmente."
            )
        else:
            self.progress_label.setText(
                "Archivio locale aggiornato il " + last_update.strftime("%d/%m/%Y alle %H:%M")
            )
        disciplines = sorted({item.discipline for item in self._all_results if item.discipline})
        current = self.discipline_filter.currentText()
        self.discipline_filter.blockSignals(True)
        self.discipline_filter.clear()
        self.discipline_filter.addItem("Tutte le discipline")
        self.discipline_filter.addItems(disciplines)
        index = self.discipline_filter.findText(current)
        if index >= 0:
            self.discipline_filter.setCurrentIndex(index)
        self.discipline_filter.blockSignals(False)
        self.apply_filters()

    @Slot()
    def apply_filters(self) -> None:
        athlete = self.athlete_filter.text().strip().casefold()
        discipline = self.discipline_filter.currentText()
        rows = []
        for item in self._all_results:
            if athlete and athlete not in item.athlete.casefold() and athlete not in item.raw_row.casefold():
                continue
            if discipline != "Tutte le discipline" and item.discipline != discipline:
                continue
            rows.append(item)
        self._visible_results = rows
        self._render(rows)

    def _render(self, rows: list[FgiResult]) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row_index, item in enumerate(rows):
            values = (
                item.date,
                item.discipline,
                item.competition,
                item.athlete,
                item.category,
                item.position,
                item.score,
                item.apparatus,
                item.source_url,
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column in (5, 6):
                    cell.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_index, column, cell)
        self.table.setSortingEnabled(True)
        self.count_label.setText(
            f"Risultati visualizzati: {len(rows)} • archivio totale: {len(self._all_results)}"
        )

    @Slot()
    def update_now(self) -> None:
        if self._thread is not None:
            return
        start_q = self.start_date.date()
        end_q = self.end_date.date()
        start = date(start_q.year(), start_q.month(), start_q.day())
        end = date(end_q.year(), end_q.month(), end_q.day())
        if end < start:
            QMessageBox.warning(self, "Periodo non valido", "La data finale precede quella iniziale.")
            return

        self.update_button.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText("Connessione al sito FGI...")
        thread = QThread(self)
        worker = FgiUpdateWorker(start, end)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self.progress_label.setText)
        worker.completed.connect(self._update_completed)
        worker.failed.connect(self._update_failed)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._thread_finished)
        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot(object)
    def _update_completed(self, report) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.progress_label.setText(
            f"Aggiornamento completato: {report.added_results} nuovi risultati, "
            f"{report.scanned_documents} classifiche analizzate."
        )
        self.refresh()
        message = (
            f"Nuovi risultati: {report.added_results}\n"
            f"Righe SPES trovate: {report.matching_rows}\n"
            f"Classifiche analizzate: {report.scanned_documents}\n"
            f"Archivio totale: {report.total_results}"
        )
        if report.warnings:
            message += f"\n\nAvvisi: {len(report.warnings)} (mostrati nel log dell'aggiornamento)."
        QMessageBox.information(self, "Risultati FGI aggiornati", message)

    @Slot(str)
    def _update_failed(self, message: str) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Aggiornamento non riuscito")
        QMessageBox.critical(
            self,
            "Errore aggiornamento FGI",
            "Impossibile aggiornare le classifiche.\n\n" + message,
        )

    @Slot()
    def _thread_finished(self) -> None:
        self.update_button.setEnabled(True)
        self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None

    def open_selected_source(self) -> None:
        selected = self.table.currentRow()
        if selected < 0 or selected >= len(self._visible_results):
            QMessageBox.information(self, "Fonte FGI", "Seleziona prima un risultato.")
            return
        webbrowser.open(self._visible_results[selected].source_url, new=2)

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Esporta risultati FGI", "risultati_fgi_spes.csv", "CSV (*.csv)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        export_results_csv(path, self._visible_results)
        QMessageBox.information(self, "Esportazione completata", path)

    def export_xlsx(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Esporta risultati FGI", "risultati_fgi_spes.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        export_results_xlsx(path, self._visible_results)
        QMessageBox.information(self, "Esportazione completata", path)
