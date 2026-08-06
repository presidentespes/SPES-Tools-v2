from __future__ import annotations

import os
import subprocess
import sys
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
from spes_tools.services.auth import SessionUser
from spes_tools.ui.user_management_window import UserManagementWindow
from spes_tools.services.storage import (
    archive_root,
    data_dir,
    get_export_directory,
    set_export_directory,
)
from spes_tools.services.updater import check_for_update, download_installer, open_release_page
from spes_tools.version import APP_VERSION


class SettingsWindow(QWidget):
    def __init__(self, current_user: SessionUser) -> None:
        super().__init__()
        self.current_user = current_user
        self.user_management_window: UserManagementWindow | None = None
        self.setWindowTitle("Consolle SPES Ginnastica Mestre - Impostazioni")
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
        backup_title.setVisible(self.current_user.can("backup"))
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
        backup_buttons.setEnabled(self.current_user.can("backup"))
        if self.current_user.can("backup"):
            layout.addLayout(backup_buttons)

        csv_title = QLabel("CSV TeamSystem")
        csv_title.setStyleSheet("font-size: 17px; font-weight: 700; margin-top: 20px;")
        layout.addWidget(csv_title)

        self.csv_path_label = QLabel()
        self.csv_path_label.setWordWrap(True)
        self.csv_path_label.setStyleSheet("color: #53657a;")
        layout.addWidget(self.csv_path_label)

        csv_buttons = QHBoxLayout()
        open_csv_button = QPushButton("Apri cartella CSV")
        open_csv_button.clicked.connect(self.open_csv_folder)
        csv_buttons.addWidget(open_csv_button)
        open_archive_button = QPushButton("Apri archivio operazioni")
        open_archive_button.clicked.connect(lambda: self._open_folder(archive_root()))
        csv_buttons.addWidget(open_archive_button)
        change_csv_button = QPushButton("Cambia cartella")
        change_csv_button.clicked.connect(self.change_csv_folder)
        csv_buttons.addWidget(change_csv_button)
        csv_buttons.addStretch()
        layout.addLayout(csv_buttons)
        self._refresh_csv_path()

        update_title = QLabel("Aggiornamenti")
        update_title.setStyleSheet("font-size: 17px; font-weight: 700; margin-top: 20px;")
        layout.addWidget(update_title)
        self.update_status = QLabel(f"Versione installata: {APP_VERSION}")
        layout.addWidget(self.update_status)
        update_button = QPushButton("Controlla aggiornamenti")
        update_button.clicked.connect(self.check_updates)
        update_button.setVisible(self.current_user.can("updates"))
        layout.addWidget(update_button)

        if self.current_user.can("users_manage"):
            users_title = QLabel("Utenti e permessi")
            users_title.setStyleSheet("font-size: 17px; font-weight: 700; margin-top: 20px;")
            layout.addWidget(users_title)
            users_button = QPushButton("Gestisci utenti e permessi")
            users_button.clicked.connect(self.open_user_management)
            layout.addWidget(users_button)
        layout.addStretch()

        note = QLabel(
            "Prima di ripristinare un backup chiudi le altre finestre dell'app. "
            "Gli aggiornamenti sono distribuiti tramite le release GitHub del progetto."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #53657a;")
        layout.addWidget(note)

    def open_user_management(self) -> None:
        if not self.current_user.can("users_manage"):
            QMessageBox.warning(self, "Permessi", "Non hai il permesso di gestire gli utenti.")
            return
        if self.user_management_window is None:
            self.user_management_window = UserManagementWindow()
        self.user_management_window.refresh()
        self.user_management_window.show()
        self.user_management_window.raise_()
        self.user_management_window.activateWindow()

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

    def _refresh_csv_path(self) -> None:
        directory = get_export_directory()
        self.csv_path_label.setText(
            f"Cartella corrente: {directory}" if directory else "Cartella corrente: non impostata"
        )

    def change_csv_folder(self) -> None:
        initial = get_export_directory() or str(Path.home() / "Documents")
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleziona la cartella dei CSV TeamSystem",
            initial,
        )
        if not directory:
            return
        set_export_directory(directory)
        self._refresh_csv_path()

    def open_csv_folder(self) -> None:
        directory = get_export_directory()
        if not directory or not Path(directory).is_dir():
            self.change_csv_folder()
            directory = get_export_directory()
        if not directory or not Path(directory).is_dir():
            return
        self._open_folder(Path(directory))

    @staticmethod
    def _open_folder(path: Path) -> None:
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            QMessageBox.critical(None, "Errore apertura cartella", str(exc))

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
