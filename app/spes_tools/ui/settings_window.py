from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from spes_tools.services.backup import create_backup, restore_backup
from spes_tools.services.storage import data_dir
from spes_tools.services.updater import check_for_update, download_installer, open_release_page
from spes_tools.version import APP_VERSION


class SettingsWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SPES Configuratore Contabile - Impostazioni")
        self.resize(680, 430)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Impostazioni e manutenzione")
        title.setStyleSheet("font-size: 25px; font-weight: bold; color: #073b84;")
        layout.addWidget(title)

        path_label = QLabel(f"Dati utente: {data_dir()}")
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: #53657a;")
        layout.addWidget(path_label)

        backup_title = QLabel("Backup configurazione e storico")
        backup_title.setStyleSheet("font-size: 17px; font-weight: 700; margin-top: 15px;")
        layout.addWidget(backup_title)

        backup_buttons = QHBoxLayout()
        export_button = QPushButton("Esporta backup")
        export_button.clicked.connect(self.export_backup)
        backup_buttons.addWidget(export_button)
        import_button = QPushButton("Ripristina backup")
        import_button.clicked.connect(self.import_backup)
        backup_buttons.addWidget(import_button)
        open_button = QPushButton("Apri cartella dati")
        open_button.clicked.connect(self.open_data_folder)
        backup_buttons.addWidget(open_button)
        layout.addLayout(backup_buttons)

        update_title = QLabel("Aggiornamenti")
        update_title.setStyleSheet("font-size: 17px; font-weight: 700; margin-top: 20px;")
        layout.addWidget(update_title)
        self.update_status = QLabel(f"Versione installata: {APP_VERSION}")
        layout.addWidget(self.update_status)
        update_button = QPushButton("Controlla aggiornamenti")
        update_button.clicked.connect(self.check_updates)
        layout.addWidget(update_button)
        layout.addStretch()

        note = QLabel(
            "Prima di ripristinare un backup chiudi le altre finestre dell'app. "
            "Gli aggiornamenti sono distribuiti tramite le release GitHub del progetto."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #53657a;")
        layout.addWidget(note)

    def export_backup(self) -> None:
        default_name = f"SPES_backup_{datetime.now():%Y%m%d_%H%M}.zip"
        path, _ = QFileDialog.getSaveFileName(self, "Esporta backup", default_name, "Archivio ZIP (*.zip)")
        if not path:
            return
        try:
            output = create_backup(path)
        except Exception as exc:
            QMessageBox.critical(self, "Errore backup", str(exc))
            return
        QMessageBox.information(self, "Backup completato", f"Backup creato:\n{output}")

    def import_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Ripristina backup", "", "Archivio ZIP (*.zip)")
        if not path:
            return
        answer = QMessageBox.question(
            self,
            "Conferma ripristino",
            "Il ripristino sostituirà configurazione ABI, regole e storico presenti. Continuare?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            restored = restore_backup(path)
        except Exception as exc:
            QMessageBox.critical(self, "Errore ripristino", str(exc))
            return
        QMessageBox.information(
            self,
            "Ripristino completato",
            "File ripristinati:\n" + "\n".join(restored) + "\n\nRiavvia l'applicazione.",
        )

    def open_data_folder(self) -> None:
        path = str(data_dir())
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])

    def check_updates(self) -> None:
        self.update_status.setText("Controllo aggiornamenti in corso...")
        try:
            release = check_for_update()
        except Exception as exc:
            self.update_status.setText("Controllo non riuscito")
            QMessageBox.warning(self, "Aggiornamenti", f"Impossibile controllare gli aggiornamenti:\n{exc}")
            return
        if release is None:
            self.update_status.setText(f"Versione {APP_VERSION}: aggiornata")
            QMessageBox.information(self, "Aggiornamenti", "Stai già usando la versione più recente.")
            return

        self.update_status.setText(f"Disponibile versione {release.version}")
        if not release.installer_url:
            answer = QMessageBox.question(
                self,
                "Aggiornamento disponibile",
                f"È disponibile la versione {release.version}. Aprire la pagina della release?",
            )
            if answer == QMessageBox.Yes:
                open_release_page(release)
            return

        answer = QMessageBox.question(
            self,
            "Aggiornamento disponibile",
            f"È disponibile la versione {release.version}. Scaricare e avviare l'installer?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            installer = download_installer(release, Path.home() / "Downloads")
            subprocess.Popen([str(installer)], shell=True)
        except Exception as exc:
            QMessageBox.critical(self, "Errore aggiornamento", str(exc))
            return
        QMessageBox.information(
            self,
            "Installer avviato",
            "Chiudi SPES Configuratore Contabile e completa l'installazione guidata.",
        )
