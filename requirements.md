# Project: NodeFlow - Features & Specifications

## 1. Core Objective

To develop a desktop application using Python and PySide6 that streamlines the process of qualitative text analysis. The software enables researchers to manage multiple projects, import documents, assign codes (labels) to text segments, and organize these codes into a fully hierarchical and editable tree structure for easy retrieval and export.

## 2. Key Features

### Project & Data Management

* **Startup View**: The application starts with a dedicated project selection screen, similar to professional creative software. Users can select an existing project or create a new one to begin a session.
* **Project-Specific Workspaces**: Once a project is selected, the user enters a workspace dedicated entirely to that project's data (participants, documents, and nodes).
* **Participant Management**: Within a project's workspace, users have full CRUD (Create, Read, Update, Delete) capabilities for managing the list of research participants.
* **Document Handling**:
    * Users can import documents from both plain text (`.txt`) and Microsoft Word (`.docx`) files.
    * Upon import, a dialog prompts the user to assign the document to a specific, existing participant, creating a clear data link.

### Coding & Analysis

* **Multi-Level Hierarchical Node Tree**: A central feature is a `QTreeWidget` that allows for the creation of an infinitely deep hierarchy of nodes (e.g., `1. Theme` -> `1.1. Sub-theme` -> `1.1.1. Specific Point`).
* **Automatic Node Numbering**: The tree automatically prepends a hierarchical number (e.g., `1.`, `1.1.`, `2.1.3.`) to each node for enhanced readability. This numbering automatically updates when nodes are reordered or their levels are changed.
* **Full Node Structure Manipulation**: Users have complete control over the node tree structure via dedicated buttons:
    * **Move Up/Down**: To reorder nodes among their siblings.
    * **Promote (Outdent)**: To move a child node up one level, making it a sibling of its former parent.
    * **Demote (Indent)**: To move a node down one level, making it a child of the sibling directly above it.
* **Contextual Text Coding**: Users can highlight any segment of text in the content view and right-click to open a dynamic, nested context menu. This menu mirrors the entire node tree, allowing for fast and intuitive code assignment.
* **Coded Segment Viewer**: A dedicated panel lists all coded segments for the active document, showing the coded text, the assigned node, and the participant who said it.

### Search & Export

* **(Future Feature) Advanced Search**: A planned feature to allow users to search for coded segments by participant, node, or keywords.
* **JSON Export**: Users can export the entire coded structure of a document to a hierarchical JSON file. This is ideal for data backup, interoperability with other software, or for input into data analysis and AI tools.
* **Word Document Export**: Users can generate a formatted `.docx` report. The report uses headings for each node (respecting the hierarchy) and lists the associated coded text segments as bullet points underneath, creating a clean, readable summary for papers or presentations.

## 3. System Requirements

* **Operating System**: Windows (initially)
* **Python**: Python 3.10+
* **Core Libraries**: PySide6, python-docx