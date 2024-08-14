import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, 
                             QHBoxLayout, QLabel, QDockWidget, QSizePolicy)
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from radar_data_acquisition import initialize_radar, get_radar_data
import threading

class FallDetectionSignals(QObject):
    update_status = pyqtSignal(bool)

class ButtonDock(QDockWidget):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

class RadarGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Radar Data Analysis")
        # self.showFullScreen()

        # Create a central widget to hold the dock widgets
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Button dock
        button_dock = ButtonDock("Controls", self)
        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)

        self.fall_detection_button = QPushButton("Run Fall Detection")
        self.fall_detection_button.clicked.connect(self.run_fall_detection)
        button_layout.addWidget(self.fall_detection_button)

        self.presence_detection_button = QPushButton("Run Presence Detection")
        self.presence_detection_button.clicked.connect(self.run_presence_detection)
        button_layout.addWidget(self.presence_detection_button)

        button_dock.setWidget(button_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, button_dock)

        # Fall detection dock
        self.fall_detection_dock = QDockWidget("Fall Detection", self)
        self.fall_detection_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        self.fall_detection_widget = QLabel("Fall Detection Status: Not Running")
        self.fall_detection_widget.setAlignment(Qt.AlignCenter)
        self.fall_detection_widget.setStyleSheet("border: 1px solid black;")
        self.fall_detection_dock.setWidget(self.fall_detection_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.fall_detection_dock)

        # Presence detection dock
        self.presence_detection_dock = QDockWidget("Presence Detection", self)
        self.presence_detection_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        self.presence_detection_widget = QLabel("Presence Detection: Not Running")
        self.presence_detection_widget.setAlignment(Qt.AlignCenter)
        self.presence_detection_widget.setStyleSheet("border: 1px solid black;")
        self.presence_detection_dock.setWidget(self.presence_detection_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.presence_detection_dock)

        # Initialize radar data acquisition
        initialize_radar()

        self.presence_detection = None
        self.fall_detection_signals = FallDetectionSignals()
        self.fall_detection_signals.update_status.connect(self.update_fall_detection_status)

    def run_fall_detection(self):
        self.fall_detection_widget.setText("Fall Detection Status: Running...")
        thread = threading.Thread(target=self._fall_detection)
        thread.start()

    def _fall_detection(self):
        from Multi_fall_detection import run_fall_detection
        run_fall_detection(self.fall_detection_signals)

    def update_fall_detection_status(self, fall_detected):
        if fall_detected:
            self.fall_detection_widget.setText("Fall Detection Status: 💥 FALL DETECTED! 💥")
        else:
            self.fall_detection_widget.setText("Fall Detection Status: 🧍 No fall detected")

    def run_presence_detection(self):
        if self.presence_detection is None:
            from Multi_PresenceDetectionTopView import run_presence_detection
            self.presence_detection = run_presence_detection()
            plot = self.presence_detection.initialize_plot()
            self.presence_detection_widget = plot
            self.presence_detection_dock.setWidget(plot)
            self.presence_detection.signals.update_plot.connect(plot.update_angle)

        thread = threading.Thread(target=self._presence_detection)
        thread.start()

    def _presence_detection(self):
        if self.presence_detection:
            self.presence_detection.run_presence_detection()

    def closeEvent(self, event):
        radar_data = get_radar_data()
        if radar_data:
            radar_data.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = RadarGUI()
    gui.show()
    sys.exit(app.exec_())