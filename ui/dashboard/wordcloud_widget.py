from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QObject, Signal, QRunnable, QThreadPool
from wordcloud import WordCloud
import io
import os
from collections import Counter
import traceback


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""

    result = Signal(QPixmap, str)


class WordCloudWorker(QRunnable):
    """Worker thread for generating the word cloud asynchronously."""

    def __init__(self, segments, is_dark):
        super().__init__()
        self.segments = segments
        self.is_dark = is_dark
        self.signals = WorkerSignals()

    def _find_cjk_font(self):
        """Tries to find a common CJK font on the user's system."""
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

    def run(self):
        """The main work task, executed in a separate thread."""
        try:
            node_names = [
                seg["node_name"]
                for seg in self.segments
                if "node_name" in seg and seg["node_name"]
            ]

            if not node_names:
                self.signals.result.emit(
                    QPixmap(), "No codes have been applied in the current scope."
                )
                return

            frequencies = Counter(node_names)
            bg_color = "#2c2c2c" if self.is_dark else "white"
            font_path = None

            if any(ord(char) > 127 for word in frequencies for char in word):
                font_path = self._find_cjk_font()
                if not font_path:
                    self.signals.result.emit(
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

            self.signals.result.emit(pixmap, "")

        except Exception as e:
            traceback.print_exc()
            self.signals.result.emit(QPixmap(), f"An error occurred:\n{e}")


class WordCloudWidget(QWidget):
    """A widget to generate and display a word cloud from node frequencies."""

    def __init__(self, theme_settings, parent=None):
        super().__init__(parent)
        self.settings = theme_settings
        self.is_dark = self.settings.get("theme") == "Dark"
        self._original_pixmap = None
        self.threadpool = QThreadPool()

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
        """Kicks off the asynchronous generation of the word cloud."""
        self.message_label.setText("Generating word cloud, please wait...")
        self.message_label.setVisible(True)
        self.image_label.setVisible(False)
        QApplication.processEvents()

        worker = WordCloudWorker(segments, self.is_dark)
        worker.signals.result.connect(self.display_wordcloud)
        self.threadpool.start(worker)

    def display_wordcloud(self, pixmap, message):
        """Slot to display the result from the worker thread."""
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
        """Scales the original pixmap to fit the current label size."""
        if self._original_pixmap:
            self.image_label.setPixmap(
                self._original_pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def resizeEvent(self, event):
        """Handles widget resizing to ensure the image scales properly."""
        self._update_scaled_pixmap()
        super().resizeEvent(event)

    def clear_wordcloud(self):
        """Clears the word cloud image."""
        self.image_label.clear()
        self.image_label.setText("Calculating...")
