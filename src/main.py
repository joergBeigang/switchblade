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


def list_serial_ports():
    return [port.device for port in serial.tools.list_ports.comports()]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.plotter_attr = plot.PlotterSettings()
        self.graphics = plot.Graphics()
        self.open_file_name = ""
        self.setWindowTitle("Switchblade")
        gui.build_gui(self)
        self.port_timer = QTimer()
        self.port_timer.timeout.connect(self.update_ports)
        self.port_timer.start(1000)  # 1 second
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
        self.refresh_btn.clicked.connect(self.reload_svg)
        self.plot_btn.clicked.connect(self.plot)
        # check box rotate
        self.rotate_check.toggled.connect(self.action_rot_90)
        # check box frame
        self.box_check.toggled.connect(self.action_frame)
        self.box_spin.valueChanged.connect(self.action_frame_padding)

    def load_ui_values(self):
        """
        restore ui elements from last session
        """
        self.settings.bind_widget(self.speed_spin, "speed", 40)
        self.settings.bind_widget(self.speed_slider, "speed", 40)
        self.settings.bind_widget(self.pressure_spin, "pressure", 17)
        self.settings.bind_widget(self.pressure_slider, "pressure", 17)
        self.settings.bind_widget(self.box_check, "box", False)
        self.settings.bind_widget(self.box_spin, "box_spin", 5)
        self.settings.bind_widget(self.rotate_check, "rotate90", False)
        self.settings.bind_widget(self.port_combo, "port", "/dev/ttyUSB0")

    def closeEvent(self, event):
        """
        when closing the application the state of the ui elements
        is saved to a file (or registry on win)
        """
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
        """
        file open and call update_svg
        """
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open SVG file", "", "SVG Files (*.svg)"
        )
        if file_name:
            self.open_file_name = file_name
            self.reload_svg()
        #     # Remove previous SVG if any
        #     if self.current_svg_item:
        #         self.scene.removeItem(self.current_svg_item)
        #     self.open_file_name = file_name
        #     self.graphics.load_svg(file_name)
        # self.update_svg()

    def reload_svg(self):
        if self.open_file_name:
            # Remove previous SVG if any
            if self.current_svg_item:
                self.scene.removeItem(self.current_svg_item)
            #
            # get the color for rendering from the palette
            # palette = QApplication.palette()
            # render_color = palette.color(QPalette.Text)
            render_color = self.qcolor_to_svg(
                QApplication.palette().color(QPalette.Text)
            )
            self.graphics.load_svg(self.open_file_name, render_color)

        self.update_svg()

    def qcolor_to_svg(self, color):
        """
        format color for svg attributes
        """
        return color.name()  # "#aabbcc"

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
        self.graphics_view.fitInView(
            svg_item.boundingRect(), Qt.KeepAspectRatio)
        self.action_frame(self.box_check.isChecked())

    def action_rot_90(self):
        """
        rotates the scene by 90 degrees
        """
        self.graphics.rotate_by_90()
        self.update_svg()

    def action_frame_padding(self, *args):
        """
        change frame padding
        """
        state = self.box_check.isChecked()
        if state:
            dist = self.box_spin.value()
            self.graphics.remove_frame()
            self.graphics.add_frame(dist)
            self.update_svg()

    def action_frame(self, *args):
        """
        adds or removes a frame around all objects
        for easier removeal of the vinyl from the
        silicone paper
        """
        dist = self.box_spin.value()
        state = self.box_check.isChecked()
        if self.graphics.frame is True and not state:
            self.graphics.frame_toggle(dist)
            self.update_svg()
        if self.graphics.frame is False and state:
            self.graphics.frame_toggle(dist)
            self.update_svg()

    def resizeEvent(self, event):
        """
        added an update to the resizeEvent so the render
        is matching the window size
        """
        self.update_svg()
        # Call the base implementation (important!)
        super().resizeEvent(event)

    def update_plotter_attributes(self):
        """
        updates based on the state of the gui
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
