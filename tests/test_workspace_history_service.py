from services.workspace_history_service import WorkspaceCommand, WorkspaceHistory


def test_workspace_history_undo_redo_and_redo_clear():
    values = []
    history = WorkspaceHistory(max_depth=10)

    history.execute(
        WorkspaceCommand("Add A", lambda: values.append("a"), lambda: values.pop())
    )
    history.execute(
        WorkspaceCommand("Add B", lambda: values.append("b"), lambda: values.pop())
    )

    assert values == ["a", "b"]
    assert history.next_undo_label() == "Add B"

    history.undo()
    assert values == ["a"]
    assert history.can_redo()

    history.execute(
        WorkspaceCommand("Add C", lambda: values.append("c"), lambda: values.pop())
    )
    assert values == ["a", "c"]
    assert not history.can_redo()


def test_workspace_history_trims_to_max_depth():
    values = []
    history = WorkspaceHistory(max_depth=2)

    for value in ("a", "b", "c"):
        history.execute(
            WorkspaceCommand(
                f"Add {value}",
                lambda value=value: values.append(value),
                lambda: values.pop(),
            )
        )

    assert [command.label for command in history.undo_stack] == ["Add b", "Add c"]

    history.undo()
    history.undo()
    assert values == ["a"]
    assert not history.can_undo()
