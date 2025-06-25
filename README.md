<img src="resource/icon.png" width="20%" alt="Description of image">

# NodeFlow - Qualitative Analysis Tool 

NodeFlow is a user-friendly desktop application designed to assist researchers and students in the qualitative analysis of text-based data, such as interview transcripts. Built with Python and PySide6, it provides a powerful and modern interface to simplify the process of coding (labeling) text segments and organizing these codes into a fully hierarchical structure.

## Key Features

* **Professional Project-Based Workflow**: A startup screen to create new projects or select existing ones before entering the main workspace.
* **Full Participant Management**: Full CRUD (Create, Read, Update, Delete) functionality for managing research participants within each project.
* **Advanced Hierarchical Node Coding**:
    * Create and manage "nodes" (codes/labels) in a flexible, multi-level tree structure.
    * Automatic hierarchical numbering for clear organization (e.g., 1., 1.1., 1.1.1.).
    * Full control to reorder nodes (Move Up/Down) and change their level (Promote/Demote) via Drag-and-Drop.
* **Versatile Document Handling**:
    * Import documents from both plain text (`.txt`) and Microsoft Word (`.docx`) formats.
    * Assign each document to a specific participant upon import.
* **Intuitive Text Coding**:
    * Right-click on any selected text to bring up a dynamic, nested context menu of all your nodes.
    * Assign a code with a single click.
    * View all coded segments, their corresponding node, and the participant in a clear summary table.
* **Powerful Data Export**:
    * Export your coded data to a structured **JSON** file, perfect for backups or further processing with other tools and AI.
    * Export a clean, formatted **Word Document** report, with your nodes as headings and the coded text listed beneath them.
    * Export a comprehensive **Excel** report, with each node and its children's coded segments on a separate, hierarchically-ordered worksheet.

## Localization/Translation

- All translations are stored in YAML files in the `locales/` directory (e.g., `en.yml`, `zh.yml`).
- Use hierarchical keys for each string, e.g.:
  - `app.view.dashboard.default_title`
  - `app.view.dashboard.welcome_message`
- In code, use:
  ```python
  from utils.common import get_translation
  get_translation('app.view.dashboard.default_title', language)
  get_translation('app.view.dashboard.welcome_message', language, title='NodeFlow')
  ```
- To add a new language, create a new YAML file in `locales/` with the same key structure.

## Getting Started (For Developers)

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd NodeFlow
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    # Create the virtual environment
    python -m venv venv

    # Activate it (Windows)
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Application:**
    ```bash
    python main.py
    ```

## Packaging as an Executable (EXE) with PyInstaller

To create a standalone Windows executable from NodeFlow using PyInstaller:

1. **Install PyInstaller** (if not already installed):
    ```bash
    pip install pyinstaller
    ```

2. **Run PyInstaller** from the project root:
    ```bash
    pyinstaller --onefile --windowed --name "NodeFlow" --icon resource/icon.png --add-data "locales;locales" --add-data "resource;resource" main.py
    ```
    - `--name`: Bundle it in a specific file name.
    - `--onefile`: Bundle everything into a single EXE file.
    - `--windowed`: Prevents a console window from appearing (for GUI apps).
    - `--icon`: Sets the application icon.
    - `--add-data`: Ensures the `locales` and `resource` folders are included in the EXE. Use a semicolon `;` as the separator on Windows.

3. **Find your EXE** in the `dist/` folder:
    - The output will be at `dist/main.exe`.

4. **Distribute** the EXE file. You can share the EXE with others; they do not need Python installed.

**Note:**
- If you add or rename resource files, update the `--add-data` arguments accordingly.
- For troubleshooting, see the [PyInstaller documentation](https://pyinstaller.org/en/stable/).