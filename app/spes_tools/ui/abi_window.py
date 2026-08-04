from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from spes_tools.services.storage import load_abi_config, reset_abi_config, save_abi_config


class AbiWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SPES Tools - Causali ABI")
        self.resize(760, 560)
        self.config = load_abi_config()
        self.tables: dict[str, QTableWidget] = {}
        self._build_ui()
        self._fill_tables()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Causali ABI")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #083b72;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Modifica i codici usati dai parser. Le modifiche sono applicate alle importazioni successive."))

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        for bank in ("NEXI", "BCC", "VOLKSBANK"):
            table = QTableWidget(0, 2)
            table.setHorizontalHeaderLabels(["Tipo movimento", "Causale ABI"])
            table.horizontalHeader().setStretchLastSection(True)
            self.tables[bank] = table
            self.tabs.addTab(table, bank)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Salva")
        save_btn.clicked.connect(self.save)
        buttons.addWidget(save_btn)
        reset_btn = QPushButton("Ripristina valori iniziali")
        reset_btn.clicked.connect(self.reset)
        buttons.addWidget(reset_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

    def _fill_tables(self) -> None:
        for bank, table in self.tables.items():
            values = self.config.get(bank, {})
            table.setRowCount(len(values))
            for row, (key, code) in enumerate(values.items()):
                key_item = QTableWidgetItem(key)
                key_item.setFlags(key_item.flags() & ~key_item.flags().ItemIsEditable)
                table.setItem(row, 0, key_item)
                table.setItem(row, 1, QTableWidgetItem(code))
            table.resizeColumnsToContents()

    def save(self) -> None:
        for bank, table in self.tables.items():
            updated: dict[str, str] = {}
            for row in range(table.rowCount()):
                key = table.item(row, 0).text().strip()
                value = table.item(row, 1).text().strip()
                if not value:
                    QMessageBox.warning(self, "Valore mancante", f"Inserire un codice per {bank} / {key}.")
                    return
                updated[key] = value
            self.config[bank] = updated
        save_abi_config(self.config)
        QMessageBox.information(self, "Salvataggio completato", "Le causali ABI sono state salvate.")

    def reset(self) -> None:
        answer = QMessageBox.question(self, "Conferma", "Ripristinare tutte le causali ABI iniziali?")
        if answer != QMessageBox.Yes:
            return
        self.config = reset_abi_config()
        self._fill_tables()
        QMessageBox.information(self, "Ripristino completato", "Valori iniziali ripristinati.")
