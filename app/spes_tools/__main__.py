import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from spes_tools.resources import resource_path
from spes_tools.ui.main_window import MainWindow
from spes_tools.version import APP_NAME, ORGANIZATION_NAME


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(ORGANIZATION_NAME)

    icon_path = resource_path("assets/logo_spes.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    splash: QSplashScreen | None = None
    logo_path = resource_path("assets/logo_spes.png")
    if logo_path.exists():
        pixmap = QPixmap(str(logo_path)).scaled(
            260, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        splash = QSplashScreen(pixmap)
        splash.showMessage(
            APP_NAME,
            Qt.AlignBottom | Qt.AlignHCenter,
            Qt.white,
        )
        splash.show()
        app.processEvents()

    window = MainWindow()
    if splash is not None:
        QTimer.singleShot(900, lambda: (splash.finish(window), window.show()))
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
