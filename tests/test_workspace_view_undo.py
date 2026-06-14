import database
from PySide6.QtGui import QTextCursor
from repositories.base import initialize_database
from ui.workspace.workspace_view import WorkspaceView


def test_workspace_undo_prefers_text_history_after_autosave(qtbot):
    initialize_database()
    database.add_project("Undo Replace")
    project = database.get_all_projects()[0]
    participant_id = database.add_participant(project["id"], "Alice")
    database.add_document(project["id"], "Doc 1", "alpha beta", participant_id)

    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    widget.show()

    widget.center_pane.show_find_bar()
    widget.center_pane.text_edit.setFocus()
    widget.center_pane.text_edit.moveCursor(QTextCursor.MoveOperation.End)
    widget.center_pane.text_edit.insertPlainText(" gamma")
    assert widget.center_pane.is_dirty

    widget.center_pane.autosave_document()
    assert not widget.center_pane.is_dirty
    assert widget.center_pane.text_edit.toPlainText() == "alpha beta gamma"

    widget.undo_workspace_action()

    assert widget.center_pane.text_edit.toPlainText() == "alpha beta"
    assert widget.center_pane.is_dirty


def test_replace_all_records_restorable_document_snapshot(qtbot):
    initialize_database()
    database.add_project("Replace All Undo")
    project = database.get_all_projects()[0]
    participant_id = database.add_participant(project["id"], "Alice")
    document_id = database.add_document(
        project["id"], "Doc 1", "of alpha of beta", participant_id
    )
    node_id = database.add_node(project["id"], "Theme", None, "#FFFF00")
    database.add_coded_segment(document_id, node_id, participant_id, 3, 16, "alpha of beta")

    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    widget.show()

    replaced_count = widget.center_pane._replace_all_confirmed("of", "around")

    assert replaced_count == 2
    assert widget.center_pane.text_edit.toPlainText() == "around alpha around beta"
    segments = database.get_coded_segments_for_document(document_id)
    assert segments[0]["content_preview"] == "alpha around beta"

    widget.undo_workspace_action()

    content, _ = database.get_document_content(document_id)
    segments = database.get_coded_segments_for_document(document_id)
    assert content == "of alpha of beta"
    assert widget.center_pane.text_edit.toPlainText() == "of alpha of beta"
    assert segments[0]["segment_start"] == 3
    assert segments[0]["segment_end"] == 16
    assert segments[0]["content_preview"] == "alpha of beta"
