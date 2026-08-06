from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from spes_tools.services.auth import SessionUser, UserStore
from spes_tools.version import APP_NAME, APP_VERSION


class ChangePasswordDialog(QDialog):
    def __init__(self, username: str, store: UserStore, parent=None) -> None:
        super().__init__(parent)
        self.username = username
        self.store = store
        self.setWindowTitle("Cambio password obbligatorio")
        self.setModal(True)
        layout = QVBoxLayout(self)
        info = QLabel("La password iniziale deve essere sostituita prima di continuare.")
        info.setWordWrap(True)
        layout.addWidget(info)
        form = QFormLayout()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.Password)
        form.addRow("Nuova password:", self.password)
        form.addRow("Conferma password:", self.confirm)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self) -> None:
        password = self.password.text()
        if password != self.confirm.text():
            QMessageBox.warning(self, "Password", "Le due password non coincidono.")
            return
        try:
            self.store.set_password(self.username, password, must_change=False)
        except ValueError as exc:
            QMessageBox.warning(self, "Password", str(exc))
            return
        self.accept()


class LoginDialog(QDialog):
    def __init__(self, store: UserStore | None = None) -> None:
        super().__init__()
        self.store = store or UserStore()
        self.session_user: SessionUser | None = None
        self.setWindowTitle(f"Accesso - {APP_NAME}")
        self.setFixedWidth(430)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel(APP_NAME)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 23px; font-weight: 800; color: #073b84;")
        layout.addWidget(title)
        version = QLabel(f"Versione {APP_VERSION}")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #53657a;")
        layout.addWidget(version)

        form = QFormLayout()
        self.username = QComboBox()
        for user in self.store.list_users():
            if bool(user.get("active", True)):
                self.username.addItem(str(user.get("display_name") or user.get("username")), str(user.get("username")))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.returnPressed.connect(self.login)
        form.addRow("Utente:", self.username)
        form.addRow("Password:", self.password)
        layout.addLayout(form)

        self.error = QLabel("")
        self.error.setStyleSheet("color: #b00020;")
        layout.addWidget(self.error)
        login = QPushButton("Accedi")
        login.setDefault(True)
        login.clicked.connect(self.login)
        layout.addWidget(login)
        note = QLabel("Al primo accesso usa la password iniziale fornita e cambiala quando richiesto.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #53657a; font-size: 11px;")
        layout.addWidget(note)

    def login(self) -> None:
        username = str(self.username.currentData() or "")
        session, must_change = self.store.authenticate(username, self.password.text())
        if session is None:
            self.error.setText("Utente o password non validi.")
            self.password.selectAll()
            self.password.setFocus()
            return
        if must_change:
            change = ChangePasswordDialog(username, self.store, self)
            if change.exec() != QDialog.Accepted:
                return
            session, _ = self.store.authenticate(username, change.password.text())
            if session is None:
                self.error.setText("Impossibile completare il cambio password.")
                return
        self.session_user = session
        self.accept()
