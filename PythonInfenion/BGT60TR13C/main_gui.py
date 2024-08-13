import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout
from radar_data_acquisition import initialize_radar, get_radar_data
import threading

class RadarGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Radar Data Analysis")
        self.setGeometry(100, 100, 800, 600)

        main_layout = QHBoxLayout()

        button_layout = QVBoxLayout()

        self.fall_detection_button = QPushButton("Run Fall Detection")
        self.fall_detection_button.clicked.connect(self.run_fall_detection)
        button_layout.addWidget(self.fall_detection_button)

        self.presence_detection_button = QPushButton("Run Presence Detection")
        self.presence_detection_button.clicked.connect(self.run_presence_detection)
        button_layout.addWidget(self.presence_detection_button)

        # Add more buttons for other algorithms here

        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        main_layout.addWidget(button_widget)

        self.plot_widget = QWidget()
        main_layout.addWidget(self.plot_widget)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Initialize radar data acquisition
        initialize_radar()

        self.presence_detection = None

    def run_fall_detection(self):
        thread = threading.Thread(target=self._fall_detection)
        thread.start()

    def _fall_detection(self):
        from Multi_fall_detection import run_fall_detection
        run_fall_detection()

    def run_presence_detection(self):
        if self.presence_detection is None:
            from Multi_PresenceDetectionTopView import run_presence_detection
            self.presence_detection = run_presence_detection()
            plot = self.presence_detection.initialize_plot()
            layout = QVBoxLayout()
            layout.addWidget(plot)
            self.plot_widget.setLayout(layout)
            self.presence_detection.signals.update_plot.connect(plot.update_angle)


        thread = threading.Thread(target=self.presence_detection.run_presence_detection)
        thread.start()

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