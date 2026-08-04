from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from spes_tools.services.storage import add_history


SPORT_PROFILE = "Collaboratore sportivo"


class CafWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SPES Tools - CAF Tools")
        self.resize(650, 600)
        self.last_result: dict[str, float | str] | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("CAF Tools - Calcolo lordo/netto")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #083b72;")
        layout.addWidget(title)
        layout.addWidget(QLabel(
            "Calcolo indicativo configurabile. Non sostituisce un cedolino o un calcolo fiscale professionale."
        ))

        self.form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItems(["Da lordo a netto", "Da netto a lordo"])
        self.form.addRow("Tipo calcolo", self.mode)

        self.profile = QComboBox()
        self.profile.addItems(["Dipendente", "Pensionato", SPORT_PROFILE])
        self.profile.currentTextChanged.connect(self._profile_changed)
        self.form.addRow("Profilo", self.profile)

        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 10_000_000)
        self.amount.setDecimals(2)
        self.amount.setSuffix(" EUR")
        self.form.addRow("Importo", self.amount)

        self.previous_gross_label = QLabel("Lordo gia percepito")
        self.previous_gross = QDoubleSpinBox()
        self.previous_gross.setRange(0, 10_000_000)
        self.previous_gross.setDecimals(2)
        self.previous_gross.setSuffix(" EUR")
        self.previous_gross.setToolTip("Lordo sportivo gia percepito nell'anno prima di questo compenso")
        self.form.addRow(self.previous_gross_label, self.previous_gross)

        self.tax_rate = QDoubleSpinBox()
        self.tax_rate.setRange(0, 100)
        self.tax_rate.setDecimals(2)
        self.tax_rate.setValue(23.0)
        self.tax_rate.setSuffix(" %")
        self.form.addRow("Aliquota imposte", self.tax_rate)

        self.contrib_rate = QDoubleSpinBox()
        self.contrib_rate.setRange(0, 100)
        self.contrib_rate.setDecimals(2)
        self.contrib_rate.setValue(9.19)
        self.contrib_rate.setSuffix(" %")
        self.form.addRow("Contributi", self.contrib_rate)

        self.deductions = QDoubleSpinBox()
        self.deductions.setRange(0, 10_000_000)
        self.deductions.setDecimals(2)
        self.deductions.setSuffix(" EUR")
        self.form.addRow("Detrazioni/abbattimenti", self.deductions)

        self.months = QSpinBox()
        self.months.setRange(1, 14)
        self.months.setValue(12)
        self.form.addRow("Mensilita", self.months)
        layout.addLayout(self.form)

        buttons = QHBoxLayout()
        calc_btn = QPushButton("Calcola")
        calc_btn.clicked.connect(self.calculate)
        buttons.addWidget(calc_btn)
        pdf_btn = QPushButton("Esporta PDF")
        pdf_btn.clicked.connect(self.export_pdf)
        buttons.addWidget(pdf_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.result = QLabel("Inserisci i dati e premi Calcola.")
        self.result.setWordWrap(True)
        self.result.setStyleSheet(
            "font-size: 16px; padding: 12px; background: white; border: 1px solid #d6dde5;"
        )
        layout.addWidget(self.result)

        # Apply initial visibility and defaults after every widget exists.
        self._profile_changed(self.profile.currentText())

    def _profile_changed(self, profile: str) -> None:
        defaults = {
            "Dipendente": (23.0, 9.19),
            "Pensionato": (23.0, 0.0),
            SPORT_PROFILE: (23.0, 24.0),
        }
        tax, contrib = defaults.get(profile, (23.0, 0.0))
        self.tax_rate.setValue(tax)
        self.contrib_rate.setValue(contrib)
        is_sport = profile == SPORT_PROFILE
        self.previous_gross_label.setVisible(is_sport)
        self.previous_gross.setVisible(is_sport)
        self.previous_gross.setEnabled(is_sport)

    def calculate(self) -> None:
        amount = self.amount.value()
        tax = self.tax_rate.value() / 100.0
        contrib = self.contrib_rate.value() / 100.0
        deduction = self.deductions.value()
        total_rate = tax + contrib

        if self.mode.currentIndex() == 0:
            gross = amount
            contributions = gross * contrib
            taxes = max(0.0, gross * tax - deduction)
            net = max(0.0, gross - contributions - taxes)
        else:
            net = amount
            if total_rate >= 0.999:
                QMessageBox.warning(
                    self,
                    "Aliquote non valide",
                    "La somma delle aliquote deve essere inferiore al 100%.",
                )
                return
            gross = max(0.0, (net - deduction) / (1.0 - total_rate))
            contributions = gross * contrib
            taxes = max(0.0, gross * tax - deduction)

        previous_gross = self.previous_gross.value() if self.profile.currentText() == SPORT_PROFILE else 0.0
        cumulative_gross = previous_gross + gross
        monthly = net / self.months.value()
        self.last_result = {
            "profilo": self.profile.currentText(),
            "modalita": self.mode.currentText(),
            "lordo_gia_percepito": previous_gross,
            "lordo": gross,
            "lordo_cumulato": cumulative_gross,
            "contributi": contributions,
            "imposte": taxes,
            "netto": net,
            "netto_mensile": monthly,
            "mensilita": float(self.months.value()),
        }

        sport_lines = ""
        if self.profile.currentText() == SPORT_PROFILE:
            sport_lines = (
                f"Lordo gia percepito: EUR {previous_gross:,.2f}\n"
                f"Lordo cumulato: EUR {cumulative_gross:,.2f}\n"
            )
        self.result.setText(
            sport_lines
            + f"Lordo del calcolo: EUR {gross:,.2f}\n"
            + f"Contributi: EUR {contributions:,.2f}\n"
            + f"Imposte stimate: EUR {taxes:,.2f}\n"
            + f"Netto: EUR {net:,.2f}\n"
            + f"Netto medio per mensilita: EUR {monthly:,.2f}"
        )

    def export_pdf(self) -> None:
        if self.last_result is None:
            self.calculate()
        if self.last_result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva calcolo PDF", "calcolo_caf.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            self._write_pdf(Path(path))
            add_history(
                module="CAF Tools",
                source="Calcolo manuale",
                output=path,
                rows=1,
                details=str(self.last_result.get("profilo", "")),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Errore PDF", str(exc))
            return
        QMessageBox.information(self, "PDF creato", path)

    def _write_pdf(self, path: Path) -> None:
        result = self.last_result or {}
        pdf = canvas.Canvas(str(path), pagesize=A4)
        _, height = A4
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(50, height - 60, "SPES Tools - Calcolo lordo/netto")
        pdf.setFont("Helvetica", 11)
        y = height - 100
        lines = [
            f"Profilo: {result.get('profilo', '')}",
            f"Modalita: {result.get('modalita', '')}",
        ]
        if result.get("profilo") == SPORT_PROFILE:
            lines.extend([
                f"Lordo gia percepito: EUR {float(result.get('lordo_gia_percepito', 0)):,.2f}",
                f"Lordo cumulato: EUR {float(result.get('lordo_cumulato', 0)):,.2f}",
            ])
        lines.extend([
            f"Lordo del calcolo: EUR {float(result.get('lordo', 0)):,.2f}",
            f"Contributi: EUR {float(result.get('contributi', 0)):,.2f}",
            f"Imposte stimate: EUR {float(result.get('imposte', 0)):,.2f}",
            f"Netto: EUR {float(result.get('netto', 0)):,.2f}",
            f"Netto medio mensile: EUR {float(result.get('netto_mensile', 0)):,.2f}",
            "",
            "Calcolo indicativo. Verificare i risultati con un professionista abilitato.",
        ])
        for line in lines:
            pdf.drawString(50, y, line)
            y -= 22
        pdf.save()
