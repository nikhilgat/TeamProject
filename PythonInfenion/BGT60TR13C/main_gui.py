import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, 
                             QHBoxLayout, QLabel, QDockWidget, QSizePolicy, QSlider)
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtGui import QFont
from Radar_Data_Acquisition import initialize_radar, get_radar_data
import threading
from Posture_Detection_Usecase import PostureDetectionAlgo
from Fall_Detection_Usecase import FallDetectionAlgo
from People_Count_Usecase import PresenceAlgo
from Presence_detection_Usecase import run_presence_detection

class RadarSignals(QObject):
    update_posture = pyqtSignal(str)
    update_fall = pyqtSignal(bool)
    update_people_count = pyqtSignal(int)
    
class ButtonDock(QDockWidget):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.setMinimumSize(400, 500)  # Set initial size for the dock

class RadarGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Radar Data Analysis")
        self.setGeometry(600, 500, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Button dock
        button_dock = ButtonDock("Controls", self)
        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)

        self.posture_detection_button = QPushButton("Run Posture Detection")
        self.posture_detection_button.clicked.connect(self.run_posture_detection)
        button_layout.addWidget(self.posture_detection_button)

        self.presence_detection_button = QPushButton("Run Presence Detection")
        self.presence_detection_button.clicked.connect(self.run_presence_detection)
        button_layout.addWidget(self.presence_detection_button)

        self.fall_detection_button = QPushButton("Run Fall Detection")
        self.fall_detection_button.clicked.connect(self.run_fall_detection)
        button_layout.addWidget(self.fall_detection_button)

        self.people_count_button = QPushButton("Run People Count")
        self.people_count_button.clicked.connect(self.run_people_count)
        button_layout.addWidget(self.people_count_button)

        button_dock.setWidget(button_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, button_dock)

        # Posture detection dock
        self.posture_detection_dock = QDockWidget("Posture Detection", self)
        self.posture_detection_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.posture_detection_dock.setMinimumSize(200, 200)

        posture_widget = QWidget()
        posture_layout = QVBoxLayout(posture_widget)

        self.posture_icon_label = QLabel("", alignment=Qt.AlignCenter)
        self.posture_icon_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        posture_layout.addWidget(self.posture_icon_label)

        self.icon_size_slider = QSlider(Qt.Horizontal)
        self.icon_size_slider.setMinimum(50)
        self.icon_size_slider.setMaximum(200)
        self.icon_size_slider.setValue(100)
        self.icon_size_slider.valueChanged.connect(self.update_icon_size)
        posture_layout.addWidget(self.icon_size_slider)

        self.posture_detection_dock.setWidget(posture_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.posture_detection_dock)

        # Presence detection dock
        self.presence_detection_dock = QDockWidget("Presence Detection", self)
        self.presence_detection_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.presence_detection_dock.setMinimumSize(200, 200)
        self.presence_detection_widget = QLabel("Presence Detection: Not Running")
        self.presence_detection_widget.setAlignment(Qt.AlignCenter)
        self.presence_detection_widget.setStyleSheet("border: 1px solid black;")
        self.presence_detection_dock.setWidget(self.presence_detection_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.presence_detection_dock)

        # Fall detection dock
        self.fall_detection_dock = QDockWidget("Fall Detection", self)
        self.fall_detection_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.fall_detection_dock.setMinimumSize(200, 200)
        self.fall_detection_widget = QLabel("Fall Detection: Not Running")
        self.fall_detection_widget.setAlignment(Qt.AlignCenter)
        self.fall_detection_widget.setStyleSheet("border: 1px solid black;")
        self.fall_detection_dock.setWidget(self.fall_detection_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.fall_detection_dock)

        # People count dock
        self.people_count_dock = QDockWidget("People Count", self)
        self.people_count_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.people_count_dock.setMinimumSize(200, 200)
        self.people_count_widget = QLabel("People Count: Not Running")
        self.people_count_widget.setAlignment(Qt.AlignCenter)
        self.people_count_widget.setStyleSheet("border: 1px solid black;")
        self.people_count_dock.setWidget(self.people_count_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.people_count_dock)
        
        initialize_radar()
        self.radar_data = get_radar_data()

        self.presence_detection = None
        self.radar_signals = RadarSignals()
        self.radar_signals.update_posture.connect(self.update_posture_detection_status)
        self.radar_signals.update_fall.connect(self.update_fall_detection_status)
        self.radar_signals.update_people_count.connect(self.update_people_count_status)

        self.icons = {
            "standing": "🧍",
            "sitting": "🪑",
            "sleeping": "🛌",
            "no_presence": "❌",
            "unknown": "❓"
        }

        self.update_icon_size(100)

        # Initialize algorithms
        self.posture_algo = PostureDetectionAlgo(
            self.radar_data.config.chirp.num_samples,
            self.radar_data.config.num_chirps
        )
        self.fall_detection_algo = FallDetectionAlgo(
            self.radar_data.config.chirp.num_samples,
            self.radar_data.config.num_chirps,
            self.radar_data.config.chirp_repetition_time_s,
            self.radar_data.config.chirp.start_frequency_Hz
        )
        self.presence_algo = PresenceAlgo(
            self.radar_data.config.chirp.num_samples,
            self.radar_data.config.num_chirps
        )

    def posture_detection_loop(self):
        while True:
            frame = self.radar_data.get_latest_frame()
            if frame is not None:
                mat = frame[0, :, :]  # Assuming we're using the first antenna
                state = self.posture_algo.presence(mat)
                
                if state.presence:
                    if len(state.peaks) > 0:
                        peak_idx = state.peaks[0]
                        max_range_m = self.radar_data.device.metrics_from_sequence(
                            self.radar_data.device.get_acquisition_sequence().loop.sub_sequence.contents
                        ).max_range_m
                        distance = (peak_idx / self.radar_data.config.chirp.num_samples) * max_range_m

                        if distance <= 0.50:
                            posture = "standing"
                        elif 0.50 < distance <= 0.70:
                            posture = "sitting"
                        elif 0.70 < distance <= 0.90:
                            posture = "sleeping"
                        else:
                            posture = "unknown"
                    else:
                        posture = "unknown"
                else:
                    posture = "no_presence"

                self.radar_signals.update_posture.emit(posture)

    def run_posture_detection(self):
        thread = threading.Thread(target=self.posture_detection_loop)
        thread.start()

    def run_fall_detection(self):
            thread = threading.Thread(target=self._fall_detection)
            thread.start()

    def _fall_detection(self):
        while True:
            frame = self.radar_data.get_latest_frame()
            if frame is not None:
                mat = frame[0, :, :]  # Assuming we're using the first antenna
                fall_detected = self.fall_detection_algo.detect_fall(mat)
                self.radar_signals.update_fall.emit(fall_detected)

    def run_people_count(self):
        thread = threading.Thread(target=self._people_count)
        thread.start()

    def _people_count(self):
        while True:
            frame = self.radar_data.get_latest_frame()
            if frame is not None:
                mat = frame[0, :, :]  # Assuming we're using the first antenna
                state = self.presence_algo.presence(mat)
                self.radar_signals.update_people_count.emit(state.num_persons)

    def run_presence_detection(self):
        if self.presence_detection is None:
            from Presence_detection_Usecase import run_presence_detection
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

    def update_posture_detection_status(self, status):
        self.posture_icon_label.setText(self.icons.get(status.lower(), self.icons["unknown"]))

    def update_fall_detection_status(self, fall_detected):
        if fall_detected:
            self.fall_detection_widget.setText("Fall Detected!")
            self.fall_detection_widget.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        else:
            self.fall_detection_widget.setText("No Fall Detected")
            self.fall_detection_widget.setStyleSheet("background-color: green; color: white;")

    def update_people_count_status(self, count):
        self.people_count_widget.setText(f"People Count: {count}")

    def update_icon_size(self, size):
        font = QFont()
        font.setPointSize(size)
        self.posture_icon_label.setFont(font)

    def closeEvent(self, event):
        if self.radar_data:
            self.radar_data.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = RadarGUI()
    gui.show()
    sys.exit(app.exec_())