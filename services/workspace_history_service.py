from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class WorkspaceCommand:
    label: str
    do: Callable[[], None]
    undo: Callable[[], None]
    after_refresh: Callable[[], None] = field(default=lambda: None)


class WorkspaceHistory:
    def __init__(self, max_depth: int = 100):
        self.undo_stack: list[WorkspaceCommand] = []
        self.redo_stack: list[WorkspaceCommand] = []
        self.max_depth = max_depth
        self._callbacks: list[Callable[[], None]] = []

    def add_changed_callback(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def set_max_depth(self, max_depth: int) -> None:
        self.max_depth = max(1, max_depth)
        self._trim()
        self._notify_changed()

    def execute(self, command: WorkspaceCommand) -> None:
        command.do()
        self._push_applied(command)
        command.after_refresh()

    def record_applied(self, command: WorkspaceCommand) -> None:
        self._push_applied(command)
        self._notify_changed()

    def undo(self) -> None:
        if not self.undo_stack:
            return
        command = self.undo_stack.pop()
        command.undo()
        self.redo_stack.append(command)
        command.after_refresh()
        self._notify_changed()

    def redo(self) -> None:
        if not self.redo_stack:
            return
        command = self.redo_stack.pop()
        command.do()
        self.undo_stack.append(command)
        command.after_refresh()
        self._notify_changed()

    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    def can_redo(self) -> bool:
        return bool(self.redo_stack)

    def next_undo_label(self) -> str | None:
        return self.undo_stack[-1].label if self.undo_stack else None

    def next_redo_label(self) -> str | None:
        return self.redo_stack[-1].label if self.redo_stack else None

    def _push_applied(self, command: WorkspaceCommand) -> None:
        self.undo_stack.append(command)
        self.redo_stack.clear()
        self._trim()
        self._notify_changed()

    def _trim(self) -> None:
        if len(self.undo_stack) > self.max_depth:
            del self.undo_stack[: len(self.undo_stack) - self.max_depth]

    def _notify_changed(self) -> None:
        for callback in self._callbacks:
            callback()
