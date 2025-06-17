# NodeFlow - Qualitative Analysis Tool

NodeFlow is a user-friendly desktop application designed to assist researchers and students in the qualitative analysis of text-based data, such as interview transcripts. Built with Python and PySide6, it provides a powerful and modern interface to simplify the process of coding (labeling) text segments and organizing these codes into a fully hierarchical structure.

## Key Features

* **Professional Project-Based Workflow**: A startup screen to create new projects or select existing ones before entering the main workspace.
* **Full Participant Management**: Full CRUD (Create, Read, Update, Delete) functionality for managing research participants within each project.
* **Advanced Hierarchical Node Coding**:
    * Create and manage "nodes" (codes/labels) in a flexible, multi-level tree structure.
    * Automatic hierarchical numbering for clear organization (e.g., 1., 1.1., 1.1.1.).
    * Full control to reorder nodes (Move Up/Down) and change their level (Promote/Demote).
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