import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from spes_tools.resources import resource_path
from spes_tools.ui.main_window import MainWindow


APP_NAME = "SPES Configuratore Contabile"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("ASD SPES Mestre Ginnastica")

    icon_path = resource_path("assets/logo_spes.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
