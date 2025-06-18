# Project: NodeFlow - Features & Specifications

## 1. Core Objective

To develop a user-friendly desktop application using Python and PySide6 that streamlines the process of qualitative text analysis. The software enables researchers to manage multiple projects, import documents, assign codes (labels) to text segments, and organize these codes into a fully hierarchical and editable tree structure for easy retrieval, analysis, and export.

## 2. Key Features

### Project & Data Management

* **Startup View**: The application starts with a dedicated project selection screen. Users can create, rename, delete, and select existing projects to begin a session.
* **Project-Specific Workspaces**: Once a project is selected, the user enters a workspace dedicated entirely to that project's data (participants, documents, and nodes).
* **Participant Management**: Within a project's workspace, users have full CRUD (Create, Read, Update, Delete) capabilities for managing the list of research participants.
* **Theme Management**: Users can switch between a **Light** and **Dark** theme via the settings menu for comfortable viewing.

### Document Handling

* **Versatile Document Import**:
    * Users can import documents from plain text (`.txt`), Microsoft Word (`.docx`), and Microsoft Excel (`.xlsx`) files.
    * Drag-and-drop functionality is supported for easy file import.
    * For text and Word documents, a dialog prompts the user to assign the document to a specific participant.
    * For Excel files, an advanced mapping dialog allows users to specify which columns correspond to the document title, content, and participant name.
* **Document Viewer**: An intuitive tab for viewing and editing document content.

### Coding & Analysis

* **Multi-Level Hierarchical Node Tree**: A central feature is a `QTreeWidget` that allows for the creation of an infinitely deep hierarchy of nodes (e.g., `1. Theme` -> `1.1. Sub-theme` -> `1.1.1. Specific Point`).
* **Full Node Structure Manipulation**:
    * Users have complete control over the node tree structure via **Drag-and-Drop**.
    * Nodes can be renamed, deleted, and have their color customized.
    * Hierarchical numbering is automatically applied and updated.
* **Contextual Text Coding**: Users can highlight any segment of text in the content view and click a node from the tree to assign the code.
* **Coded Segment Viewer**:
    * A dedicated panel lists all coded segments.
    * This view can be scoped to the **current document** or the **entire project**.
    * Includes filtering and search capabilities.
    * Clicking a segment navigates to its position in the document viewer.
* **Node Statistics**: The node tree displays statistics (word count percentage, segment count) for each node. This can be scoped to the **current document** or the **entire project**.

### Dashboard & Visualization

* **Project Dashboard**: A comprehensive dashboard provides a high-level overview of the project's data.
* **Key Metrics**: Displays total word count, number of coded segments, and coded word count.
* **Visualizations**:
    * **Bar and Pie Charts**: To visualize the distribution of codes.
    * **Word Cloud**: To show the frequency of applied node names.
    * **Cross-Tabulation Matrix**: To show the co-occurrence of codes within the same text segments.
* **Advanced Filtering**: Dashboard data can be filtered by document, participant, or a specific node and its descendants.

### Search & Export

* **Data Export**:
    * **JSON Export**: Export the entire project structure to a hierarchical JSON file, ideal for backups or interoperability.
    * **Word Document Export**: Generate a formatted `.docx` report with nodes as headings and coded segments as bullet points.
    * **Excel Export**: Export data to a structured `.xlsx` file, with options for single-sheet or multi-sheet reports based on the node hierarchy.
* **Selective Export**: Users can export a specific node "family" (the node and all its children) to Word or Excel.
* **Dashboard Export**: Charts, tables, and crosstab data from the dashboard can be exported to images or CSV files.

## 3. System Requirements

* **Operating System**: Cross-platform (tested on Windows)
* **Python**: Python 3.10+
* **Core Libraries**: PySide6, python-docx, openpyxl, wordcloud