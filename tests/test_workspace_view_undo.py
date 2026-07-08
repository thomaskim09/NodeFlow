import database
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
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


def test_format_change_does_not_expand_coded_segment(qtbot):
    initialize_database()
    database.add_project("Format Signal")
    project = database.get_all_projects()[0]
    participant_id = database.add_participant(project["id"], "Alice")
    document_id = database.add_document(
        project["id"], "Doc 1", "alpha beta gamma", participant_id
    )
    node_id = database.add_node(project["id"], "Theme", None, "#FFFF00")
    database.add_coded_segment(document_id, node_id, participant_id, 6, 10, "beta")

    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    widget.show()

    cursor = widget.center_pane.text_edit.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(len("alpha beta gamma"), QTextCursor.MoveMode.KeepAnchor)
    fmt = QTextCharFormat()
    fmt.setBackground(QColor("#B03000"))
    cursor.mergeCharFormat(fmt)

    segment = widget.center_pane._coded_segments_cache[0]
    assert segment["segment_start"] == 6
    assert segment["segment_end"] == 10

    cursor = widget.center_pane.text_edit.textCursor()
    cursor.setPosition(8)
    widget.center_pane.text_edit.setTextCursor(cursor)
    widget.center_pane.text_edit.insertPlainText("X")

    segment = widget.center_pane._coded_segments_cache[0]
    assert segment["segment_start"] == 6
    assert segment["segment_end"] == 11
    assert segment["content_preview"] == "beXta"


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


def test_coding_selection_updates_segment_view_without_node_reload(qtbot, monkeypatch):
    initialize_database()
    database.add_project("Single Refresh")
    project = database.get_all_projects()[0]
    participant_id = database.add_participant(project["id"], "Alice")
    database.add_document(project["id"], "Doc 1", "alpha beta", participant_id)
    node_id = database.add_node(project["id"], "Theme", None, "#FFFF00")

    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    cursor = widget.center_pane.text_edit.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(5, QTextCursor.MoveMode.KeepAnchor)
    widget.center_pane.text_edit.setTextCursor(cursor)

    refreshes = {"segments": 0, "nodes": 0}
    wait_cursor_seen = []
    original_add_segment = database.add_coded_segment
    original_populate = widget.bottom_pane.populate_tree
    original_load_nodes = widget.node_tree_manager.load_nodes

    def add_segment_with_cursor(*args, **kwargs):
        wait_cursor_seen.append(QApplication.overrideCursor().shape())
        return original_add_segment(*args, **kwargs)

    def populate_once(segments):
        refreshes["segments"] += 1
        return original_populate(segments)

    def load_nodes_once(*args, **kwargs):
        refreshes["nodes"] += 1
        return original_load_nodes(*args, **kwargs)

    monkeypatch.setattr(database, "add_coded_segment", add_segment_with_cursor)
    monkeypatch.setattr(widget.bottom_pane, "populate_tree", populate_once)
    monkeypatch.setattr(widget.node_tree_manager, "load_nodes", load_nodes_once)

    widget.code_selection(node_id)

    assert refreshes == {"segments": 1, "nodes": 0}
    assert len(widget.center_pane._coded_segments_cache) == 1
    assert len(widget.center_pane._coded_segment_selections) == 1
    node_item = widget.node_tree_manager.tree_widget.topLevelItem(0)
    node_widget = widget.node_tree_manager.tree_widget.itemWidget(node_item, 0)
    participant_item = widget.participant_manager.list_widget.item(0)
    participant_widget = widget.participant_manager.list_widget.itemWidget(
        participant_item
    )
    assert node_widget.stats_label.text() == "50.0% | 1 Segments"
    assert participant_widget.stats_label.text() == "50.0% | 1 Segments"
    assert wait_cursor_seen == [Qt.CursorShape.WaitCursor]
    assert QApplication.overrideCursor() is None

    widget.undo_workspace_action()

    assert refreshes["nodes"] == 0
    assert node_widget.stats_label.text() == ""
    assert participant_widget.stats_label.text() == ""


def test_project_open_and_document_switch_refresh_views_once(qtbot, monkeypatch):
    initialize_database()
    database.add_project("Single Switch Refresh")
    project = database.get_all_projects()[0]
    participant_id = database.add_participant(project["id"], "Alice")
    database.add_document(project["id"], "Doc 1", "alpha", participant_id)
    database.add_document(project["id"], "Doc 2", "beta", participant_id)

    from ui.workspace.coded_segments_view import CodedSegmentsView
    from ui.workspace.node_tree_manager import NodeTreeManager
    from ui.workspace.participant_manager import ParticipantManager

    opens = {"segments": 0, "nodes": 0, "participants": 0}
    original_load_segments = CodedSegmentsView.load_segments
    original_load_nodes_for_open = NodeTreeManager.load_nodes
    original_load_participants = ParticipantManager.load_participants

    def load_segments_once(self, *args, **kwargs):
        opens["segments"] += 1
        return original_load_segments(self, *args, **kwargs)

    def load_participants_once(self, *args, **kwargs):
        opens["participants"] += 1
        return original_load_participants(self, *args, **kwargs)

    def load_nodes_for_open_once(self, *args, **kwargs):
        opens["nodes"] += 1
        return original_load_nodes_for_open(self, *args, **kwargs)

    monkeypatch.setattr(CodedSegmentsView, "load_segments", load_segments_once)
    monkeypatch.setattr(NodeTreeManager, "load_nodes", load_nodes_for_open_once)
    monkeypatch.setattr(ParticipantManager, "load_participants", load_participants_once)

    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)

    assert opens == {"segments": 1, "nodes": 1, "participants": 1}

    refreshes = {"segments": 0, "nodes": 0, "participants": 0}
    original_populate = widget.bottom_pane.populate_tree
    original_load_nodes = widget.node_tree_manager.load_nodes

    def populate_once(segments):
        refreshes["segments"] += 1
        return original_populate(segments)

    def load_nodes_once(*args, **kwargs):
        refreshes["nodes"] += 1
        return original_load_nodes(*args, **kwargs)

    def count_participants(*args, **kwargs):
        refreshes["participants"] += 1
        return original_load_participants(widget.participant_manager, *args, **kwargs)

    monkeypatch.setattr(widget.bottom_pane, "populate_tree", populate_once)
    monkeypatch.setattr(widget.node_tree_manager, "load_nodes", load_nodes_once)
    monkeypatch.setattr(widget.participant_manager, "load_participants", count_participants)
    widget.bottom_pane.search_input.setText("alpha")
    refreshes["segments"] = 0

    widget.center_pane.doc_selector.setCurrentIndex(1)

    assert refreshes == {"segments": 1, "nodes": 1, "participants": 1}


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
