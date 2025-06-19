from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from wordcloud import WordCloud
import io
import os
from collections import Counter


class WordCloudWidget(QWidget):
    """A widget to generate and display a word cloud from node frequencies."""

    def __init__(self, theme_settings, parent=None):
        super().__init__(parent)
        self.settings = theme_settings
        self.is_dark = self.settings.get("theme") == "Dark"
        self._original_pixmap = None

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

    def update_wordcloud(self, segments):
        """Synchronously generate and display the word cloud."""
        self.message_label.setText("Generating word cloud, please wait...")
        self.message_label.setVisible(True)
        self.image_label.setVisible(False)
        QApplication.processEvents()

        # Synchronous word cloud generation
        try:
            node_names = [
                seg["node_name"]
                for seg in segments
                if "node_name" in seg and seg["node_name"]
            ]
            if not node_names:
                self.display_wordcloud(
                    QPixmap(), "No codes have been applied in the current scope."
                )
                return
            frequencies = Counter(node_names)
            bg_color = "#2c2c2c" if self.is_dark else "white"
            font_path = None
            if any(ord(char) > 127 for word in frequencies for char in word):
                font_path = self._find_cjk_font()
                if not font_path:
                    self.display_wordcloud(
                        QPixmap(),
                        "Could not find a suitable font for special characters.",
                    )
                    return
            colormap = "Pastel1" if self.is_dark else "viridis"
            wc_object = WordCloud(
                font_path=font_path,
                background_color=bg_color,
                max_words=150,
                width=1000,
                height=600,
                colormap=colormap,
                random_state=42,
                prefer_horizontal=1,
            )
            wc = wc_object.generate_from_frequencies(frequencies)
            pil_image = wc.to_image()
            buffer = io.BytesIO()
            pil_image.save(buffer, format="PNG")
            qt_image = QImage.fromData(buffer.getvalue())
            pixmap = QPixmap.fromImage(qt_image)
            self.display_wordcloud(pixmap, "")
        except Exception as e:
            import traceback

            traceback.print_exc()
            self.display_wordcloud(QPixmap(), f"An error occurred:\n{e}")

    def _find_cjk_font(self):
        if os.name == "nt":
            paths = [
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/malgun.ttf",
            ]
        else:
            paths = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti.ttf",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
            ]
        for path in paths:
            if os.path.exists(path):
                return path
        return None

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
        self.image_label.setText("Calculating...")
