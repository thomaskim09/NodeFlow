import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QSize
from PySide6.QtGui import QScreen, QIcon

from ui_startup_view import StartupView
from ui_workspace_view import WorkspaceView
import database


class MainWindow(QMainWindow):
    """
    The main window of the application. It acts as a controller to switch
    between the startup view and the main workspace view.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("NodeFlow")
        self.setWindowIcon(QIcon("icon.png"))
        database.create_tables()
        self.show_startup_view()

    def center_window(self):
        """Helper function to center the main window on the screen."""
        center_point = QScreen.availableGeometry(QApplication.primaryScreen()).center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def show_startup_view(self):
        """Displays the project selection screen."""
        self.setWindowTitle("NodeFlow - Select Project")
        self.setMinimumSize(QSize(500, 400))
        self.resize(500, 400)
        self.center_window()

        startup_view = StartupView(self.show_workspace_view)
        self.setCentralWidget(startup_view)

    def show_workspace_view(self, project_id, project_name):
        """Displays the main workspace for the selected project."""
        self.setWindowTitle(f"NodeFlow - {project_name}")
        self.setMinimumSize(QSize(1000, 700))
        self.resize(1200, 800)
        self.center_window()

        # WorkspaceView no longer needs the callback
        workspace_view = WorkspaceView(project_id, project_name)
        self.setCentralWidget(workspace_view)


# Main execution block
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
