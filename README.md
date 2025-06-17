# NodeFlow - Qualitative Analysis Tool

NodeFlow is a user-friendly desktop application designed to assist researchers and students in the qualitative analysis of text-based data, such as interview transcripts. It simplifies the process of coding (labeling) text segments and organizing these codes into a hierarchical structure.

## Key Features

* **Project-Based Workflow**: Manage multiple research projects, each with its own isolated set of data, participants, and node structures.
* **Participant Management**: Full CRUD (Create, Read, Update, Delete) functionality for managing research participants.
* **Hierarchical Node-Based Coding**:
    * Create and manage "nodes" (labels or codes) in a flexible, multi-level tree structure.
    * Easily assign one or more nodes to segments of your text content.
    * Reorder and restructure your node tree with user-friendly controls.
* **Bilingual Search**: Powerful search functionality that works seamlessly with both English and Chinese characters to find content by node or participant.
* **Flexible Data Export**:
    * Export coded data to **JSON** for further processing or analysis with AI tools.
    * Export to a **Word Document**, neatly formatted with participant responses organized under your chosen nodes.
* **Intuitive UI**: A clean, multi-paned interface built with Python/Tkinter that allows you to view your content, node tree, and participant list all at once.

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