import tkinter as tk
from tkinter import ttk, messagebox
import database


class ProjectManager:
    def __init__(self, parent):
        """
        Initializes the Project Manager UI components within the parent widget.
        'parent' will be the left_pane from main.py.
        """
        self.parent = parent
        self.active_project_id = tk.StringVar()

        # Create a container frame for project management widgets
        project_frame = ttk.LabelFrame(
            self.parent, text="Project Management", padding=10
        )
        project_frame.pack(fill="x", padx=10, pady=10)

        # Project selection dropdown
        ttk.Label(project_frame, text="Active Project:").pack(fill="x")

        self.project_combo = ttk.Combobox(
            project_frame, textvariable=self.active_project_id, state="readonly"
        )
        self.project_combo.pack(fill="x", expand=True, pady=(0, 5))
        self.project_combo.bind("<<ComboboxSelected>>", self.on_project_select)

        # Button to create a new project
        new_project_button = ttk.Button(
            project_frame, text="New Project...", command=self.open_new_project_dialog
        )
        new_project_button.pack(fill="x")

        # Load existing projects into the dropdown
        self.load_projects()

    def load_projects(self):
        """Fetches projects from the database and populates the combobox."""
        projects = database.get_all_projects()
        # Format for display: "Project Name (ID: 1)"
        self.project_map = {f"{p['name']} (ID: {p['id']})": p["id"] for p in projects}
        self.project_combo["values"] = list(self.project_map.keys())

        if self.project_combo["values"]:
            self.project_combo.current(0)  # Select the first project by default
            self.on_project_select()  # Trigger the selection event manually

    def on_project_select(self, event=None):
        """Handles the event when a project is selected from the dropdown."""
        selected_display_name = self.active_project_id.get()
        project_id = self.project_map.get(selected_display_name)

        if project_id:
            print(f"Switched to project ID: {project_id}")
            # Later, this will trigger loading of participants, nodes, etc.
            # For now, we just print to confirm it's working.

    def open_new_project_dialog(self):
        """Opens a Toplevel window to get details for a new project."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Create New Project")
        self.dialog.geometry("300x150")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)  # Keep dialog on top of the main window
        self.dialog.grab_set()  # Modal behavior

        frame = ttk.Frame(self.dialog, padding=10)
        frame.pack(expand=True, fill="both")

        ttk.Label(frame, text="Project Name:").pack(pady=5)
        self.new_project_name_entry = ttk.Entry(frame)
        self.new_project_name_entry.pack(fill="x", expand=True)
        self.new_project_name_entry.focus_set()  # Set focus to the entry field

        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        save_button = ttk.Button(
            button_frame, text="Save", command=self.save_new_project
        )
        save_button.pack(side="left", padx=5)

        cancel_button = ttk.Button(
            button_frame, text="Cancel", command=self.dialog.destroy
        )
        cancel_button.pack(side="left", padx=5)

    def save_new_project(self):
        """Validates input and saves the new project to the database."""
        project_name = self.new_project_name_entry.get().strip()
        if not project_name:
            messagebox.showerror(
                "Error", "Project name cannot be empty.", parent=self.dialog
            )
            return

        database.add_project(project_name)
        messagebox.showinfo(
            "Success",
            f"Project '{project_name}' created successfully.",
            parent=self.dialog,
        )
        self.dialog.destroy()
        self.load_projects()  # Refresh the project list in the main window
