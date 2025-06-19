import math
import networkx as nx
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QStackedWidget,
    QHBoxLayout,
    QPushButton,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsTextItem,
    QButtonGroup,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QFont


class CoOccurrenceWidget(QWidget):
    """
    A widget to display code co-occurrence data in a matrix and a graph view.
    """

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.is_dark = self.settings.get("theme") == "Dark"
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # --- Top Controls ---
        controls_layout = QHBoxLayout()
        intro_text = (
            "Visualize code relationships: the matrix shows co-occurrence counts, "
            "the graph shows connection structure."
        )
        self.intro_label = QLabel(intro_text)
        self.intro_label.setWordWrap(True)
        self.intro_label.setStyleSheet("font-size: 11pt;")
        self.intro_label.setMaximumHeight(40)
        self.intro_label.setMaximumWidth(500)
        controls_layout.addWidget(self.intro_label)
        controls_layout.addStretch()

        self.view_button_group = QButtonGroup(self)
        self.view_matrix_button = QPushButton("Matrix View")
        self.view_matrix_button.setCheckable(True)
        self.view_graph_button = QPushButton("Graph View")
        self.view_graph_button.setCheckable(True)
        self.view_button_group.addButton(self.view_matrix_button)
        self.view_button_group.addButton(self.view_graph_button)
        self.view_matrix_button.setChecked(True)

        controls_layout.addWidget(self.view_matrix_button)
        controls_layout.addWidget(self.view_graph_button)

        # --- Stacked Widget for Views ---
        self.stacked_widget = QStackedWidget()

        # --- View 1: Matrix ---
        self.matrix_view_widget = QWidget()
        matrix_layout = QVBoxLayout(self.matrix_view_widget)
        matrix_layout.setContentsMargins(0, 5, 0, 0)
        self.table_widget = QTableWidget()
        self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        matrix_layout.addWidget(self.table_widget)
        self.stacked_widget.addWidget(self.matrix_view_widget)

        # --- View 2: Graph ---
        self.graph_view = QGraphicsView()
        self.graph_view.setRenderHint(QPainter.Antialiasing)
        self.graph_scene = QGraphicsScene(self)
        self.graph_view.setScene(self.graph_scene)
        self.stacked_widget.addWidget(self.graph_view)

        self.layout.addLayout(controls_layout)
        self.layout.addWidget(self.stacked_widget)

        # --- Connections ---
        self.view_matrix_button.clicked.connect(
            lambda: self.stacked_widget.setCurrentIndex(0)
        )
        self.view_graph_button.clicked.connect(
            lambda: self.stacked_widget.setCurrentIndex(1)
        )

        self.clear_views()

    def update_data(self, matrix_data, headers):
        """
        Updates both the matrix and graph views with new data.
        """
        self._update_matrix_view(matrix_data, headers)
        self._update_graph_view(matrix_data, headers)

    def _update_matrix_view(self, matrix_data, headers):
        if not matrix_data or not headers:
            self.table_widget.clear()
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            return

        self.table_widget.setRowCount(len(headers))
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.table_widget.setVerticalHeaderLabels(headers)

        for i, h1 in enumerate(headers):
            for j, h2 in enumerate(headers):
                value = matrix_data.get(h1, {}).get(h2, 0)
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_widget.setItem(i, j, item)

        self.table_widget.resizeColumnsToContents()

    def _update_graph_view(self, matrix_data, headers):
        self.graph_scene.clear()
        if not matrix_data or not headers:
            return

        G = nx.Graph()
        node_sizes = {}
        max_weight = 0

        for node_name in headers:
            G.add_node(node_name)
            node_sizes[node_name] = matrix_data.get(node_name, {}).get(node_name, 1)

        for i, node1 in enumerate(headers):
            for j in range(i + 1, len(headers)):
                node2 = headers[j]
                weight = matrix_data.get(node1, {}).get(node2, 0)
                if weight > 0:
                    G.add_edge(node1, node2, weight=weight)
                    if weight > max_weight:
                        max_weight = weight

        # --- AMENDED LINE ---
        # Only exit if there are no nodes to draw.
        # This ensures that unconnected nodes will still be displayed.
        if not G.nodes():
            return

        pos = nx.spring_layout(
            G, k=1.5 / math.sqrt(len(G.nodes())), iterations=75, seed=42
        )
        self._scale_layout_to_view(pos)

        edge_color = QColor("#888888") if self.is_dark else QColor("#aaaaaa")
        node_color = QColor("#5b9bd5")
        text_color = QColor(Qt.white)

        # Only try to draw edges if they exist
        if G.edges():
            for edge in G.edges(data=True):
                p1 = pos[edge[0]]
                p2 = pos[edge[1]]
                thickness = 0.5 + 2.5 * (edge[2]["weight"] / max_weight)
                line = QGraphicsLineItem(p1[0], p1[1], p2[0], p2[1])
                line.setPen(QPen(edge_color, thickness))
                line.setZValue(-1)
                self.graph_scene.addItem(line)

        max_node_size = max(node_sizes.values()) if node_sizes else 1
        for node_name in G.nodes():
            p = pos[node_name]
            raw_size = node_sizes.get(node_name, 1)
            # Use log scale for better visual difference in node sizes
            log_scaled_size = math.log(raw_size + 1) / math.log(max_node_size + 1)
            node_diameter = 20 + 50 * log_scaled_size

            ellipse = QGraphicsEllipseItem(0, 0, node_diameter, node_diameter)
            ellipse.setPos(p[0] - node_diameter / 2, p[1] - node_diameter / 2)
            ellipse.setBrush(node_color)
            ellipse.setPen(QPen(Qt.NoPen))
            self.graph_scene.addItem(ellipse)

            text = QGraphicsTextItem(node_name)
            text.setFont(QFont("Arial", 9))
            text.setDefaultTextColor(text_color)
            text_rect = text.boundingRect()
            text.setPos(p[0] - text_rect.width() / 2, p[1] - text_rect.height() / 2)
            self.graph_scene.addItem(text)

    def _scale_layout_to_view(self, pos, padding=50):
        if not pos:
            return

        view_rect = self.graph_view.viewport().rect()
        # --- AMENDED CODE BLOCK ---
        # Add safety checks for small viewports and single-line/dot layouts
        if view_rect.width() <= padding or view_rect.height() <= padding:
            return  # Avoid division by zero if view is too small

        scene_width = view_rect.width() - padding
        scene_height = view_rect.height() - padding

        x_coords = [p[0] for p in pos.values()]
        y_coords = [p[1] for p in pos.values()]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        x_range = max_x - min_x
        y_range = max_y - min_y

        if x_range == 0:
            x_range = 1
        if y_range == 0:
            y_range = 1

        x_scale = scene_width / x_range
        y_scale = scene_height / y_range

        for node, (x, y) in pos.items():
            new_x = (x - min_x) * x_scale + padding / 2
            new_y = (y - min_y) * y_scale + padding / 2
            pos[node] = (new_x, new_y)

    def clear_views(self):
        self._update_matrix_view({}, [])
        self._update_graph_view({}, [])

    def get_matrix_for_export(self):
        return self.table_widget
