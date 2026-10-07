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
* **Optional AI-Assisted Suggestions**:
    * Request temporary coding suggestions for selected text after explicit privacy confirmation.
    * Suggestions may match existing nodes or propose a new qualitative code; review, edit, accept, or reject each one.
    * New nodes are created and coded only after the researcher explicitly chooses **Create & Code**. AI never creates nodes or changes coding data autonomously.
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

## AI-Assisted Suggestions

AI suggestions are optional and require explicit researcher approval before any
node or coded segment is persisted. Selected text and the minimum existing node
context may be sent to an external AI provider after confirmation. Suggestions
are temporary and can be edited or rejected; NodeFlow does not claim that AI
suggestions are accurate or complete. A suggestion may match an existing node
or propose a new root code. New nodes are never created automatically: the
researcher must explicitly choose Create & Code, or confirm Use Existing & Code
when a matching node already exists. The editor toolbar button is enabled only
when non-empty text is selected.

Configure the provider, API key, model, and optional endpoint in the workspace
Settings dialog. The password-masked key is saved locally in
`data/settings.json`, so the startup script can use it on the next launch.
Environment variables such as `NODEFLOW_AI_API_KEY` override saved settings.
Gemini is the default provider and uses `gemini-flash-lite-latest`; optionally
set `NODEFLOW_AI_MODEL` to choose another Gemini model, including
`gemini-flash-latest`. To use an OpenAI-compatible provider instead, set
`NODEFLOW_AI_PROVIDER=openai_compatible` and `NODEFLOW_AI_API_URL`. The key is
not stored in SQLite or exported project files.

## macOS: Step-by-Step (Run from Source)

### Quick Script

```bash
./scripts/start-nodeflow.sh
```

This script is lightweight for normal use:

- first run: creates `.venv`, installs runtime dependencies, then launches
- later runs: launches directly without reinstalling everything

If you need to refresh the environment:

```bash
./scripts/start-nodeflow.sh --reinstall
```

For straightforward debugging, you can also run the app directly:

```bash
source .venv/bin/activate
python main.py
```

### Recommended (with `.venv`)

1. **Open Terminal and go to the project**
   ```bash
   cd /path/to/NodeFlow
   ```

2. **Check Python version**
   ```bash
   python3 --version
   ```
   Target: Python `3.13` or `3.14`.

3. **Create and activate virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"
   ```

5. **Start the app**
   ```bash
   python main.py
   ```

6. **Next time, run again**
   ```bash
   cd /path/to/NodeFlow
   source .venv/bin/activate
   python main.py
   ```

### Alternative (no virtual environment)

Use this only if you intentionally want global/user-site installs.

1. **Go to project**
   ```bash
   cd /path/to/NodeFlow
   ```

2. **Install dependencies to user site**
   ```bash
   python3 -m pip install --user -e ".[dev]" --break-system-packages
   ```

3. **Start the app**
   ```bash
   python3 main.py
   ```

If macOS blocks package installation, use the recommended `.venv` flow above.

## Windows Quick Start

```powershell
cd C:\path\to\NodeFlow
.\scripts\start-nodeflow.ps1
```

This PowerShell script only installs dependencies on first run, then starts the app directly on later runs.

To refresh the environment:

```powershell
.\scripts\start-nodeflow.ps1 --reinstall
```

## Packaging

PyInstaller builds must be produced on the target OS. Build the Windows bundle on Windows and the macOS app on macOS.

### Windows
```powershell
.\scripts\package-nodeflow.ps1
```

### macOS
```bash
./scripts/package-nodeflow.sh
```

### Packaging Targets

- `./scripts/package-nodeflow.sh macos` builds the macOS app bundle on macOS.
- `.\scripts\package-nodeflow.ps1 windows` builds the Windows executable on Windows.
- Cross-packaging is not supported here: Windows builds should be made on Windows, and macOS builds should be made on macOS.

## Testing

```bash
pytest
```
