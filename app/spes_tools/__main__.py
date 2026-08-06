import sys
from datetime import date

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QSplashScreen

from spes_tools.resources import resource_path
from spes_tools.ui.main_window import MainWindow
from spes_tools.ui.login_window import LoginDialog
from spes_tools.version import APP_NAME, ORGANIZATION_NAME
from spes_tools.services.fgi_results import current_season, update_fgi_results
from spes_tools.services.fgi_scheduler import (
    ensure_weekly_fgi_calendar_task,
    ensure_weekly_fgi_task,
)
from spes_tools.services.fgi_calendar import update_fgi_calendar


def main() -> int:
    if "--update-fgi-calendar" in sys.argv:
        try:
            update_fgi_calendar()
        except Exception as exc:
            print(f"Aggiornamento calendario FGI non riuscito: {exc}", file=sys.stderr)
            return 1
        return 0

    if "--update-fgi" in sys.argv:
        start, end, _ = current_season(date.today())
        try:
            update_fgi_results(start, end)
        except Exception as exc:
            print(f"Aggiornamento FGI non riuscito: {exc}", file=sys.stderr)
            return 1
        return 0

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
        pixmap = QPixmap(str(logo_path)).scaled(260, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        splash = QSplashScreen(pixmap)
        splash.showMessage(APP_NAME, Qt.AlignBottom | Qt.AlignHCenter, Qt.white)
        splash.show()
        app.processEvents()

    ensure_weekly_fgi_task()
    ensure_weekly_fgi_calendar_task()

    if splash is not None:
        splash.close()

    login = LoginDialog()
    if login.exec() != QDialog.Accepted or login.session_user is None:
        return 0

    window = MainWindow(login.session_user)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
