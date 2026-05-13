import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QSplashScreen
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QColor
import os

from ui.startup_view import StartupView

from managers.theme_manager import apply_theme
import database
from utils.common import get_resource_path
from services.logging_service import configure_logging


class MainWindow(QMainWindow):
    """
    The main window of the application. It acts as a controller to show the startup view only.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NodeFlow")
        if os.path.exists(get_resource_path("icon.png")):
            self.setWindowIcon(QIcon(get_resource_path("icon.png")))
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


if __name__ == "__main__":
    configure_logging()
    app = QApplication(sys.argv)
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
    apply_theme(app)
    app.processEvents()

    splash.showMessage(
        "Initializing database...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        QColor("#f0f0f0"),
    )
    database.create_tables()
    app.processEvents()

    splash.showMessage(
        "Loading workspace...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        QColor("#f0f0f0"),
    )
    window = MainWindow()
    window.show()
    app.processEvents()
    splash.finish(window)
    sys.exit(app.exec())
