import numpy as np
from scipy import signal
from helpers.fft_spectrum import fft_spectrum
import time
from radar_data_acquisition import get_radar_data
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtGui import QFont
import sys
import threading

class FallDetectionSignals(QObject):
    update_status = pyqtSignal(bool)

class FallDetectionAlgo:
    def __init__(self, num_samples_per_chirp, num_chirps_per_frame):
        self.num_samples_per_chirp = num_samples_per_chirp
        self.num_chirps_per_frame = num_chirps_per_frame

        self.window = signal.windows.blackmanharris(num_samples_per_chirp).reshape(1, num_samples_per_chirp)

        self.fall_threshold = 0.00001  
        self.alpha = 0.5

        self.slow_avg = None
        self.fast_avg = None
        self.first_run = True

    def detect_fall(self, mat):
        range_fft = fft_spectrum(mat, self.window)

        fft_spec_abs = abs(range_fft)
        fft_norm = np.divide(fft_spec_abs.sum(axis=0), self.num_chirps_per_frame)

        if self.first_run:
            self.slow_avg = fft_norm
            self.fast_avg = fft_norm
            self.first_run = False

        self.slow_avg = self.slow_avg * (1 - self.alpha) + fft_norm * self.alpha
        self.fast_avg = self.fast_avg * self.alpha + fft_norm * (1 - self.alpha)
        data = self.fast_avg - self.slow_avg

        fall_detected = np.max(data) > self.fall_threshold

        return fall_detected

class FallDetectionStatusGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Fall Detection Status')
        self.setGeometry(100, 100, 300, 100)

        layout = QVBoxLayout()
        self.status_label = QLabel("🧍 No fall detected", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont('Arial', 20))
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def update_status(self, fall_detected):
        if fall_detected:
            self.status_label.setText("💥 FALL DETECTED! 💥")
        else:
            self.status_label.setText("🧍 No fall detected")

def run_fall_detection(signals):
    radar_data = get_radar_data()
    if radar_data is None:
        print("Radar data acquisition not initialized")
        return

    num_samples_per_chirp = radar_data.config.chirp.num_samples
    num_chirps_per_frame = radar_data.config.num_chirps
    algo = FallDetectionAlgo(num_samples_per_chirp, num_chirps_per_frame)

    print("Fall detection algorithm started.")
    
    while radar_data.running:
        frame = radar_data.get_latest_frame()
        if frame is not None:
            mat = frame[0, :, :]
            fall_detected = algo.detect_fall(mat)
            signals.update_status.emit(fall_detected)
        time.sleep(0.1)

    print("Fall detection algorithm stopped.")

def start_fall_detection():
    app = QApplication(sys.argv)
    status_gui = FallDetectionStatusGUI()
    status_gui.show()

    signals = FallDetectionSignals()
    signals.update_status.connect(status_gui.update_status)

    fall_detection_thread = threading.Thread(target=run_fall_detection, args=(signals,))
    fall_detection_thread.start()

    sys.exit(app.exec_())

if __name__ == "__main__":
    from radar_data_acquisition import initialize_radar
    initialize_radar()
    start_fall_detection()