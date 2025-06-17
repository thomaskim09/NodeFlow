# Project: NodeFlow - Features & Specifications

## 1. Core Objective
To develop a desktop application that streamlines the process of qualitative text analysis. The software will enable researchers to import interview transcripts, assign codes (labels) to text segments, and organize these codes into a hierarchical tree structure (nodes) for easy retrieval and export.

## 2. Key Features

### Project & Data Management
* **Project Management**: The application will support the creation and management of multiple projects. Each project will contain its own participants, content, and node hierarchy.
* **Participant Management**: Users can add, edit, and delete participants for each project.
* **Content Handling**: Users can import text content (e.g., from a .txt file) for analysis. The content will be linkable to participants.

### Coding & Analysis
* **Hierarchical Node Tree**: A central feature will be a tree view for creating a multi-level hierarchy of nodes (e.g., "Themes" -> "Sub-theme 1.1" -> "Specific Point 1.1.1").
* **Text Coding**: Users can highlight text in the content view and assign one or more nodes from the tree to the selection.
* **Node Reordering**: The UI will provide an intuitive way to rearrange nodes within the tree (e.g., move up/down, change level). A drag-and-drop interface is the ultimate goal.
* **Bilingual Support**: All text fields and search functions must support both English and Chinese characters.

### Search & Export
* **Advanced Search**: Users can search for coded segments by participant, by node, or by keywords within the content itself.
* **JSON Export**: Export selected nodes and their corresponding coded text segments into a structured JSON file.
* **Word Export**: Generate a Word document that organizes the coded text segments under their respective node headings, indicating which participant provided the response.

## 3. System Requirements
* **Operating System**: Windows (initially)
* **Python**: Python 3.10+