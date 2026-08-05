from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from spes_tools.services.storage import (
    load_abi_config, reset_abi_config, save_abi_config,
    load_rules_config, reset_rules_config, save_rules_config,
)


class AbiWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SPES Configuratore Contabile - Causali ABI")
        self.resize(760, 560)
        self.config = load_abi_config()
        self.tables: dict[str, QTableWidget] = {}
        self.rules = load_rules_config()
        self.keyword_input = QLineEdit()
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
        for bank in ("NEXI", "BCC", "VOLKSBANK", "CASSA"):
            table = QTableWidget(0, 2)
            table.setHorizontalHeaderLabels(["Tipo movimento", "Causale ABI"])
            table.horizontalHeader().setStretchLastSection(True)
            self.tables[bank] = table
            self.tabs.addTab(table, bank)

        rules_tab = QWidget()
        rules_form = QFormLayout(rules_tab)
        self.keyword_input.setText(", ".join(self.rules.get("VOLKSBANK", {}).get("quota_corso_keywords", [])))
        self.keyword_input.setToolTip("Parole separate da virgola. Valide per bonifici Volksbank in entrata.")
        rules_form.addRow("Volksbank causale 99 - parole chiave", self.keyword_input)
        rules_form.addRow(QLabel("Esempi: quota, mensile, mensilità, corso"))
        self.tabs.addTab(rules_tab, "REGOLE")

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
        keywords = [x.strip() for x in self.keyword_input.text().split(",") if x.strip()]
        self.rules.setdefault("VOLKSBANK", {})["quota_corso_keywords"] = keywords
        save_rules_config(self.rules)
        QMessageBox.information(self, "Salvataggio completato", "Le causali ABI sono state salvate.")

    def reset(self) -> None:
        answer = QMessageBox.question(self, "Conferma", "Ripristinare tutte le causali ABI iniziali?")
        if answer != QMessageBox.Yes:
            return
        self.config = reset_abi_config()
        self.rules = reset_rules_config()
        self.keyword_input.setText(", ".join(self.rules["VOLKSBANK"]["quota_corso_keywords"]))
        self._fill_tables()
        QMessageBox.information(self, "Ripristino completato", "Valori iniziali ripristinati.")
