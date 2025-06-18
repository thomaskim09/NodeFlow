from PySide6.QtWidgets import QFileDialog
from docx import Document
from openpyxl.styles import Font
import json
import re
import database
import openpyxl


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


def export_to_excel(project_id, parent_widget=None):
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
        nodes_by_parent.get(node["parent_id"], []).append(node)

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
            headers = ["Participant", "Coded Segment", "Document"]
            ws.append(headers)

            # --- NEW: Bold headers ---
            header_font = Font(bold=True)
            for cell in ws[1]:
                cell.font = header_font

            # Get all node IDs for this sheet (self + descendants)
            ids_to_include = [node_id] + get_all_descendant_ids(node_id)

            # Filter segments and write to sheet
            segments_for_sheet = [
                s for s in coded_segments if s["node_id"] in ids_to_include
            ]
            for seg in segments_for_sheet:
                participant = seg["participant_name"] or "N/A"
                ws.append([participant, seg["content_preview"], seg["document_title"]])

            # Adjust column widths
            ws.column_dimensions["A"].width = 25
            ws.column_dimensions["B"].width = 80
            ws.column_dimensions["C"].width = 40

            # Recurse for children
            create_sheets_recursively(node_id, prefix=current_prefix)

    # Start the process from the root (nodes with no parent)
    create_sheets_recursively(None)

    wb.save(file_path)
    print(f"Excel report saved to {file_path}")


# --- NEW: Selective node family export to Word ---
def export_node_family_to_word(project_id, start_node_id, parent_widget=None):
    """Exports a specific node and its children to a .docx file."""
    if not start_node_id:
        return

    # Fetch all project data
    all_nodes = database.get_nodes_for_project(project_id)
    coded_segments = database.get_coded_segments_for_project(project_id)
    nodes_map = {n["id"]: n for n in all_nodes}

    start_node = nodes_map.get(start_node_id)
    if not start_node:
        return

    file_path, _ = QFileDialog.getSaveFileName(
        parent_widget,
        f"Save Word Report for '{start_node['name']}'",
        "",
        "Word Documents (*.docx)",
    )
    if not file_path:
        return

    # Get descendant IDs
    nodes_by_parent = {n_id: [] for n_id in nodes_map}
    nodes_by_parent[None] = []
    for n in all_nodes:
        nodes_by_parent.setdefault(n["parent_id"], []).append(n)

    def get_all_descendant_ids(node_id):
        descendants = []
        for child_node in nodes_by_parent.get(node_id, []):
            descendants.append(child_node["id"])
            descendants.extend(get_all_descendant_ids(child_node["id"]))
        return descendants

    ids_to_include = [start_node_id] + get_all_descendant_ids(start_node_id)

    # Filter segments
    segments_by_node = {}
    for seg in coded_segments:
        if seg["node_id"] in ids_to_include:
            node_id = seg["node_id"]
            if node_id not in segments_by_node:
                segments_by_node[node_id] = []
            segments_by_node[node_id].append(seg)

    # Build the document
    doc = Document()
    doc.add_heading(f"Report for Node: {start_node['name']}", 0)

    def write_nodes_recursively(parent_id, level=0, prefix=""):
        children = sorted(
            [
                n
                for n in all_nodes
                if n["parent_id"] == parent_id and n["id"] in ids_to_include
            ],
            key=lambda x: x["position"],
        )
        # Special handling for the starting node
        if parent_id == start_node.get("parent_id"):
            children = [start_node] + [c for c in children if c["id"] != start_node_id]
            children = [start_node]

        for i, node in enumerate(children):
            current_prefix = f"{prefix}{i + 1}."
            doc.add_heading(f"{current_prefix} {node['name']}", level=level + 1)

            if node["id"] in segments_by_node:
                for seg_data in segments_by_node[node["id"]]:
                    participant = seg_data["participant_name"] or "N/A"
                    document = seg_data["document_title"] or "N/A"
                    text = seg_data["content_preview"]
                    p = doc.add_paragraph(style="List Bullet")
                    p.add_run(f"{participant} in '{document}': ").bold = True
                    p.add_run(text)

            write_nodes_recursively(node["id"], level + 1, current_prefix)

    # Start recursion from the selected node
    write_nodes_recursively(start_node_id, level=1, prefix="1.")
    # Also need to write the start_node itself
    doc.add_heading(f"1. {start_node['name']}", level=1)
    if start_node_id in segments_by_node:
        for seg_data in segments_by_node[start_node_id]:
            participant = seg_data["participant_name"] or "N/A"
            document = seg_data["document_title"] or "N/A"
            text = seg_data["content_preview"]
            p = doc.add_paragraph(style="List Bullet")
            p.add_run(f"{participant} in '{document}': ").bold = True
            p.add_run(text)

    doc.save(file_path)


# --- NEW: Selective node family export to Excel ---
def export_node_family_to_excel(project_id, start_node_id, parent_widget=None):
    """Exports a specific node and its children to an .xlsx file."""
    if not start_node_id:
        return

    all_nodes = database.get_nodes_for_project(project_id)
    coded_segments = database.get_coded_segments_for_project(project_id)
    nodes_map = {n["id"]: n for n in all_nodes}

    start_node = nodes_map.get(start_node_id)
    if not start_node:
        return

    file_path, _ = QFileDialog.getSaveFileName(
        parent_widget,
        f"Save Excel Report for '{start_node['name']}'",
        "",
        "Excel Files (*.xlsx)",
    )
    if not file_path:
        return

    nodes_by_parent = {n_id: [] for n_id in nodes_map}
    nodes_by_parent[None] = []
    for n in all_nodes:
        nodes_by_parent.setdefault(n["parent_id"], []).append(n)

    for children_list in nodes_by_parent.values():
        children_list.sort(key=lambda x: x["position"])

    def get_all_descendant_ids(node_id):
        descendants = []
        for child_node in nodes_by_parent.get(node_id, []):
            descendants.append(child_node["id"])
            descendants.extend(get_all_descendant_ids(child_node["id"]))
        return descendants

    ids_to_include = [start_node_id] + get_all_descendant_ids(start_node_id)

    wb = openpyxl.Workbook()
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])

    def sanitize_sheet_name(name):
        return re.sub(r"[\\/*?:\[\]]", "", name)[:31]

    # Create one sheet for the whole family
    sheet_name = sanitize_sheet_name(start_node["name"])
    ws = wb.create_sheet(title=sheet_name)
    headers = ["Node", "Participant", "Coded Segment", "Document"]
    ws.append(headers)

    header_font = Font(bold=True)
    for cell in ws[1]:
        cell.font = header_font

    # Filter segments and write to sheet
    segments_for_sheet = [s for s in coded_segments if s["node_id"] in ids_to_include]
    for seg in sorted(segments_for_sheet, key=lambda s: s["node_name"]):
        ws.append(
            [
                seg["node_name"],
                seg["participant_name"] or "N/A",
                seg["content_preview"],
                seg["document_title"],
            ]
        )

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 80
    ws.column_dimensions["D"].width = 40

    wb.save(file_path)
