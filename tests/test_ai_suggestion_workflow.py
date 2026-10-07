import database
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QCursor, QEnterEvent, QTextCursor
from PySide6.QtWidgets import QLineEdit, QPushButton, QMessageBox
from repositories.base import initialize_database
from services.ai_suggestion_service import AISuggestion
from ui.workspace.ai_suggestion_dialog import AISuggestionDialog
from ui.workspace import content_view as content_view_module
from ui.workspace.content_view import InstantToolTipButton
from ui.workspace.workspace_view import WorkspaceView


def _workspace_fixture():
    initialize_database()
    database.add_project("AI Workflow")
    project = database.get_all_projects()[0]
    participant_id = database.add_participant(project["id"], "Alice")
    document_id = database.add_document(
        project["id"], "Interview", "alpha beta", participant_id
    )
    existing_node_id = database.add_node(
        project["id"], "Existing Theme", None, "#FFFF00"
    )
    return project, participant_id, document_id, existing_node_id


def _select_alpha(widget):
    cursor = widget.center_pane.text_edit.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(5, QTextCursor.MoveMode.KeepAnchor)
    widget.center_pane.text_edit.setTextCursor(cursor)
    return widget._capture_ai_selection()


def test_rejecting_all_suggestions_does_not_change_database(qtbot):
    project, _, document_id, existing_node_id = _workspace_fixture()
    suggestion = AISuggestion("Temporary", "Review me", existing_node_id)
    before_nodes = database.get_nodes_for_project(project["id"])
    before_segments = database.get_coded_segments_for_document(document_id)
    dialog = AISuggestionDialog(
        [suggestion],
        lambda item: True,
        {existing_node_id: {"name": "Existing Theme", "color": "#FFFF00"}},
        parent=None,
    )
    qtbot.addWidget(dialog)

    card = dialog.cards_layout.itemAt(0).widget()
    assert len(card.findChildren(QPushButton)) == 3
    assert any("#FFFF00" in label.styleSheet() for label in card.findChildren(type(dialog.status_label)))

    dialog._reject_suggestion(suggestion)

    assert dialog.suggestions == []
    assert database.get_nodes_for_project(project["id"]) == before_nodes
    assert database.get_coded_segments_for_document(document_id) == before_segments
    dialog.close()


def test_new_suggestion_is_editable_and_rejection_is_not_persisted(qtbot):
    project, _, document_id, _ = _workspace_fixture()
    suggestion = AISuggestion("Temporary New Code", "Review me", None)
    before_nodes = database.get_nodes_for_project(project["id"])
    before_segments = database.get_coded_segments_for_document(document_id)
    captured_names = []
    dialog = AISuggestionDialog(
        [suggestion],
        lambda item: True,
        {},
        parent=None,
        create_new_callback=lambda item, name: captured_names.append(name) or True,
    )
    qtbot.addWidget(dialog)

    card = dialog.cards_layout.itemAt(0).widget()
    editor = card.findChild(QLineEdit)
    assert editor is not None
    assert any("New Code Suggestion" in label.text() for label in card.findChildren(type(dialog.status_label)))
    editor.setText("Edited New Code")
    assert len(card.findChildren(QPushButton)) == 2
    dialog._create_new_suggestion(suggestion, editor.text())
    assert captured_names == ["Edited New Code"]

    assert dialog.suggestions == []
    assert database.get_nodes_for_project(project["id"]) == before_nodes
    assert database.get_coded_segments_for_document(document_id) == before_segments
    dialog.close()


def test_ai_button_requires_selected_text(qtbot):
    project, _, _, _ = _workspace_fixture()
    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    assert not widget.center_pane.ai_suggestions_button.isEnabled()
    assert not widget.center_pane.ai_suggestions_icon.isNull()
    _select_alpha(widget)
    qtbot.wait(10)
    assert widget.center_pane.ai_suggestions_button.isEnabled()

    cursor = widget.center_pane.text_edit.textCursor()
    cursor.setPosition(cursor.selectionEnd(), QTextCursor.MoveMode.MoveAnchor)
    widget.center_pane.text_edit.setTextCursor(cursor)
    qtbot.wait(10)
    assert not widget.center_pane.ai_suggestions_button.isEnabled()


def test_tooltip_button_anchors_to_cursor(monkeypatch, qtbot):
    button = InstantToolTipButton()
    qtbot.addWidget(button)
    button.setToolTip("AI suggestions")
    captured = {}

    class TooltipSpy:
        @staticmethod
        def showText(position, text, widget, rect):
            captured.update(position=position, text=text, widget=widget, rect=rect)

        @staticmethod
        def hideText():
            pass

    monkeypatch.setattr(content_view_module, "QToolTip", TooltipSpy)
    expected_position = QCursor.pos() + QPoint(12, 16)
    position = QPointF(1, 1)
    button.enterEvent(QEnterEvent(position, position, position))

    assert captured == {
        "position": expected_position,
        "text": "AI suggestions",
        "widget": button,
        "rect": button.rect(),
    }


def test_ai_progress_dialog_is_indeterminate_and_closes(qtbot):
    project, _, _, _ = _workspace_fixture()
    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)

    widget._show_ai_progress_dialog()
    qtbot.wait(10)

    assert widget._ai_progress_dialog is not None
    assert widget._ai_progress_dialog.minimum() == 0
    assert widget._ai_progress_dialog.maximum() == 0
    assert widget._ai_progress_dialog.isVisible()

    widget._close_ai_progress_dialog()
    widget.close()
    qtbot.wait(10)
    assert widget._ai_progress_dialog is None


def test_accepting_existing_node_creates_undoable_coded_segment(qtbot):
    project, participant_id, document_id, existing_node_id = _workspace_fixture()
    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    selection = _select_alpha(widget)
    suggestion = AISuggestion("Existing Theme", "Matches", existing_node_id)

    assert widget._accept_ai_existing_suggestion(suggestion, selection)
    segments = database.get_coded_segments_for_document(document_id)
    assert len(segments) == 1
    assert segments[0]["node_id"] == existing_node_id
    assert segments[0]["participant_id"] == participant_id

    widget.history.undo()
    assert database.get_coded_segments_for_document(document_id) == []
    widget.history.redo()
    assert len(database.get_coded_segments_for_document(document_id)) == 1


def test_create_and_code_new_node_is_atomic_and_undoable(qtbot):
    project, participant_id, document_id, _ = _workspace_fixture()
    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    selection = _select_alpha(widget)
    suggestion = AISuggestion("New Theme", "Matches", None)

    assert widget._create_ai_new_suggestion(suggestion, "Edited Theme", selection)
    nodes = database.get_nodes_for_project(project["id"])
    segments = database.get_coded_segments_for_document(document_id)
    created = next(node for node in nodes if node["name"] == "Edited Theme")
    assert created["parent_id"] is None
    assert len(segments) == 1
    assert segments[0]["node_id"] == created["id"]
    assert segments[0]["participant_id"] == participant_id

    widget.history.undo()
    remaining_nodes = database.get_nodes_for_project(project["id"])
    assert [node["name"] for node in remaining_nodes] == ["Existing Theme"]
    assert database.get_coded_segments_for_document(document_id) == []
    widget.history.redo()
    assert len(database.get_nodes_for_project(project["id"])) == 2
    assert len(database.get_coded_segments_for_document(document_id)) == 1


def test_same_name_requires_confirmation_and_can_use_existing_node(qtbot, monkeypatch):
    project, _, document_id, existing_node_id = _workspace_fixture()
    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    selection = _select_alpha(widget)
    suggestion = AISuggestion("New Theme", "Matches", None)

    monkeypatch.setattr(widget, "_confirm_use_existing_node", lambda name: False)
    assert not widget._create_ai_new_suggestion(suggestion, "existing theme", selection)
    assert database.get_coded_segments_for_document(document_id) == []

    monkeypatch.setattr(widget, "_confirm_use_existing_node", lambda name: True)
    assert widget._create_ai_new_suggestion(suggestion, "existing theme", selection)
    segments = database.get_coded_segments_for_document(document_id)
    assert len(segments) == 1
    assert segments[0]["node_id"] == existing_node_id


def test_participant_change_blocks_both_ai_acceptance_paths(qtbot, monkeypatch):
    project, _, document_id, existing_node_id = _workspace_fixture()
    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    selection = _select_alpha(widget)
    widget.center_pane.current_participant_id = None
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)

    assert not widget._accept_ai_existing_suggestion(
        AISuggestion("Existing", "Matches", existing_node_id), selection
    )
    assert not widget._create_ai_new_suggestion(
        AISuggestion("New", "Matches", None), "New", selection
    )
    assert database.get_coded_segments_for_document(document_id) == []


def test_document_change_blocks_new_node_creation(qtbot, monkeypatch):
    project, _, document_id, _ = _workspace_fixture()
    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    selection = _select_alpha(widget)
    widget.center_pane.text_edit.insertPlainText(" changed")
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)

    assert not widget._create_ai_new_suggestion(
        AISuggestion("New", "Matches", None), "New", selection
    )
    remaining_nodes = database.get_nodes_for_project(project["id"])
    assert [node["name"] for node in remaining_nodes] == ["Existing Theme"]
    assert database.get_coded_segments_for_document(document_id) == []


def test_new_node_rolls_back_when_segment_creation_fails(qtbot, monkeypatch):
    project, _, document_id, _ = _workspace_fixture()
    widget = WorkspaceView(project["id"], project["name"], lambda: None)
    qtbot.addWidget(widget)
    selection = _select_alpha(widget)
    monkeypatch.setattr(
        "ui.workspace.workspace_view.database.add_coded_segment",
        lambda *args: (_ for _ in ()).throw(RuntimeError("segment failed")),
    )
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)

    assert not widget._create_ai_new_suggestion(
        AISuggestion("New", "Matches", None), "New", selection
    )
    remaining_nodes = database.get_nodes_for_project(project["id"])
    assert [node["name"] for node in remaining_nodes] == ["Existing Theme"]
    assert database.get_coded_segments_for_document(document_id) == []
