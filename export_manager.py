from PySide6.QtWidgets import QFileDialog
from docx import Document
import json
import database


def export_to_word(project_id, document_id, parent_widget=None):
    """Exports the coded segments of a document to a .docx file."""
    if not document_id:
        return

    # Ask user for save location
    file_path, _ = QFileDialog.getSaveFileName(
        parent_widget, "Save Word Report", "", "Word Documents (*.docx)"
    )
    if not file_path:
        return

    # --- Fetch and structure the data ---
    nodes = database.get_nodes_for_project(project_id)
    coded_segments = database.get_coded_segments_for_document(document_id)

    # Group segments by their node ID
    segments_by_node = {}
    for seg in coded_segments:
        node_id = seg["node_id"]
        if node_id not in segments_by_node:
            segments_by_node[node_id] = []
        segments_by_node[node_id].append(seg["content_preview"])

    # --- Build the Word Document ---
    doc = Document()
    doc.add_heading("Qualitative Analysis Report", 0)

    # A recursive function to write nodes and their segments
    def write_nodes_recursively(parent_id=None, level=0, prefix=""):
        # Get all children of the current parent
        children = sorted(
            [n for n in nodes if n["parent_id"] == parent_id],
            key=lambda x: x["position"],
        )

        for i, node in enumerate(children):
            current_prefix = f"{prefix}{i + 1}."

            # Add node name as a heading (e.g., Heading 1, Heading 2)
            doc.add_heading(f"{current_prefix} {node['name']}", level=level + 1)

            # Check if there are any coded segments for this node
            if node["id"] in segments_by_node:
                for segment_text in segments_by_node[node["id"]]:
                    doc.add_paragraph(segment_text, style="List Bullet")

            # Recurse for children of this node
            write_nodes_recursively(
                parent_id=node["id"], level=level + 1, prefix=current_prefix
            )

    write_nodes_recursively()
    doc.save(file_path)
    print(f"Report saved to {file_path}")


def export_to_json(project_id, document_id, parent_widget=None):
    """Exports the coded segments of a document to a .json file."""
    if not document_id:
        return

    file_path, _ = QFileDialog.getSaveFileName(
        parent_widget, "Save JSON Export", "", "JSON Files (*.json)"
    )
    if not file_path:
        return

    # --- Fetch and structure the data ---
    nodes = database.get_nodes_for_project(project_id)
    coded_segments = database.get_coded_segments_for_document(document_id)

    segments_by_node = {}
    for seg in coded_segments:
        node_id = seg["node_id"]
        if node_id not in segments_by_node:
            segments_by_node[node_id] = []
        segments_by_node[node_id].append(seg["content_preview"])

    # --- Build the hierarchical JSON structure ---
    json_output = []

    def build_json_recursively(parent_id=None):
        children_data = []
        children = sorted(
            [n for n in nodes if n["parent_id"] == parent_id],
            key=lambda x: x["position"],
        )

        for node in children:
            node_obj = {
                "id": node["id"],
                "name": node["name"],
                "segments": segments_by_node.get(node["id"], []),
                "children": build_json_recursively(parent_id=node["id"]),
            }
            children_data.append(node_obj)
        return children_data

    json_output = build_json_recursively()

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=4)

    print(f"JSON data saved to {file_path}")
