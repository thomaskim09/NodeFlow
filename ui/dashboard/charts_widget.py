from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QBarSeries,
    QBarSet,
    QValueAxis,
    QBarCategoryAxis,
    QPieSeries,
    QPieSlice,
)
from utils.common import get_translation


class ChartsWidget(QWidget):
    """A widget to display bar and pie charts for the dashboard."""

    def __init__(self, theme_settings, parent=None, language=None):
        super().__init__(parent)
        self.settings = theme_settings
        self.language = language or self.settings.get("language", "English")
        self.theme = self.settings.get("theme", "Default")
        self._last_root_nodes_data = []
        layout = QHBoxLayout(self)
        self.bar_chart_view = QChartView()
        self.pie_chart_view = QChartView()
        self.bar_chart_view.setObjectName("dashboardBarChartView")
        self.pie_chart_view.setObjectName("dashboardPieChartView")
        layout.addWidget(self.bar_chart_view)
        layout.addWidget(self.pie_chart_view)

    def update_charts(self, root_nodes_data):
        """Public method to update both charts with new data."""
        self._last_root_nodes_data = list(root_nodes_data)
        self._create_bar_chart(root_nodes_data)
        self._create_pie_chart(root_nodes_data)

    def _apply_theme_to_chart(self, chart):
        is_dark = self.theme == "Dark"
        bg_color = QColor("#2E2E2E") if is_dark else QColor("#FFFFFF")
        text_color = QColor("#F0F0F0") if is_dark else QColor("#333333")
        grid_color = QColor("#4A4A4A") if is_dark else QColor("#DCDCDC")

        chart.setBackgroundBrush(bg_color)
        chart.setTitleBrush(text_color)
        for axis in chart.axes():
            axis.setLabelsBrush(text_color)
            axis.setTitleBrush(text_color)
            axis.setGridLineColor(grid_color)
        chart.legend().setLabelColor(text_color)

    def _create_bar_chart(self, root_nodes_data):
        series = QBarSeries()
        sorted_data = sorted(root_nodes_data, key=lambda x: x[1], reverse=True)
        categories = []
        for i, (node_name, percentage, _, _, node_color) in enumerate(sorted_data):
            bar_set = QBarSet(
                node_name[:15] + "..." if len(node_name) > 15 else node_name
            )
            bar_set.append(percentage)
            bar_set.setColor(QColor(node_color))  # Use the node's color
            series.append(bar_set)
            categories.append(bar_set.label())

        chart = QChart(
            title=get_translation("charts.code_distribution_bar", self.language)
        )
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        axis_x = QBarCategoryAxis()
        axis_x.append([""])
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.1f%%")

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

        self._apply_theme_to_chart(chart)
        self.bar_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.bar_chart_view.setChart(chart)

    def _create_pie_chart(self, root_nodes_data):
        series = QPieSeries()
        series.setHoleSize(0.35)

        is_dark = self.theme == "Dark"
        label_color = QColor("white") if is_dark else QColor("black")
        # Keep a small preset color list for the 'Other' slice
        other_slice_color = "#e377c2"

        sorted_data = sorted(root_nodes_data, key=lambda x: x[1], reverse=True)
        main_slices = sorted_data[:6]
        other_percentage = sum(item[1] for item in sorted_data[6:])

        for i, (name, p, _, _, color) in enumerate(main_slices):
            if p > 0.1:
                slice_ = QPieSlice(f"{name} {p:.1f}%", p)
                slice_.setLabelVisible()
                slice_.setLabelBrush(label_color)
                slice_.setBrush(QColor(color))  # Use the node's color
                series.append(slice_)

        if other_percentage > 0.1:
            slice_ = QPieSlice(
                get_translation("charts.other", self.language)
                + f" {other_percentage:.1f}%",
                other_percentage,
            )
            slice_.setLabelVisible()
            slice_.setLabelBrush(label_color)
            slice_.setBrush(QColor(other_slice_color))
            series.append(slice_)

        chart = QChart(
            title=get_translation("charts.code_distribution_pie", self.language)
        )
        chart.addSeries(series)
        self._apply_theme_to_chart(chart)
        chart.legend().setVisible(False)

        self.pie_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.pie_chart_view.setChart(chart)

    def clear_charts(self):
        bar_chart = self.bar_chart_view.chart()
        if bar_chart is not None:
            for series in list(bar_chart.series()):
                bar_chart.removeSeries(series)
        pie_chart = self.pie_chart_view.chart()
        if pie_chart is not None:
            for series in list(pie_chart.series()):
                pie_chart.removeSeries(series)
        self.bar_chart_view.setChart(QChart())
        self.pie_chart_view.setChart(QChart())

    def set_theme(self, theme: str):
        self.theme = theme
        # Keep chart views aligned with dashboard panel in both themes.
        if theme == "Dark":
            self.bar_chart_view.setStyleSheet("background-color: #1f1f1f; border: none;")
            self.pie_chart_view.setStyleSheet("background-color: #1f1f1f; border: none;")
        else:
            self.bar_chart_view.setStyleSheet("background-color: #ffffff; border: none;")
            self.pie_chart_view.setStyleSheet("background-color: #ffffff; border: none;")
        if self._last_root_nodes_data:
            self.update_charts(self._last_root_nodes_data)

    def update_language(self, new_language):
        self.language = new_language
        if self._last_root_nodes_data:
            self.update_charts(self._last_root_nodes_data)
