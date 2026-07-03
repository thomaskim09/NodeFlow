import sys
import logging
import ctypes
from PySide6.QtWidgets import QApplication, QMainWindow, QSplashScreen
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QColor
import os

from ui.startup_view import StartupView

from managers.theme_manager import apply_theme
import database
from utils.common import get_resource_path
from services.logging_service import configure_logging
from utils.app_paths import get_database_path, get_user_data_dir

LOGGER = logging.getLogger(__name__)

WINDOWS_APP_ID = "thomaskim09.NodeFlow"


def get_app_icon_path() -> str | None:
    icon_name = "icon.ico" if sys.platform == "win32" else "icon.png"
    icon_path = get_resource_path(icon_name)
    if os.path.exists(icon_path):
        return icon_path
    fallback_path = get_resource_path("icon.png")
    if os.path.exists(fallback_path):
        return fallback_path
    return None


def configure_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except (AttributeError, OSError):
        LOGGER.debug("Unable to set Windows AppUserModelID", exc_info=True)

class MainWindow(QMainWindow):
    """
    The main window of the application. It acts as a controller to show the startup view only.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NodeFlow")
        icon_path = get_app_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        self.show_startup_view()

    def center_window(self):
        """Helper function to center the main window on the screen."""
        try:
            center_point = self.screen().availableGeometry().center()
            frame_geometry = self.frameGeometry()
            frame_geometry.moveCenter(center_point)
            self.move(frame_geometry.topLeft())
        except AttributeError:
            pass

    def show_startup_view(self):
        """Displays the project selection screen."""
        self.setWindowTitle("NodeFlow - Select Project")
        self.setMinimumSize(QSize(500, 400))
        self.resize(500, 400)
        startup_view = StartupView()
        self.setCentralWidget(startup_view)
        self.center_window()


def main() -> int:
    log_path = configure_logging()
    LOGGER.info("Starting NodeFlow")
    LOGGER.info("User data directory: %s", get_user_data_dir())
    LOGGER.info("Database path: %s", get_database_path())
    LOGGER.info("Log path: %s", log_path)
    configure_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName("NodeFlow")
    app.setApplicationDisplayName("NodeFlow")
    app_icon_path = get_app_icon_path()
    if app_icon_path:
        app.setWindowIcon(QIcon(app_icon_path))
    splash_path = get_resource_path("splashscreen.png")
    pixmap = QPixmap(splash_path) if os.path.exists(splash_path) else QPixmap()
    splash = QSplashScreen(pixmap)
    splash.show()
    splash.showMessage(
        "Starting NodeFlow...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        QColor("#f0f0f0"),
    )
    app.processEvents()

    splash.showMessage(
        "Applying theme...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        QColor("#f0f0f0"),
    )
    LOGGER.debug("Applying theme")
    apply_theme(app)
    app.processEvents()

    splash.showMessage(
        "Initializing database...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        QColor("#f0f0f0"),
    )
    LOGGER.debug("Initializing database")
    database.create_tables()
    app.processEvents()

    splash.showMessage(
        "Loading workspace...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        QColor("#f0f0f0"),
    )
    LOGGER.debug("Creating main window")
    window = MainWindow()
    window.show()
    app.processEvents()
    splash.finish(window)
    LOGGER.info("NodeFlow startup complete")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
