from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from spes_tools.services.auth import DEFAULT_PASSWORD, PERMISSIONS, ROLE_DEFAULTS, UserStore


class UserManagementWindow(QWidget):
    def __init__(self, store: UserStore | None = None) -> None:
        super().__init__()
        self.store = store or UserStore()
        self.setWindowTitle("Gestione utenti e permessi")
        self.resize(920, 650)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        title = QLabel("Gestione utenti e permessi")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #073b84;")
        root.addWidget(title)
        subtitle = QLabel("Il profilo assegna i permessi iniziali; l'amministratore può personalizzarli per ogni utente.")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        splitter = QSplitter()
        root.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.users = QListWidget()
        self.users.currentItemChanged.connect(self.load_current)
        left_layout.addWidget(self.users, 1)
        new_button = QPushButton("Nuovo utente")
        new_button.clicked.connect(self.new_user)
        left_layout.addWidget(new_button)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.username = QLineEdit()
        self.username.setReadOnly(True)
        self.display_name = QLineEdit()
        self.role = QComboBox()
        self.role.addItems(["admin", "segreteria", "consiglieri"])
        self.role.currentTextChanged.connect(self.role_changed)
        self.active = QCheckBox("Account attivo")
        form.addRow("Nome utente:", self.username)
        form.addRow("Nome visualizzato:", self.display_name)
        form.addRow("Profilo:", self.role)
        form.addRow("Stato:", self.active)
        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("Permessi personalizzati"))
        self.permissions = QListWidget()
        for key, label in PERMISSIONS.items():
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, key)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.permissions.addItem(item)
        right_layout.addWidget(self.permissions, 1)

        buttons = QHBoxLayout()
        save = QPushButton("Salva")
        save.clicked.connect(self.save_current)
        buttons.addWidget(save)
        reset_role = QPushButton("Ripristina permessi profilo")
        reset_role.clicked.connect(self.apply_role_defaults)
        buttons.addWidget(reset_role)
        reset_password = QPushButton("Reimposta password")
        reset_password.clicked.connect(self.reset_password)
        buttons.addWidget(reset_password)
        delete = QPushButton("Elimina")
        delete.clicked.connect(self.delete_current)
        buttons.addWidget(delete)
        right_layout.addLayout(buttons)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 2)

    def refresh(self, select_username: str | None = None) -> None:
        self.users.clear()
        target = None
        for user in self.store.list_users():
            username = str(user.get("username", ""))
            item = QListWidgetItem(f"{user.get('display_name', username)}  [{user.get('role', '')}]")
            item.setData(Qt.UserRole, username)
            self.users.addItem(item)
            if username == select_username:
                target = item
        if target:
            self.users.setCurrentItem(target)
        elif self.users.count():
            self.users.setCurrentRow(0)

    def current_username(self) -> str:
        item = self.users.currentItem()
        return str(item.data(Qt.UserRole)) if item else ""

    def load_current(self, current: QListWidgetItem | None, previous=None) -> None:
        if current is None:
            return
        user = self.store.get_user(str(current.data(Qt.UserRole)))
        if not user:
            return
        self.username.setText(str(user.get("username", "")))
        self.display_name.setText(str(user.get("display_name", "")))
        self.role.setCurrentText(str(user.get("role", "consiglieri")))
        self.active.setChecked(bool(user.get("active", True)))
        selected = set(str(value) for value in user.get("permissions", []))
        for index in range(self.permissions.count()):
            item = self.permissions.item(index)
            item.setCheckState(Qt.Checked if str(item.data(Qt.UserRole)) in selected else Qt.Unchecked)

    def selected_permissions(self) -> set[str]:
        return {
            str(self.permissions.item(index).data(Qt.UserRole))
            for index in range(self.permissions.count())
            if self.permissions.item(index).checkState() == Qt.Checked
        }

    def role_changed(self, role: str) -> None:
        # Non sovrascrive automaticamente le personalizzazioni: usare il pulsante dedicato.
        pass

    def apply_role_defaults(self) -> None:
        defaults = ROLE_DEFAULTS[self.role.currentText()]
        for index in range(self.permissions.count()):
            item = self.permissions.item(index)
            item.setCheckState(Qt.Checked if str(item.data(Qt.UserRole)) in defaults else Qt.Unchecked)

    def save_current(self) -> None:
        username = self.current_username()
        if not username:
            return
        try:
            self.store.save_user(
                username=username,
                display_name=self.display_name.text(),
                role=self.role.currentText(),
                permissions=self.selected_permissions(),
                active=self.active.isChecked(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Utente", str(exc))
            return
        self.refresh(username)
        QMessageBox.information(self, "Utente", "Permessi salvati.")

    def new_user(self) -> None:
        username, ok = QInputDialog.getText(self, "Nuovo utente", "Nome utente:")
        if not ok or not username.strip():
            return
        display, ok = QInputDialog.getText(self, "Nuovo utente", "Nome visualizzato:", text=username.strip())
        if not ok:
            return
        role, ok = QInputDialog.getItem(self, "Nuovo utente", "Profilo:", ["admin", "segreteria", "consiglieri"], 2, False)
        if not ok:
            return
        try:
            self.store.create_user(username, display, role)
        except ValueError as exc:
            QMessageBox.warning(self, "Nuovo utente", str(exc))
            return
        self.refresh(username.strip().lower())
        QMessageBox.information(self, "Nuovo utente", f"Utente creato. Password iniziale: {DEFAULT_PASSWORD}")

    def reset_password(self) -> None:
        username = self.current_username()
        if not username:
            return
        self.store.set_password(username, DEFAULT_PASSWORD, must_change=True)
        QMessageBox.information(self, "Password", f"Password reimpostata a '{DEFAULT_PASSWORD}'. Sarà richiesto il cambio al prossimo accesso.")

    def delete_current(self) -> None:
        username = self.current_username()
        if not username:
            return
        if QMessageBox.question(self, "Elimina utente", f"Eliminare l'utente {username}?") != QMessageBox.Yes:
            return
        try:
            self.store.delete_user(username)
        except ValueError as exc:
            QMessageBox.warning(self, "Elimina utente", str(exc))
            return
        self.refresh()
