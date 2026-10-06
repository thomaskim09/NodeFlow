from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from qt_material_icons import MaterialIcon
from services.ai_suggestion_service import AISuggestion
from utils.common import get_translation


class AISuggestionDialog(QDialog):
    def __init__(
        self,
        suggestions: list[AISuggestion],
        accept_existing_callback: Callable[[AISuggestion], bool],
        node_details: dict[int, dict[str, str]],
        language: str = "English",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.language = language
        self.suggestions = list(suggestions)
        self.accept_existing_callback = accept_existing_callback
        self.node_details = node_details
        self.setWindowTitle(get_translation("ai_suggestions.title", language))
        self.setMinimumSize(720, 520)
        self.resize(820, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(
            QLabel(get_translation("ai_suggestions.review_message", language))
        )
        self.note_label = QLabel(
            get_translation("ai_suggestions.existing_only_note", language)
        )
        self.note_label.setWordWrap(True)
        layout.addWidget(self.note_label)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.cards_layout.setSpacing(12)
        scroll_area.setWidget(self.cards_widget)
        layout.addWidget(scroll_area, 1)

        close_button = QPushButton(get_translation("ai_suggestions.close", language))
        close_button.clicked.connect(self.reject)
        layout.addWidget(close_button)
        self._render_suggestions()

    def _render_suggestions(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        if not self.suggestions:
            self.status_label.setText(
                get_translation("ai_suggestions.no_suggestions", self.language)
            )
            self.cards_layout.addStretch()
            return

        self.status_label.setText(
            get_translation(
                "ai_suggestions.suggestion_count",
                self.language,
                count=len(self.suggestions),
            )
        )
        for suggestion in self.suggestions:
            self.cards_layout.addWidget(self._create_card(suggestion))
        self.cards_layout.addStretch()

    def _create_card(self, suggestion: AISuggestion) -> QFrame:
        card = QFrame()
        card.setObjectName("aiSuggestionCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        details = self.node_details.get(suggestion.existing_node_id, {})
        node_name = details.get("name", str(suggestion.existing_node_id))
        node_color = self._safe_color(details.get("color"))

        heading = QHBoxLayout()
        heading.setSpacing(10)
        color_swatch = QLabel()
        color_swatch.setFixedSize(16, 16)
        color_swatch.setStyleSheet(
            f"background-color: {node_color}; border: 1px solid #777; "
            "border-radius: 8px;"
        )
        color_swatch.setToolTip(node_name)
        heading.addWidget(color_swatch)

        name_label = QLabel(suggestion.name)
        name_font = name_label.font()
        name_font.setBold(True)
        name_font.setPointSize(name_font.pointSize() + 1)
        name_label.setFont(name_font)
        name_label.setWordWrap(True)
        heading.addWidget(name_label, 1)
        layout.addLayout(heading)

        reason_label = QLabel(
            get_translation(
                "ai_suggestions.reason",
                self.language,
                reason=suggestion.reason,
            )
        )
        reason_label.setWordWrap(True)
        layout.addWidget(reason_label)

        match_label = QLabel(
            get_translation(
                "ai_suggestions.existing_node_match",
                self.language,
                name=node_name,
            )
        )
        match_label.setWordWrap(True)
        layout.addWidget(match_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        accept_button = self._icon_button(
            "check",
            get_translation("ai_suggestions.accept_tooltip", self.language),
            "#15803D",
        )
        accept_button.clicked.connect(
            lambda checked=False: self._apply_suggestion(suggestion)
        )
        edit_button = self._icon_button(
            "edit",
            get_translation("ai_suggestions.edit_tooltip", self.language),
            "#2563EB",
        )
        edit_button.clicked.connect(
            lambda checked=False: self._edit_suggestion(suggestion)
        )
        reject_button = self._icon_button(
            "close",
            get_translation("ai_suggestions.reject_tooltip", self.language),
            "#DC2626",
        )
        reject_button.clicked.connect(
            lambda checked=False: self._reject_suggestion(suggestion)
        )
        buttons.addWidget(accept_button)
        buttons.addWidget(edit_button)
        buttons.addWidget(reject_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        return card

    def _icon_button(
        self, icon_name: str, tooltip: str, icon_color: str
    ) -> QPushButton:
        button = QPushButton()
        icon = MaterialIcon(icon_name)
        icon.set_color(QColor(icon_color), QIcon.Mode.Normal)
        button.setIcon(icon)
        button.setIconSize(QSize(18, 18))
        button.setFixedSize(34, 34)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        return button

    @staticmethod
    def _safe_color(color: str | None) -> str:
        candidate = color or "#9CA3AF"
        return candidate if QColor(candidate).isValid() else "#9CA3AF"

    def _apply_suggestion(self, suggestion: AISuggestion) -> None:
        if self.accept_existing_callback(suggestion) is not False:
            self.suggestions.remove(suggestion)
            self._render_suggestions()

    def _edit_suggestion(self, suggestion: AISuggestion) -> None:
        new_name, accepted = QInputDialog.getText(
            self,
            get_translation("ai_suggestions.edit_name_title", self.language),
            get_translation("ai_suggestions.edit_name_prompt", self.language),
            text=suggestion.name,
        )
        if not accepted or not new_name.strip():
            return
        index = self.suggestions.index(suggestion)
        self.suggestions[index] = AISuggestion(
            name=new_name.strip(),
            reason=suggestion.reason,
            existing_node_id=suggestion.existing_node_id,
        )
        self._render_suggestions()

    def _reject_suggestion(self, suggestion: AISuggestion) -> None:
        self.suggestions.remove(suggestion)
        self._render_suggestions()
