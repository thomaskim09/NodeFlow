from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter, QPalette, QPen
from PySide6.QtWidgets import QComboBox


class FitPopupComboBox(QComboBox):
    """Keeps the popup width aligned with the combo field."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumContentsLength(1)

    def showPopup(self):
        super().showPopup()
        QTimer.singleShot(0, self._sync_popup_width)

    def _sync_popup_width(self):
        popup = self.view().window()
        popup.setMinimumWidth(self.width())
        popup.setMaximumWidth(self.width())
        popup.resize(self.width(), popup.height())

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        arrow_color = self.palette().color(QPalette.ColorRole.Text)
        if not self.isEnabled():
            arrow_color = self.palette().color(QPalette.ColorRole.Mid)
        pen = QPen(
            arrow_color,
            1.6,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        center_x = self.width() - 12
        center_y = self.height() // 2 + 1
        painter.drawLine(center_x - 4, center_y - 2, center_x, center_y + 2)
        painter.drawLine(center_x, center_y + 2, center_x + 4, center_y - 2)
