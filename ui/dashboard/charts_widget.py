# Create this new file at: ui/dashboard/charts_widget.py

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


class ChartsWidget(QWidget):
    """A widget to display bar and pie charts for the dashboard."""

    def __init__(self, theme_settings, parent=None):
        super().__init__(parent)
        self.settings = theme_settings

        layout = QHBoxLayout(self)
        self.bar_chart_view = QChartView()
        self.pie_chart_view = QChartView()
        layout.addWidget(self.bar_chart_view)
        layout.addWidget(self.pie_chart_view)

    def update_charts(self, root_nodes_data):
        """Public method to update both charts with new data."""
        self._create_bar_chart(root_nodes_data)
        self._create_pie_chart(root_nodes_data)

    def _apply_theme_to_chart(self, chart):
        is_dark = self.settings.get("theme") == "Dark"
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
        bar_set = QBarSet("Word Count %")
        categories = []
        for node_name, percentage, _, _ in sorted(
            root_nodes_data, key=lambda x: x[1], reverse=True
        ):
            bar_set.append(percentage)
            categories.append(
                node_name[:15] + "..." if len(node_name) > 15 else node_name
            )
        series.append(bar_set)

        chart = QChart(title="Code Distribution (Bar)")
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.1f%%")

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        chart.legend().setVisible(False)

        self._apply_theme_to_chart(chart)
        self.bar_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.bar_chart_view.setChart(chart)

    def _create_pie_chart(self, root_nodes_data):
        series = QPieSeries()
        series.setHoleSize(0.35)

        is_dark = self.settings.get("theme") == "Dark"
        label_color = QColor("white") if is_dark else QColor("black")
        pie_colors = [
            "#1f77b4",
            "#ff7f0e",
            "#2ca02c",
            "#d62728",
            "#9467bd",
            "#8c564b",
            "#e377c2",
        ]

        sorted_data = sorted(root_nodes_data, key=lambda x: x[1], reverse=True)
        main_slices = sorted_data[:6]
        other_percentage = sum(item[1] for item in sorted_data[6:])

        for i, (name, p, _, _) in enumerate(main_slices):
            if p > 0.1:
                slice_ = QPieSlice(f"{name} {p:.1f}%", p)
                slice_.setLabelVisible()
                slice_.setLabelBrush(label_color)
                slice_.setBrush(QColor(pie_colors[i % len(pie_colors)]))
                series.append(slice_)

        if other_percentage > 0.1:
            slice_ = QPieSlice(f"Other {other_percentage:.1f}%", other_percentage)
            slice_.setLabelVisible()
            slice_.setLabelBrush(label_color)
            slice_.setBrush(QColor(pie_colors[6 % len(pie_colors)]))
            series.append(slice_)

        chart = QChart(title="Code Distribution (Pie)")
        chart.addSeries(series)
        self._apply_theme_to_chart(chart)
        chart.legend().setVisible(False)

        self.pie_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.pie_chart_view.setChart(chart)
