import database
from PySide6.QtGui import QTextCursor
from repositories.base import initialize_database
from ui.workspace.workspace_view import WorkspaceView
from ui.workspace import node_tree_manager as node_tree_manager_module
from ui.workspace import participant_manager as participant_manager_module


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


def test_refresh_all_views_keeps_current_document_selected(qtbot):
    initialize_database()
    database.add_project("Refresh Selection")
    project = database.get_all_projects()[0]
    participant_id = database.add_participant(project["id"], "Alice")
    first_doc_id = database.add_document(project["id"], "Doc 1", "alpha", participant_id)
    second_doc_id = database.add_document(
        project["id"], "Doc 2", "beta gamma", participant_id
    )

    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    widget.show()

    assert widget.center_pane.current_document_id == first_doc_id
    widget.center_pane.load_document_list(doc_id_to_select=second_doc_id)
    assert widget.center_pane.current_document_id == second_doc_id

    widget.refresh_all_views()

    assert widget.center_pane.current_document_id == second_doc_id


def test_refresh_all_views_keeps_selected_node_and_participant_visible(
    qtbot, monkeypatch
):
    initialize_database()
    database.add_project("Refresh Sidebar Selection")
    project = database.get_all_projects()[0]
    participant_one = database.add_participant(project["id"], "Alice")
    participant_two = database.add_participant(project["id"], "Bob")
    database.add_document(project["id"], "Doc 1", "alpha", participant_one)
    first_node_id = database.add_node(project["id"], "Theme 1", None, "#111111")
    second_node_id = database.add_node(project["id"], "Theme 2", None, "#222222")

    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    widget.show()

    node_scrolls = []
    participant_scrolls = []

    original_node_scroll = widget.node_tree_manager.tree_widget.scrollToItem
    original_participant_scroll = widget.participant_manager.list_widget.scrollToItem

    def capture_node_scroll(item, hint):
        node_scrolls.append((item.data(0, 1), hint))
        return original_node_scroll(item, hint)

    def capture_participant_scroll(item, hint):
        row = widget.participant_manager.list_widget.row(item)
        participant_widget = widget.participant_manager.list_widget.itemWidget(item)
        participant_scrolls.append((participant_widget.participant_id, row, hint))
        return original_participant_scroll(item, hint)

    monkeypatch.setattr(
        widget.node_tree_manager.tree_widget, "scrollToItem", capture_node_scroll
    )
    monkeypatch.setattr(
        widget.participant_manager.list_widget,
        "scrollToItem",
        capture_participant_scroll,
    )

    widget.node_tree_manager.load_nodes(node_id_to_reselect=second_node_id)
    widget.participant_manager.load_participants(
        participant_id_to_select=participant_two
    )
    qtbot.wait(10)

    widget.refresh_all_views()
    qtbot.wait(10)

    assert widget.node_tree_manager.get_selected_node_id() == second_node_id
    assert widget.participant_manager.get_selected_participant_id() == participant_two
    assert node_scrolls[-1] == (
        second_node_id,
        node_tree_manager_module.QAbstractItemView.ScrollHint.PositionAtCenter,
    )
    assert participant_scrolls[-1] == (
        participant_two,
        1,
        participant_manager_module.QAbstractItemView.ScrollHint.PositionAtCenter,
    )


def test_workspace_splitters_keep_minimum_panel_sizes(qtbot):
    initialize_database()
    database.add_project("Splitter Minimums")
    project = database.get_all_projects()[0]

    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)

    assert not widget.main_splitter.childrenCollapsible()
    assert not widget.right_splitter.childrenCollapsible()
    assert widget.left_pane.minimumWidth() == 280
    assert widget.center_pane.minimumWidth() == 420
    assert widget.center_pane.minimumHeight() == 260
    assert widget.bottom_pane.minimumHeight() == 180


def test_refresh_all_views_keeps_document_cursor_and_scroll(qtbot):
    initialize_database()
    database.add_project("Refresh Editor State")
    project = database.get_all_projects()[0]
    participant_id = database.add_participant(project["id"], "Alice")
    content = "\n".join(f"line {index}" for index in range(200))
    database.add_document(project["id"], "Doc 1", content, participant_id)

    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    widget.show()

    cursor = widget.center_pane.text_edit.textCursor()
    cursor.setPosition(900)
    widget.center_pane.text_edit.setTextCursor(cursor)
    widget.center_pane.text_edit.verticalScrollBar().setValue(120)
    widget.center_pane.text_edit.setFocus()

    expected_position = widget.center_pane.text_edit.textCursor().position()
    expected_scroll = widget.center_pane.text_edit.verticalScrollBar().value()

    widget.refresh_all_views()
    qtbot.wait(10)

    assert widget.center_pane.current_document_id is not None
    assert widget.center_pane.text_edit.textCursor().position() == expected_position
    assert widget.center_pane.text_edit.verticalScrollBar().value() == expected_scroll
    assert widget.center_pane.text_edit.hasFocus()


def test_document_segment_edit_preloads_and_saves_remark(qtbot):
    initialize_database()
    database.add_project("Segment Remark UI")
    project = database.get_all_projects()[0]
    participant_id = database.add_participant(project["id"], "Alice")
    document_id = database.add_document(project["id"], "Doc 1", "alpha beta", participant_id)
    node_id = database.add_node(project["id"], "Theme", None, "#FFFF00")
    segment_id = database.add_coded_segment(document_id, node_id, participant_id, 0, 5, "alpha")
    database.update_coded_segment_remark(segment_id, "Original remark")

    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    widget.show()

    widget.center_pane.start_segment_edit_mode(segment_id, document_id, 0, 5)
    assert widget.center_pane.segment_remark_input.toPlainText() == "Original remark"

    widget.center_pane.segment_remark_input.setPlainText("Updated remark")
    widget.center_pane.save_segment_edit()

    segment = database.get_coded_segments_for_document(document_id)[0]
    assert segment["remark"] == "Updated remark"


def test_coded_segments_search_matches_remark(qtbot):
    initialize_database()
    database.add_project("Remark Search")
    project = database.get_all_projects()[0]
    participant_id = database.add_participant(project["id"], "Alice")
    document_id = database.add_document(project["id"], "Doc 1", "alpha beta", participant_id)
    node_id = database.add_node(project["id"], "Theme", None, "#FFFF00")
    segment_id = database.add_coded_segment(document_id, node_id, participant_id, 0, 5, "alpha")
    database.update_coded_segment_remark(segment_id, "follow up later")

    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    widget.show()

    widget.bottom_pane.search_scope_combo.setCurrentText("Remark")
    widget.bottom_pane.search_input.setText("follow up")

    assert widget.bottom_pane.tree_widget.topLevelItemCount() == 1
