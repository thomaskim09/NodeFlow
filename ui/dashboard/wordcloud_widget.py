from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from wordcloud import WordCloud
import io
from collections import Counter
from utils.common import get_translation
from services.platform_service import platform_service
from services.worker_service import TaskThread


class WordCloudWidget(QWidget):
    """A widget to generate and display a word cloud from node frequencies."""

    def __init__(self, theme_settings, parent=None, language=None):
        super().__init__(parent)
        self.settings = theme_settings
        self.language = language or self.settings.get("language", "English")
        self.is_dark = self.settings.get("theme") == "Dark"
        self._original_pixmap = None
        self._worker = None

        layout = QVBoxLayout(self)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        self.message_label = QLabel()
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        self.image_label.setVisible(False)
        self.message_label.setVisible(True)

    def update_language(self, new_language):
        self.language = new_language
        # Update any static message text if needed

    def update_wordcloud(self, segments):
        """Generate and display the word cloud without blocking the UI."""
        self.message_label.setText(
            get_translation("wordcloud.generating", self.language)
        )
        self.message_label.setVisible(True)
        self.image_label.setVisible(False)
        self._worker = TaskThread(self._build_wordcloud_payload, segments, self.is_dark)
        self._worker.succeeded.connect(self._on_wordcloud_ready)
        self._worker.failed.connect(self._on_wordcloud_failed)
        self._worker.start()

    @staticmethod
    def _build_wordcloud_payload(segments, is_dark):
        node_names = [
            seg["node_name"]
            for seg in segments
            if "node_name" in seg and seg["node_name"]
        ]
        if not node_names:
            return {"message_key": "wordcloud.no_codes", "png_bytes": None}
        frequencies = Counter(node_names)
        font_path = None
        if any(ord(char) > 127 for word in frequencies for char in word):
            font_path = platform_service.resolve_cjk_font()
            if not font_path:
                return {"message_key": "wordcloud.font_error", "png_bytes": None}
        wc_object = WordCloud(
            font_path=font_path,
            background_color="#2c2c2c" if is_dark else "white",
            max_words=150,
            width=1000,
            height=600,
            colormap="Pastel1" if is_dark else "viridis",
            random_state=42,
            prefer_horizontal=1,
        )
        image = wc_object.generate_from_frequencies(frequencies).to_image()
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return {"message_key": None, "png_bytes": buffer.getvalue()}

    def _on_wordcloud_ready(self, payload):
        if payload["message_key"]:
            self.display_wordcloud(
                QPixmap(), get_translation(payload["message_key"], self.language)
            )
            return
        image = QImage.fromData(payload["png_bytes"])
        self.display_wordcloud(QPixmap.fromImage(image), "")

    def _on_wordcloud_failed(self, error_tuple):
        _, error, _ = error_tuple
        self.display_wordcloud(
            QPixmap(),
            get_translation("wordcloud.error", self.language, error=str(error)),
        )

    def display_wordcloud(self, pixmap, message):
        if pixmap.isNull() or not pixmap:
            self.message_label.setText(message)
            self.message_label.setVisible(True)
            self.image_label.setVisible(False)
            self._original_pixmap = None
        else:
            self._original_pixmap = pixmap
            self.message_label.setVisible(False)
            self.image_label.setVisible(True)
            self._update_scaled_pixmap()

    def _update_scaled_pixmap(self):
        if self._original_pixmap:
            self.image_label.setPixmap(
                self._original_pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def resizeEvent(self, event):
        self._update_scaled_pixmap()
        super().resizeEvent(event)

    def clear_wordcloud(self):
        self.image_label.clear()
        self.image_label.setText(
            get_translation("wordcloud.calculating", self.language)
        )
