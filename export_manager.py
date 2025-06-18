from PySide6.QtWidgets import QFileDialog
from docx import Document
import json
import re
import database
import openpyxl  # <-- Import openpyxl


def export_to_word(project_id, document_id, parent_widget=None):
    """Exports the coded segments of a document to a .docx file."""
    if not document_id:
        return

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
        segments_by_node[node_id].append(seg)  # <-- Store the whole segment dict

    # --- Build the Word Document ---
    doc = Document()
    doc.add_heading("Qualitative Analysis Report", 0)

    def write_nodes_recursively(parent_id=None, level=0, prefix=""):
        children = sorted(
            [n for n in nodes if n["parent_id"] == parent_id],
            key=lambda x: x["position"],
        )

        for i, node in enumerate(children):
            current_prefix = f"{prefix}{i + 1}."
            doc.add_heading(f"{current_prefix} {node['name']}", level=level + 1)

            if node["id"] in segments_by_node:
                for segment_data in segments_by_node[
                    node["id"]
                ]:  # <-- Iterate through segment data
                    participant = segment_data["participant_name"] or "N/A"
                    text = segment_data["content_preview"]
                    p = doc.add_paragraph(style="List Bullet")
                    p.add_run(f"{participant}: ").bold = True
                    p.add_run(text)

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

    nodes = database.get_nodes_for_project(project_id)
    coded_segments = database.get_coded_segments_for_document(document_id)

    segments_by_node = {}
    for seg in coded_segments:
        node_id = seg["node_id"]
        if node_id not in segments_by_node:
            segments_by_node[node_id] = []
        # Store a dictionary with participant and text
        segments_by_node[node_id].append(
            {
                "participant": seg["participant_name"] or "N/A",
                "text": seg["content_preview"],
            }
        )

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
                "segments": segments_by_node.get(
                    node["id"], []
                ),  # <-- Get the list of segment objects
                "children": build_json_recursively(parent_id=node["id"]),
            }
            children_data.append(node_obj)
        return children_data

    json_output = build_json_recursively()

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=4)

    print(f"JSON data saved to {file_path}")


def export_to_excel(project_id, document_id, parent_widget=None):
    """Exports coded segments to an Excel file with one sheet per node."""

    file_path, _ = QFileDialog.getSaveFileName(
        parent_widget, "Save Excel Report", "", "Excel Files (*.xlsx)"
    )
    if not file_path:
        return

    # Fetch data for the ENTIRE project
    nodes = database.get_nodes_for_project(project_id)
    coded_segments = database.get_coded_segments_for_project(project_id)

    # --- Data Structuring for Traversal ---
    nodes_by_id = {n["id"]: n for n in nodes}
    nodes_by_parent = {n_id: [] for n_id in nodes_by_id}
    nodes_by_parent[None] = []  # For root nodes

    for n_id, node in nodes_by_id.items():
        nodes_by_parent[node["parent_id"]].append(node)

    # Sort all children lists by position
    for children_list in nodes_by_parent.values():
        children_list.sort(key=lambda x: x["position"])

    # --- Descendant and Segment Mapping ---
    descendant_cache = {}

    def get_all_descendant_ids(node_id):
        if node_id in descendant_cache:
            return descendant_cache[node_id]
        descendants = []
        for child_node in nodes_by_parent.get(node_id, []):
            descendants.append(child_node["id"])
            descendants.extend(get_all_descendant_ids(child_node["id"]))
        descendant_cache[node_id] = descendants
        return descendants

    # --- Workbook Creation ---
    wb = openpyxl.Workbook()
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])

    def sanitize_sheet_name(name):
        name = re.sub(r"[\\/*?:\[\]]", "", name)
        return name[:31]

    # --- Recursive Sheet Creation ---
    def create_sheets_recursively(parent_id, prefix=""):
        children = nodes_by_parent.get(parent_id, [])
        for i, node in enumerate(children):
            node_id = node["id"]
            current_prefix = f"{prefix}{i + 1}."
            sheet_name = sanitize_sheet_name(f"{current_prefix} {node['name']}")

            # Create worksheet
            ws = wb.create_sheet(title=sheet_name)
            ws.append(["Participant", "Coded Segment"])

            # Get all node IDs for this sheet (self + descendants)
            ids_to_include = [node_id] + get_all_descendant_ids(node_id)

            # Filter segments and write to sheet
            segments_for_sheet = [
                s for s in coded_segments if s["node_id"] in ids_to_include
            ]
            for seg in segments_for_sheet:
                participant = seg["participant_name"] or "N/A"
                ws.append([participant, seg["content_preview"]])

            # Adjust column widths
            ws.column_dimensions["A"].width = 25
            ws.column_dimensions["B"].width = 80

            # Recurse for children
            create_sheets_recursively(node_id, prefix=current_prefix)

    # Start the process from the root (nodes with no parent)
    create_sheets_recursively(None)

    wb.save(file_path)
    print(f"Excel report saved to {file_path}")
