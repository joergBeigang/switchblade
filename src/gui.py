"""
gui module
"""

from PySide6.QtWidgets import (
    QWidget,
    QGraphicsView,
    QGraphicsScene,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QSlider,
    QDoubleSpinBox,
    QPushButton,
    QCheckBox,
    QGroupBox,
    QSizePolicy,
)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPalette

# from PySide6.QtSvg import QGraphicsSvgItem
import serial.tools.list_ports

# import copy
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray

# from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtSvgWidgets import QGraphicsSvgItem

# from PySide6.QtWidgets import QGraphicsPixmapItem
from settings import SettingsManager
import plot
import gui


def build_gui(parent):
    # ---- Central widget ----
    central = QWidget()
    parent.setCentralWidget(central)

    main_layout = QHBoxLayout(central)
    main_layout.setContentsMargins(4, 4, 4, 4)
    main_layout.setSpacing(6)

    # =========================
    # Left control panel
    # =========================
    left_panel = QWidget()
    left_panel.setMinimumWidth(260)
    left_panel.setMaximumWidth(360)
    left_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    left_layout = QVBoxLayout(left_panel)
    left_layout.setSpacing(8)

    # --- Port dropdown ---
    left_layout.addWidget(QLabel("Port"))
    parent.port_combo = QComboBox()
    parent.port_combo.addItems(["/dev/ttyUSB0", "/dev/ttyUSB1"])
    left_layout.addWidget(parent.port_combo)

    # --- Baud rate dropdown ---
    left_layout.addWidget(QLabel("Baud rate"))
    parent.baud_combo = QComboBox()
    parent.baud_combo.addItems(["9600", "19200", "38400", "115200"])
    parent.baud_combo.setCurrentText("9600")
    left_layout.addWidget(parent.baud_combo)

    # --- Speed group ---
    speed_group = QGroupBox("Speed")
    speed_layout = QVBoxLayout(speed_group)

    speed_top = QHBoxLayout()
    speed_top.addWidget(QLabel("Speed"))
    parent.speed_spin = QSpinBox()
    parent.speed_spin.setRange(1, 200)
    parent.speed_spin.setValue(40)
    speed_top.addWidget(parent.speed_spin)
    speed_layout.addLayout(speed_top)

    parent.speed_slider = QSlider(Qt.Horizontal)
    parent.speed_slider.setRange(1, 200)
    parent.speed_slider.setValue(40)
    speed_layout.addWidget(parent.speed_slider)

    left_layout.addWidget(speed_group)
    # Speed two-way connection
    parent.speed_spin.valueChanged.connect(parent.speed_slider.setValue)
    parent.speed_slider.valueChanged.connect(parent.speed_spin.setValue)

    # --- Pressure group ---
    pressure_group = QGroupBox("Pressure")
    pressure_layout = QVBoxLayout(pressure_group)

    pressure_top = QHBoxLayout()
    pressure_top.addWidget(QLabel("Force"))
    parent.pressure_spin = QSpinBox()
    parent.pressure_spin.setRange(1, 200)
    parent.pressure_spin.setValue(80)
    pressure_top.addWidget(parent.pressure_spin)
    pressure_layout.addLayout(pressure_top)

    parent.pressure_slider = QSlider(Qt.Horizontal)
    parent.pressure_slider.setRange(1, 200)
    parent.pressure_slider.setValue(80)
    pressure_layout.addWidget(parent.pressure_slider)

    left_layout.addWidget(pressure_group)
    parent.pressure_spin.valueChanged.connect(parent.pressure_slider.setValue)
    parent.pressure_slider.valueChanged.connect(parent.pressure_spin.setValue)

    # --- Offset group ---
    offset_group = QGroupBox("Offset")
    offset_layout = QVBoxLayout(offset_group)

    offset_top = QHBoxLayout()
    offset_top.addWidget(QLabel("Knife Offset"))
    parent.offset_spin = QDoubleSpinBox()
    parent.offset_spin.setRange(0, 2)
    parent.offset_spin.setValue(0.2)
    parent.offset_spin.setSingleStep(0.05)
    offset_top.addWidget(parent.offset_spin)
    offset_layout.addLayout(offset_top)

    left_layout.addWidget(offset_group)

    # --- Checkboxes ---
    checkbox_box = QGroupBox("Options")
    checkbox_layout = QVBoxLayout(checkbox_box)

    frame_layout = QHBoxLayout()
    parent.box_check = QCheckBox("Frame")
    parent.box_spin = QSpinBox()
    parent.box_spin.setRange(1, 50)
    parent.box_spin.setValue(5)
    parent.rotate_check = QCheckBox("Rotate 90°")

    # checkbox_layout.addWidget(parent.box_check)
    frame_layout.addWidget(parent.box_check)
    frame_layout.addWidget(parent.box_spin)
    checkbox_layout.addLayout(frame_layout)
    checkbox_layout.addWidget(parent.rotate_check)

    # scale svg
    scale_layout = QHBoxLayout()
    label_scale = QLabel("Scale SVG")
    parent.scale_spin = QDoubleSpinBox()
    parent.scale_spin.setSingleStep(0.1)
    parent.scale_spin.setValue(1)

    scale_layout.addWidget(label_scale)
    scale_layout.addWidget(parent.scale_spin)
    checkbox_layout.addLayout(scale_layout)
    left_layout.addWidget(checkbox_box)

    # --- stats ---
    stats_box = QGroupBox("Stats")
    stats_layout = QVBoxLayout(stats_box)
    stats_label = QLabel("Output Dimensions")
    parent.stats_label2 = QLabel("")
    stats_layout.addWidget(stats_label)
    stats_layout.addWidget(parent.stats_label2)
    left_layout.addWidget(stats_box)

    # --- Buttons ---
    parent.open_btn = QPushButton("Open SVG")
    parent.refresh_btn = QPushButton("Refresh SVG")
    parent.plot_btn = QPushButton("Plot")

    left_layout.addWidget(parent.open_btn)
    left_layout.addWidget(parent.refresh_btn)
    left_layout.addWidget(parent.plot_btn)

    # Push everything up
    left_layout.addStretch()

    # =========================
    # Graphics view (right)
    # =========================
    parent.scene = QGraphicsScene()
    parent.graphics_view = QGraphicsView(parent.scene)

    parent.graphics_view.setRenderHint(QPainter.Antialiasing)
    parent.graphics_view.setSizePolicy(
        QSizePolicy.Expanding, QSizePolicy.Expanding)

    # =========================
    # Assemble main layout
    # =========================
    main_layout.addWidget(left_panel)
    main_layout.addWidget(parent.graphics_view)

    # Stretch: left ~25%, right ~75%
    main_layout.setStretch(0, 1)
    main_layout.setStretch(1, 3)


if __name__ == "__main__":
    pass
