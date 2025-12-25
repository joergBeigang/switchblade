import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette

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
        self.settings = SettingsManager()
        self.plotter_attr = plot.PlotterSettings(self.settings)
        self.graphics = plot.Graphics()
        self.actions = Actions(self)
        self.open_file_name = ""
        self.setWindowTitle("Switchblade")
        gui.build_gui(self)
        self.current_svg_item = None
        self.connect_actions()
        self.load_ui_values()

    def connect_actions(self):
        """
        connect actions to ui elements
        """
        # buttons
        self.open_btn.clicked.connect(self.actions.open_svg)
        self.refresh_btn.clicked.connect(self.actions.load_svg)
        # self.refresh_btn.clicked.connect(self.action_open_settings)
        self.plot_btn.clicked.connect(self.actions.plot)
        # check box rotate
        self.rotate_check.toggled.connect(self.actions.rot_90)
        # check box frame
        self.box_check.toggled.connect(self.actions.frame)
        self.box_spin.valueChanged.connect(self.actions.frame_padding)
        self.settings_btn.clicked.connect(self.actions.open_settings)

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
        # self.settings.bind_widget(self.port_combo, "port", "/dev/ttyUSB0")

    def update_dim(self, dim):
        self.stats_label2.setText(f"X:{dim[0]:.1f}mm Y:{dim[1]:.1f}")
        print(dim)

    def closeEvent(self, event):
        """
        when closing the application the state of the ui elements
        is saved to a file (or registry on win)
        """
        self.settings.save_all()
        super().closeEvent(event)

    def port_combo_items(self):
        return [self.port_combo.itemText(i) for i in range(self.port_combo.count())]

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
        self.actions.frame(self.box_check.isChecked())
        self.actions.rot_90()
        self.update_dim(self.graphics.update())

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


class Actions:
    """
    all actions triggerd buy gui elements
    """

    def __init__(self, parent):
        self.parent = parent
        self.graphics = parent.graphics

    def open_svg(self):
        """
        file open and call update_svg
        """
        last_dir = self.parent.settings.settings.value("last_dir", "")
        file_name, _ = QFileDialog.getOpenFileName(
            self.parent, "Open SVG file", last_dir, "SVG Files (*.svg)"
        )
        if file_name:
            self.parent.open_file_name = file_name
            dim = self.load_svg()
            if dim:
                self.parent.update_dim(dim)
            # Save the directory for next time
            import os

            self.parent.settings.settings.setValue(
                "last_dir", os.path.dirname(file_name)
            )
            print("Selected:", file_name)

    def load_svg(self):
        if self.parent.open_file_name:
            # Remove previous SVG if any
            if self.parent.current_svg_item:
                self.parent.scene.removeItem(self.parent.current_svg_item)
            # get the color for rendering from the palette
            # render_color = palette.color(QPalette.Text)
            render_color = self.qcolor_to_svg(
                QApplication.palette().color(QPalette.Text)
            )
            # reset all values of the Graphics class
            self.graphics.reset()
            dim = self.graphics.load_svg(self.parent.open_file_name, render_color)
            self.parent.update_dim(dim)

        self.parent.update_svg()

    def qcolor_to_svg(self, color):
        """
        format color for svg attributes
        """
        return color.name()  # "#aabbcc"

    def plot(self):
        if not self.graphics.paths:
            return
        self.parent.update_plotter_attributes()
        plot.send_to_plotter(self.parent.plotter_attr, self.graphics)

    def rot_90(self):
        """
        rotates the scene by 90 degrees
        """
        # self.graphics.rot_90
        if self.graphics.rot90 == self.parent.rotate_check.isChecked():
            return
        self.graphics.rotate_by_90()
        self.parent.update_svg()

    def frame(self, *args):
        """
        adds or removes a frame around all objects
        for easier removeal of the vinyl from the
        silicone paper
        """
        dist = self.parent.box_spin.value()
        state = self.parent.box_check.isChecked()
        if self.graphics.frame is True and not state:
            self.graphics.frame_toggle(dist)
            self.parent.update_svg()
        if self.graphics.frame is False and state:
            self.graphics.frame_toggle(dist)
            self.parent.update_svg()

    def frame_padding(self, *args):
        """
        change frame padding
        """
        state = self.parent.box_check.isChecked()
        if state:
            dist = self.parent.box_spin.value()
            self.graphics.remove_frame()
            dim = self.graphics.add_frame(dist)
            self.parent.update_dim(dim)
            self.parent.update_svg()

    def open_settings(self):
        dlg = gui.SettingsDialog(
            parent=self.parent,
            plot_attr=self.parent.plotter_attr,
            ports=list_serial_ports,
        )
        if dlg.exec():  # modal
            # test = dlg.get_values()g
            print(f"test{self.parent.plotter_attr.scale}")
            self.parent.plotter_attr.save_settngs()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
