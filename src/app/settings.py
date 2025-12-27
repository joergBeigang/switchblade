from PySide6.QtCore import QSettings, QObject
from PySide6.QtWidgets import (
    QComboBox,
    QSpinBox,
    QSlider,
    QCheckBox,
)


class SettingsManager(QObject):
    """
    class for PySide6's settings
    """

    def __init__(
        self, parent=None, organization="dangerousTools", appname="Switchblade"
    ):
        super().__init__(parent)
        self.settings = QSettings(organization, appname)
        self.bindings = []

    def bind_widget(self, widget, key, default=None, autosave=True):
        """
        binds a widget to save it's value to disk
        """
        self.bindings.append((widget, key, default))

        value = self.settings.value(key, default, type=self.get_type(widget))
        self.set_widget_value(widget, value)

        if not autosave:
            return

        if isinstance(widget, (QSpinBox, QSlider)):
            widget.valueChanged.connect(lambda v, k=key: self.settings.setValue(k, v))
        elif isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(
                lambda v, k=key: self.settings.setValue(k, v)
            )
        elif isinstance(widget, QCheckBox):
            widget.toggled.connect(lambda v, k=key: self.settings.setValue(k, v))

    def save_all(self):
        """
        Save all current widget values
        """
        for widget, key, _ in self.bindings:
            self.settings.setValue(key, self.get_widget_value(widget))

    def get_type(self, widget):
        """
        Return Python type
        """
        if isinstance(widget, (QSpinBox, QSlider)):
            return int
        elif isinstance(widget, QComboBox):
            return str
        elif isinstance(widget, QCheckBox):
            return bool
        else:
            return str

    def set_widget_value(self, widget, value):
        """
        Set widget to a value (when values are loaded from
        disk
        """
        if value is None:
            return
        if isinstance(widget, (QSpinBox, QSlider)):
            widget.setValue(value)
        elif isinstance(widget, QComboBox):
            index = widget.findText(value)
            if index >= 0:
                widget.setCurrentIndex(index)
        elif isinstance(widget, QCheckBox):
            widget.setChecked(value)

    def get_widget_value(self, widget):
        """
        Get the current value from a widget
        """
        if isinstance(widget, (QSpinBox, QSlider)):
            return widget.value()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()


if __name__ == "__main__":
    pass
