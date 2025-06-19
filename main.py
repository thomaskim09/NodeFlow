import sys
import time
from PySide6.QtWidgets import QApplication, QMainWindow, QSplashScreen
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap
import os

from ui.startup_view import StartupView
from ui.workspace.workspace_view import WorkspaceView

from managers.theme_manager import apply_theme
import database
from utils.common import get_resource_path


class MainWindow(QMainWindow):
    """
    The main window of the application. It acts as a controller to switch
    between the startup view and the main workspace view.
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
        startup_view = StartupView(self.show_workspace_view)
        self.setCentralWidget(startup_view)
        self.center_window()

    def show_workspace_view(self, project_id, project_name):
        """Displays the main workspace, deferring data load to a background thread."""
        self.setWindowTitle(f"NodeFlow - {project_name}")
        self.setMinimumSize(QSize(1000, 700))
        self.resize(1200, 800)
        workspace_view = WorkspaceView(project_id, project_name, self.show_startup_view)
        self.setCentralWidget(workspace_view)
        self.center_window()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pixmap = QPixmap(get_resource_path("splashscreen.png"))
    splash = QSplashScreen(pixmap)
    splash.show()
    app.processEvents()
    apply_theme(app)
    database.create_tables()
    time.sleep(2)
    window = MainWindow()
    window.show()
    splash.finish(window)
    sys.exit(app.exec())
