import sqlite3

import pytest
import openpyxl
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QMessageBox

import database
from repositories.base import SCHEMA_VERSION, get_connection, initialize_database
from services.dashboard_service import DashboardQuery, dashboard_service
from services.import_service import import_service
from ui.dashboard.crosstab_widget import CrosstabWidget
from ui.workspace.workspace_view import WorkspaceView
from utils.app_paths import get_database_backups_dir, get_database_path


def test_existing_database_migration_preserves_data_and_creates_backup():
    path = get_database_path()
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                participant_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO projects (name) VALUES ('Legacy');
            INSERT INTO participants (project_id, name) VALUES (1, 'Alice');
            INSERT INTO documents (project_id, participant_id, title, content)
            VALUES (1, 1, 'Interview', 'alpha beta');
            PRAGMA user_version = 2;
            """
        )

    initialize_database()

    content, participant_id = database.get_document_content(1)
    assert content == "alpha beta"
    assert participant_id == 1
    backups = list(get_database_backups_dir().glob("nodeflow_backup_*.db"))
    assert backups
    with get_connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(documents)")}
        segment_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(coded_segments)")
        }
    assert "source_sha256" in columns
    assert "remark" in segment_columns


def test_initialize_database_is_idempotent_for_latest_schema():
    initialize_database()
    database.add_project("Stable")

    initialize_database()

    assert database.get_all_projects()[0]["name"] == "Stable"


def test_dashboard_cache_is_invalidated_after_segment_write():
    initialize_database()
    database.add_project("Analysis")
    project_id = database.get_all_projects()[0]["id"]
    participant_id = database.add_participant(project_id, "Alice")
    document_id = database.add_document(
        project_id, "Interview", "alpha beta gamma", participant_id
    )
    node_id = database.add_node(project_id, "Theme", None, "#111111")
    database.add_coded_segment(document_id, node_id, participant_id, 0, 5, "alpha")
    query = DashboardQuery(project_id=project_id, doc_id=-1, part_id=-1, node_id=-1)

    assert dashboard_service.load(query)["coded_words"] == 1
    database.add_coded_segment(document_id, node_id, participant_id, 6, 10, "beta")

    assert dashboard_service.load(query)["coded_words"] == 2


def test_crosstab_uses_document_id_not_duplicate_title(qtbot):
    widget = CrosstabWidget({"theme": "Light", "language": "English"})
    qtbot.addWidget(widget)
    nodes = [
        {"id": 1, "name": "Theme 1"},
        {"id": 2, "name": "Theme 2"},
    ]
    segments = [
        {
            "document_id": 1,
            "document_title": "Same",
            "segment_start": 0,
            "segment_end": 5,
            "node_id": 1,
        },
        {
            "document_id": 2,
            "document_title": "Same",
            "segment_start": 0,
            "segment_end": 5,
            "node_id": 2,
        },
    ]

    widget.update_crosstab(segments, nodes)

    assert widget.table.item(0, 1).text() == "0"
    assert widget.table.item(1, 0).text() == "0"


def test_text_import_copies_original_and_stores_metadata(tmp_path):
    initialize_database()
    source = tmp_path / "interview.txt"
    source.write_text("alpha beta", encoding="utf-8")

    title, content, metadata = import_service.read_text_document(str(source))

    assert title == "interview.txt"
    assert content == "alpha beta"
    assert metadata["source_filename"] == "interview.txt"
    copied_path = metadata["source_copy_path"]
    assert copied_path
    assert copied_path != str(source)
    assert metadata["source_sha256"]
    assert metadata["source_kind"] == "txt"

    database.add_project("Import")
    project_id = database.get_all_projects()[0]["id"]
    document_id = database.add_document(project_id, title, content, None, metadata)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT source_filename, source_copy_path, source_sha256 FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
    assert row["source_filename"] == "interview.txt"
    assert row["source_copy_path"] == copied_path
    assert row["source_sha256"] == metadata["source_sha256"]


def test_excel_import_copies_workbook_and_records_source_rows(tmp_path):
    initialize_database()
    database.add_project("Excel Import")
    project_id = database.get_all_projects()[0]["id"]
    workbook_path = tmp_path / "batch.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["Title", "Content", "Participant"])
    sheet.append(["Doc A", "alpha beta", "Alice"])
    sheet.append(["Doc B", "gamma delta", "Bob"])
    workbook.save(workbook_path)

    imported, errors = import_service.import_excel_data(
        project_id,
        str(workbook_path),
        {"title": "Title", "content": "Content", "participant": "Participant"},
    )

    assert imported == 2
    assert errors == []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT title, source_filename, source_copy_path, source_kind, source_row
            FROM documents
            ORDER BY title
            """
        ).fetchall()
    assert [row["source_row"] for row in rows] == [2, 3]
    assert {row["source_filename"] for row in rows} == {"batch.xlsx"}
    assert {row["source_kind"] for row in rows} == {"xlsx"}
    assert len({row["source_copy_path"] for row in rows}) == 1


def test_invalid_segment_ranges_are_rejected():
    initialize_database()
    database.add_project("Ranges")
    project_id = database.get_all_projects()[0]["id"]
    participant_id = database.add_participant(project_id, "Alice")
    document_id = database.add_document(project_id, "Doc", "alpha", participant_id)
    node_id = database.add_node(project_id, "Theme", None, "#111111")

    with pytest.raises(ValueError):
        database.add_coded_segment(document_id, node_id, participant_id, 0, 99, "bad")


def test_confirmed_segment_deletion_autosaves(qtbot, monkeypatch):
    fixture = _workspace_with_segment()
    widget = fixture["widget"]
    qtbot.addWidget(widget)
    document_id = fixture["document_id"]
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Yes
    )

    _delete_text_range(widget.center_pane, 6, 10)
    widget.center_pane.autosave_document()

    content, _ = database.get_document_content(document_id)
    assert content == "alpha "
    assert database.get_coded_segments_for_document(document_id) == []
    assert not widget.center_pane.is_dirty


def test_canceling_segment_deletion_restores_text_and_segment(qtbot, monkeypatch):
    fixture = _workspace_with_segment()
    widget = fixture["widget"]
    qtbot.addWidget(widget)
    document_id = fixture["document_id"]
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.No
    )

    _delete_text_range(widget.center_pane, 6, 10)

    content, _ = database.get_document_content(document_id)
    assert widget.center_pane.text_edit.toPlainText() == "alpha beta"
    assert content == "alpha beta"
    segment = widget.center_pane._coded_segments_cache[0]
    assert segment["segment_start"] == 6
    assert segment["segment_end"] == 10
    assert [
        (
            selection.cursor.selectionStart(),
            selection.cursor.selectionEnd(),
        )
        for selection in widget.center_pane.text_edit.extraSelections()
    ] == [(6, 10)]
    assert len(database.get_coded_segments_for_document(document_id)) == 1
    assert not widget.center_pane.is_dirty


def test_deleting_part_of_segment_adjusts_without_prompt(qtbot, monkeypatch):
    fixture = _workspace_with_segment()
    widget = fixture["widget"]
    qtbot.addWidget(widget)
    document_id = fixture["document_id"]

    def fail_if_prompted(*args, **kwargs):
        raise AssertionError("Partial segment edits should not prompt.")

    monkeypatch.setattr(QMessageBox, "warning", fail_if_prompted)

    _delete_text_range(widget.center_pane, 7, 9)
    segment = widget.center_pane._coded_segments_cache[0]
    saved = widget.center_pane.save_document(show_success_prompt=False)

    content, _ = database.get_document_content(document_id)
    assert saved is True
    assert content == "alpha ba"
    assert segment["segment_start"] == 6
    assert segment["segment_end"] == 8
    assert segment["content_preview"] == "ba"
    segments = database.get_coded_segments_for_document(document_id)
    assert len(segments) == 1
    assert segments[0]["content_preview"] == "ba"
    assert not widget.center_pane.is_dirty


def _workspace_with_segment():
    initialize_database()
    database.add_project("Segment Safety")
    project = database.get_all_projects()[0]
    participant_id = database.add_participant(project["id"], "Alice")
    document_id = database.add_document(
        project["id"], "Doc 1", "alpha beta", participant_id
    )
    node_id = database.add_node(project["id"], "Theme", None, "#111111")
    database.add_coded_segment(document_id, node_id, participant_id, 6, 10, "beta")
    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    return {"widget": widget, "document_id": document_id}


def _delete_text_range(content_view, start: int, end: int) -> None:
    cursor = content_view.text_edit.textCursor()
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    cursor.removeSelectedText()
