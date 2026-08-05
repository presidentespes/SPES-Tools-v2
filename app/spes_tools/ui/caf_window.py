from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSignalBlocker
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from spes_tools.services.storage import add_history


from spes_tools.services.compensation import (
    CATEGORY_EMPLOYEE, CATEGORY_PENSIONER, CATEGORY_SPORT,
    SPORT_NO_OTHER_COVERAGE, SPORT_PENSION_OR_OTHER,
    Calculation, gross_for_target, ordinary_from_gross, sport_from_gross,
)


class CafWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SPES Configuratore Contabile - Convertitore compensi")
        self.resize(820, 760)
        self.last_result: Calculation | None = None
        self._build_ui()
        self._update_fields()
        self.calculate(show_errors=False)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Convertitore compensi")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #083b72;")
        layout.addWidget(title)
        subtitle = QLabel("Calcolo Lordo ↔ Netto • anteprima immediata")
        subtitle.setStyleSheet("color: #53657a;")
        layout.addWidget(subtitle)

        self.form = QFormLayout()

        self.category = QComboBox()
        self.category.addItems([CATEGORY_EMPLOYEE, CATEGORY_PENSIONER, CATEGORY_SPORT])
        self.category.currentTextChanged.connect(self._update_fields)
        self.form.addRow("Categoria", self.category)

        self.direction = QComboBox()
        self.direction.addItems(["Netto → Lordo", "Lordo → Netto"])
        self.form.addRow("Direzione", self.direction)

        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 10_000_000)
        self.amount.setDecimals(2)
        self.amount.setValue(1_000.00)
        self.amount.setPrefix("€ ")
        self.form.addRow("Importo", self.amount)

        self.sport_profile_label = QLabel("Profilo sportivo")
        self.sport_profile = QComboBox()
        self.sport_profile.addItems([SPORT_NO_OTHER_COVERAGE, SPORT_PENSION_OR_OTHER])
        self.form.addRow(self.sport_profile_label, self.sport_profile)

        self.previous_gross_label = QLabel("Lordo già percepito nell'anno")
        self.previous_gross = QDoubleSpinBox()
        self.previous_gross.setRange(0, 10_000_000)
        self.previous_gross.setDecimals(2)
        self.previous_gross.setPrefix("€ ")
        self.previous_gross.setToolTip(
            "Lordo già percepito nello stesso anno, usato per soglie e riepilogo cumulativo."
        )
        self.form.addRow(self.previous_gross_label, self.previous_gross)

        self.total_rate_label = QLabel("Aliquota contributiva totale")
        self.total_rate = QDoubleSpinBox()
        self.total_rate.setRange(0, 100)
        self.total_rate.setDecimals(2)
        self.total_rate.setValue(24.0)
        self.total_rate.setSuffix(" %")
        self.form.addRow(self.total_rate_label, self.total_rate)

        self.taxable_base_label = QLabel("Base imponibile contributiva")
        self.taxable_base = QDoubleSpinBox()
        self.taxable_base.setRange(0, 100)
        self.taxable_base.setDecimals(2)
        self.taxable_base.setValue(50.0)
        self.taxable_base.setSuffix(" %")
        self.form.addRow(self.taxable_base_label, self.taxable_base)

        self.tax_rate_label = QLabel("Aliquota fiscale stimata oltre € 15.000")
        self.tax_rate = QDoubleSpinBox()
        self.tax_rate.setRange(0, 100)
        self.tax_rate.setDecimals(2)
        self.tax_rate.setValue(23.0)
        self.tax_rate.setSuffix(" %")
        self.form.addRow(self.tax_rate_label, self.tax_rate)

        layout.addLayout(self.form)

        buttons = QHBoxLayout()
        calc_btn = QPushButton("Calcola")
        calc_btn.clicked.connect(lambda: self.calculate(show_errors=True))
        buttons.addWidget(calc_btn)

        reset_btn = QPushButton("Azzera")
        reset_btn.clicked.connect(self.reset_form)
        buttons.addWidget(reset_btn)

        copy_btn = QPushButton("Copia")
        copy_btn.clicked.connect(self.copy_result)
        buttons.addWidget(copy_btn)

        pdf_btn = QPushButton("Esporta PDF")
        pdf_btn.clicked.connect(self.export_pdf)
        buttons.addWidget(pdf_btn)
        layout.addLayout(buttons)

        result_title = QLabel("Risultato / anteprima")
        result_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(result_title)

        self.primary_result = QLabel("Inserisci i dati")
        self.primary_result.setAlignment(self.primary_result.alignment())
        self.primary_result.setStyleSheet(
            "font-size: 24px; font-weight: bold; padding: 10px; "
            "background: #f3f6f9; color: #083b72;"
        )
        layout.addWidget(self.primary_result)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(230)
        self.details.setFont(QFont("Consolas", 11))
        self.details.setStyleSheet("background: white; border: 1px solid #d6dde5;")
        layout.addWidget(self.details)

        info = QLabel(
            "Il risultato è visibile subito; il PDF serve solo per esportarlo. "
            "Il calcolo fiscale è una simulazione da verificare con il consulente."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #53657a;")
        layout.addWidget(info)

        # Anteprima automatica a ogni modifica.
        self.category.currentTextChanged.connect(self._auto_calculate)
        self.direction.currentTextChanged.connect(self._auto_calculate)
        self.sport_profile.currentTextChanged.connect(self._auto_calculate)
        for widget in (
            self.amount,
            self.previous_gross,
            self.total_rate,
            self.taxable_base,
            self.tax_rate,
        ):
            widget.valueChanged.connect(self._auto_calculate)

    def _update_fields(self, *_args) -> None:
        category = self.category.currentText()
        is_sport = category == CATEGORY_SPORT
        is_pensioner = category == CATEGORY_PENSIONER

        self.sport_profile_label.setVisible(is_sport)
        self.sport_profile.setVisible(is_sport)

        # Richiesta: il lordo già percepito è disponibile sia per pensionato sia per sportivo.
        show_previous = is_sport or is_pensioner
        self.previous_gross_label.setVisible(show_previous)
        self.previous_gross.setVisible(show_previous)
        self.previous_gross.setEnabled(show_previous)

        self.total_rate_label.setVisible(not is_sport)
        self.total_rate.setVisible(not is_sport)
        self.taxable_base_label.setVisible(not is_sport)
        self.taxable_base.setVisible(not is_sport)
        self.tax_rate_label.setVisible(is_sport)
        self.tax_rate.setVisible(is_sport)

        if category == CATEGORY_EMPLOYEE:
            with QSignalBlocker(self.total_rate), QSignalBlocker(self.taxable_base):
                self.total_rate.setValue(24.0)
                self.taxable_base.setValue(50.0)
        elif category == CATEGORY_PENSIONER:
            with QSignalBlocker(self.total_rate), QSignalBlocker(self.taxable_base):
                self.total_rate.setValue(24.0)
                self.taxable_base.setValue(50.0)

        self._auto_calculate()

    def _auto_calculate(self, *_args) -> None:
        self.calculate(show_errors=False)

    def _ordinary_from_gross(self, gross: float) -> Calculation:
        category = self.category.currentText()
        return ordinary_from_gross(
            category=category, gross=gross,
            previous=self.previous_gross.value() if category == CATEGORY_PENSIONER else 0.0,
            total_rate_pct=self.total_rate.value(),
            taxable_base_pct=self.taxable_base.value(),
        )

    def _ordinary_calculation(self, direction: str, amount: float) -> Calculation:
        if direction == "Lordo → Netto":
            return self._ordinary_from_gross(amount)
        return gross_for_target(amount, self._ordinary_from_gross)

    def _sport_from_gross(self, gross: float) -> Calculation:
        return sport_from_gross(
            gross=gross, previous=self.previous_gross.value(),
            no_other_coverage=self.sport_profile.currentText() == SPORT_NO_OTHER_COVERAGE,
            tax_rate_pct=self.tax_rate.value(),
        )

    def _sport_calculation(self, direction: str, amount: float) -> Calculation:
        if direction == "Lordo → Netto":
            return self._sport_from_gross(amount)
        return gross_for_target(amount, self._sport_from_gross)

    def calculate(self, show_errors: bool = True) -> None:
        try:
            amount = self.amount.value()
            direction = self.direction.currentText()
            if self.category.currentText() == CATEGORY_SPORT:
                result = self._sport_calculation(direction, amount)
            else:
                result = self._ordinary_calculation(direction, amount)
            self.last_result = result
            self._show_result(result)
        except Exception as exc:
            self.last_result = None
            self.primary_result.setText("Calcolo non disponibile")
            self.details.setPlainText(str(exc))
            if show_errors:
                QMessageBox.critical(self, "Errore calcolo", str(exc))

    def _show_result(self, result: Calculation) -> None:
        primary = result.gross if result.direction == "Netto → Lordo" else result.net
        label = "Lordo da riconoscere" if result.direction == "Netto → Lordo" else "Netto risultante"
        self.primary_result.setText(f"{label}: € {primary:,.2f}")

        lines = [
            f"Categoria:                  {result.category}",
            f"Direzione:                  {result.direction}",
        ]
        if result.category in {CATEGORY_PENSIONER, CATEGORY_SPORT}:
            lines.extend([
                f"Lordo già percepito:        € {result.previous_gross:,.2f}",
                f"Lordo cumulato:             € {result.cumulative_gross:,.2f}",
                f"Franchigia residua:         € {result.franchise_remaining:,.2f}",
                f"Quota soggetta a contributi: € {result.contributory_part:,.2f}",
            ])
        if result.category == CATEGORY_SPORT:
            lines.append(f"Profilo previdenziale:      {self.sport_profile.currentText()}")
        lines.extend([
            "",
            f"Lordo:                      € {result.gross:,.2f}",
            f"Contributo previdenziale:   € {result.previdential:,.2f}",
            f"Altri contributi:           € {result.other_contrib:,.2f}",
            f"IRPEF/addizionali stimate:  € {result.taxes:,.2f}",
            "-----------------------------------------------",
            f"Netto:                      € {result.net:,.2f}",
            "",
            f"Nota: {result.note}",
        ])
        self.details.setPlainText("\n".join(lines))

    def reset_form(self) -> None:
        with QSignalBlocker(self.amount), QSignalBlocker(self.previous_gross):
            self.amount.setValue(0.0)
            self.previous_gross.setValue(0.0)
        self.calculate(show_errors=False)

    def copy_result(self) -> None:
        if self.last_result is None:
            QMessageBox.information(self, "Copia", "Nessun risultato disponibile.")
            return
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(
            self.primary_result.text() + "\n\n" + self.details.toPlainText()
        )
        QMessageBox.information(self, "Copia", "Risultato copiato negli appunti.")

    def export_pdf(self) -> None:
        # L'anteprima è sempre aggiornata; il PDF esporta esattamente il risultato visibile.
        self.calculate(show_errors=True)
        if self.last_result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva calcolo PDF", "calcolo_compensi.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            self._write_pdf(Path(path))
            add_history(
                module="Convertitore compensi",
                source="Calcolo manuale",
                output=path,
                rows=1,
                details=self.last_result.category,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Errore PDF", str(exc))
            return
        QMessageBox.information(self, "PDF creato", path)

    def _write_pdf(self, path: Path) -> None:
        pdf = canvas.Canvas(str(path), pagesize=A4)
        _, height = A4
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(50, height - 60, "SPES Configuratore Contabile - Calcolo lordo/netto")
        pdf.setFont("Helvetica", 10)
        y = height - 100
        lines = [self.primary_result.text(), ""] + self.details.toPlainText().splitlines()
        for line in lines:
            safe_line = line.replace("€", "EUR")
            pdf.drawString(50, y, safe_line)
            y -= 18
            if y < 60:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = height - 60
        pdf.save()
