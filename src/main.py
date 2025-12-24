import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
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
    QFileDialog,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter

# from PySide6.QtSvg import QGraphicsSvgItem
import serial.tools.list_ports
import copy
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import QGraphicsPixmapItem
from settings import SettingsManager
import plot


def list_serial_ports():
    return [port.device for port in serial.tools.list_ports.comports()]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.plotter_attr = plot.PlotterSettings()
        self.graphics = plot.Graphics()
        self.open_file_name = ""
        self.setWindowTitle("Plotter GUI")

        # ---- Central widget ----
        central = QWidget()
        self.setCentralWidget(central)

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
        self.port_combo = QComboBox()
        self.port_combo.addItems(["/dev/ttyUSB0", "/dev/ttyUSB1"])
        left_layout.addWidget(self.port_combo)

        # --- Baud rate dropdown ---
        left_layout.addWidget(QLabel("Baud rate"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "115200"])
        self.baud_combo.setCurrentText("9600")
        left_layout.addWidget(self.baud_combo)

        # --- Speed group ---
        speed_group = QGroupBox("Speed")
        speed_layout = QVBoxLayout(speed_group)

        speed_top = QHBoxLayout()
        speed_top.addWidget(QLabel("Speed"))
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 200)
        self.speed_spin.setValue(40)
        speed_top.addWidget(self.speed_spin)
        speed_layout.addLayout(speed_top)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 200)
        self.speed_slider.setValue(40)
        speed_layout.addWidget(self.speed_slider)

        left_layout.addWidget(speed_group)
        # Speed two-way connection
        self.speed_spin.valueChanged.connect(self.speed_slider.setValue)
        self.speed_slider.valueChanged.connect(self.speed_spin.setValue)

        # --- Pressure group ---
        pressure_group = QGroupBox("Pressure")
        pressure_layout = QVBoxLayout(pressure_group)

        pressure_top = QHBoxLayout()
        pressure_top.addWidget(QLabel("Force"))
        self.pressure_spin = QSpinBox()
        self.pressure_spin.setRange(1, 200)
        self.pressure_spin.setValue(80)
        pressure_top.addWidget(self.pressure_spin)
        pressure_layout.addLayout(pressure_top)

        self.pressure_slider = QSlider(Qt.Horizontal)
        self.pressure_slider.setRange(1, 200)
        self.pressure_slider.setValue(80)
        pressure_layout.addWidget(self.pressure_slider)

        left_layout.addWidget(pressure_group)
        self.pressure_spin.valueChanged.connect(self.pressure_slider.setValue)
        self.pressure_slider.valueChanged.connect(self.pressure_spin.setValue)

        # --- Offset group ---
        offset_group = QGroupBox("Offset")
        offset_layout = QVBoxLayout(offset_group)

        offset_top = QHBoxLayout()
        offset_top.addWidget(QLabel("Knife Offset"))
        self.offset_spin = QDoubleSpinBox()
        self.offset_spin.setRange(0, 2)
        self.offset_spin.setValue(0.2)
        self.offset_spin.setSingleStep(0.05)
        offset_top.addWidget(self.offset_spin)
        offset_layout.addLayout(offset_top)

        left_layout.addWidget(offset_group)

        # --- Checkboxes ---
        checkbox_box = QGroupBox("Options")
        checkbox_layout = QVBoxLayout(checkbox_box)

        self.box_check = QCheckBox("Frame")
        self.rotate_check = QCheckBox("Rotate 90°")

        checkbox_layout.addWidget(self.box_check)
        checkbox_layout.addWidget(self.rotate_check)

        left_layout.addWidget(checkbox_box)

        # --- Buttons ---
        self.open_btn = QPushButton("Open SVG")
        self.refresh_btn = QPushButton("Refresh SVG")
        self.plot_btn = QPushButton("Plot")

        left_layout.addWidget(self.open_btn)
        left_layout.addWidget(self.refresh_btn)
        left_layout.addWidget(self.plot_btn)

        # Push everything up
        left_layout.addStretch()

        # =========================
        # Graphics view (right)
        # =========================
        scene = QGraphicsScene()
        graphics_view = QGraphicsView(scene)

        graphics_view.setRenderHint(QPainter.Antialiasing)
        graphics_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # =========================
        # Assemble main layout
        # =========================
        main_layout.addWidget(left_panel)
        main_layout.addWidget(graphics_view)

        # Stretch: left ~25%, right ~75%
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 3)
        self.port_timer = QTimer()
        self.port_timer.timeout.connect(self.update_ports)
        self.port_timer.start(1000)  # 1 second
        self.scene = scene
        self.graphics_view = graphics_view
        self.current_svg_item = None

        # Connect Open SVG button
        self.connect_actions()

        self.settings = SettingsManager()
        self.load_ui_values()

    def connect_actions(self):
        """
        connect actions to ui elements
        """
        # buttons
        self.open_btn.clicked.connect(self.open_svg)
        self.refresh_btn.clicked.connect(self.update_svg)
        self.plot_btn.clicked.connect(self.plot)
        # check box rotate
        self.rotate_check.toggled.connect(self.action_rot_90)
        # check box frame
        self.box_check.toggled.connect(self.action_frame)

    def load_ui_values(self):
        self.settings.bind_widget(self.speed_spin, "speed", 40)
        self.settings.bind_widget(self.speed_slider, "speed", 40)
        self.settings.bind_widget(self.pressure_spin, "pressure", 17)
        self.settings.bind_widget(self.pressure_slider, "pressure", 17)
        self.settings.bind_widget(self.box_check, "box", False)
        self.settings.bind_widget(self.rotate_check, "rotate90", False)
        self.settings.bind_widget(self.port_combo, "port", "/dev/ttyUSB0")

    def closeEvent(self, event):
        # Save all widgets before closing
        self.settings.save_all()
        super().closeEvent(event)

    def update_ports(self):
        current = self.port_combo.currentText()
        ports = list_serial_ports()
        if set(ports) != set(self.port_combo_items()):
            self.port_combo.clear()
            self.port_combo.addItems(ports)
            if current in ports:
                self.port_combo.setCurrentText(current)

    def port_combo_items(self):
        return [self.port_combo.itemText(i) for i in range(self.port_combo.count())]

    def open_svg(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open SVG file", "", "SVG Files (*.svg)"
        )
        if file_name:
            # Remove previous SVG if any
            if self.current_svg_item:
                self.scene.removeItem(self.current_svg_item)
            self.open_file_name = file_name
            self.graphics.load_svg(file_name)
        self.update_svg()

    def update_svg(self):
        """
        update attributes and render
        """
        self.scene.clear()
        if not self.graphics.svg_xml:
            return
        self.current_svg_item = None

        # Create a renderer from in-memory SVG
        self.current_renderer = QSvgRenderer(QByteArray(self.graphics.svg_xml))

        # Create SVG item and add to scene
        svg_item = QGraphicsSvgItem()
        svg_item.setSharedRenderer(self.current_renderer)
        self.scene.addItem(svg_item)
        self.current_svg_item = svg_item

        # Resize scene to bounding rect
        self.scene.setSceneRect(svg_item.boundingRect())
        self.graphics_view.fitInView(svg_item.boundingRect(), Qt.KeepAspectRatio)
        self.action_frame(self.box_check.isChecked())

    def action_rot_90(self):
        self.graphics.rotate_by_90()
        self.update_svg()

    def action_frame(self, state: int):
        if self.graphics.frame is True and state == 0:
            self.graphics.frame_toggle()
            self.update_svg()
        if self.graphics.frame is False and state == 1:
            self.graphics.frame_toggle()
            self.update_svg()

    def resizeEvent(self, event):
        # This is called whenever the window is resized
        self.update_svg()
        # Call the base implementation (important!)
        super().resizeEvent(event)

    def update_plotter_attributes(self):
        """
        updates the isinstance of the dataclass
        file_name = self.open_file_name
        # Render SVG into a pixmap
        renderer = QSvgRenderer(file_name)
        size = renderer.defaultSize()
        pixmap = QPixmap(size.width(), size.height())
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        """
        self.plotter_attr.port = self.port_combo.currentText()
        self.plotter_attr.baud = self.baud_combo.currentText()
        self.plotter_attr.knife_offset = self.offset_spin.value()
        self.plotter_attr.speed = self.speed_spin.value()
        self.plotter_attr.pressure = self.pressure_spin.value()
        self.plotter_attr.scale = 100

    def plot(self):
        self.update_plotter_attributes()
        plot.send_to_plotter(self.plotter_attr, self.graphics)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
