from PySide6.QtWidgets import QMainWindow
from .workspace_view import WorkspaceView


class WorkspaceMainWindow(QMainWindow):
    def __init__(self, project_id, project_name, startup_window):
        super().__init__()
        self.project_id = project_id
        self.project_name = project_name
        self.startup_window = startup_window
        self.setWindowTitle(f"NodeFlow - {project_name}")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        self.workspace_view = WorkspaceView(
            project_id, project_name, self.back_to_startup
        )
        self.setCentralWidget(self.workspace_view)

    def back_to_startup(self):
        self.close()
        if self.startup_window:
            self.startup_window.window().show()
