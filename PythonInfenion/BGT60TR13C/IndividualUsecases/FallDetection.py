'''

This Usecase need to have a specific configuration to work properly.
Change the num_chirps from 128 to 64.

'''

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QFrame, QMessageBox, QPushButton
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
import numpy as np
from scipy import signal
from scipy.ndimage import convolve
from helpers.fft_spectrum import fft_spectrum 
from radar_data_acquisition import initialize_radar, get_radar_data


class FallDetectionAlgo:
    def __init__(self, num_samples_per_chirp, num_chirps_per_frame, chirp_repetition_time_s, start_frequency_Hz):
        self.num_samples_per_chirp = num_samples_per_chirp
        self.num_chirps_per_frame = num_chirps_per_frame
        self.chirp_repetition_time_s = chirp_repetition_time_s
        self.start_frequency_Hz = start_frequency_Hz
        self.window = signal.windows.blackmanharris(num_samples_per_chirp).reshape(1, num_samples_per_chirp)
        self.fall_threshold = 1
        self.alpha = 0.4
        self.slow_avg = None
        self.fast_avg = None
        self.first_run = True

    def detect_fall(self, mat):
        mat_fil = mean_filter(mat)
        range_fft = fft_spectrum(mat_fil, self.window)
        fft_spec_abs = abs(range_fft)
        fft_norm = np.divide(fft_spec_abs.sum(axis=0), self.num_chirps_per_frame)
        radial_velocity = self.calculate_radial_velocity(mat)
        fft_norm = radial_velocity
        if self.first_run:
            self.slow_avg = fft_norm
            self.fast_avg = fft_norm
            self.first_run = False
        self.slow_avg = self.slow_avg * (1 - self.alpha) + fft_norm * self.alpha
        self.fast_avg = self.fast_avg * self.alpha + fft_norm * (1 - self.alpha)
        data = self.fast_avg - self.slow_avg
        fall_detected = np.max(data) > self.fall_threshold
        write_ndarray_to_file(mat, 'mat_data.txt')
        fall_detected = abs(radial_velocity) > 0.6
        return fall_detected

    def calculate_radial_velocity(self, mat_fil):
        doppler_fft = np.fft.fftshift(np.fft.fft2(mat_fil, axes=(0, 1)), axes=0)
        doppler_freq = np.fft.fftfreq(self.num_chirps_per_frame, self.chirp_repetition_time_s)
        doppler_freq = np.fft.fftshift(doppler_freq)
        doppler_spectrum = np.abs(doppler_fft).sum(axis=1)
        doppler_spectrum[32] = 0
        peak_index = np.argmax(doppler_spectrum)
        c = 3e8
        wavelength = c / self.start_frequency_Hz
        velocity = doppler_freq[peak_index] * wavelength / 2
        return velocity

class FallDetectionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.algo = None
        self.device = None
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.update_frame)
        self.setup_radar()
        self.fall_detected_flag = False

    def initUI(self):
        self.setWindowTitle('Fall Detection System')
        self.setGeometry(100, 100, 800, 600) 
        self.setStyleSheet("background-color: #f0f0f0;")
        font = QFont()
        font.setPointSize(14)

        self.label = QLabel('Initializing...', self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(font)
        self.label.setStyleSheet("color: #333;")
        self.frame = QFrame(self)
        self.frame.setFrameShape(QFrame.Box)
        self.frame.setFrameShadow(QFrame.Raised)
        self.frame.setLineWidth(2)
        self.frame.setStyleSheet("QFrame { background-color: white; border: 2px solid #0078D7; border-radius: 10px; }")
        self.red_light = QLabel(self)
        self.red_light.setFixedSize(60, 60) 
        self.red_light.setStyleSheet("background-color: grey; border-radius: 30px;") 
        self.reset_button = QPushButton('Reset Fall Detection', self)
        self.reset_button.setFont(font)
        self.reset_button.setStyleSheet("background-color: #0078D7; color: white; border-radius: 5px; padding: 10px;")
        self.reset_button.clicked.connect(self.reset_fall_flag)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.red_light, alignment=Qt.AlignCenter)
        layout.addWidget(self.reset_button, alignment=Qt.AlignCenter, stretch=1)
        self.frame.setLayout(layout)

        central_widget = QWidget()
        central_layout = QVBoxLayout()
        central_layout.addWidget(self.frame, alignment=Qt.AlignCenter)
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)


    def setup_radar(self):
        try:
            initialize_radar()
            self.radar_data = get_radar_data()
            config = self.radar_data.config
            self.algo = FallDetectionAlgo(
                config.chirp.num_samples, 
                config.num_chirps, 
                config.chirp_repetition_time_s, 
                config.chirp.start_frequency_Hz
                )
            self.frame_timer.start(100) 
        except Exception as e:
            self.show_error_message(f"Error setting up radar: {e}")

    def update_frame(self):
        try:
            frame = self.radar_data.get_latest_frame()
            if frame is not None:
                mat = frame[0, :, :] 
                fall_detected = self.algo.detect_fall(mat)
                if fall_detected:
                    self.fall_detected_flag = True
                    self.fallFlag()
                    self.label.setText("Fall Detected 🚨") 
                    self.frame.setStyleSheet("QFrame { background-color: #ffcccc; border: 2px solid #ff0000; border-radius: 10px; }")
                else:
                    self.fall_detected_flag = False
                    self.label.setText("No Fall Detected ✅") 
                    self.frame.setStyleSheet("QFrame { background-color: #ccffcc; border: 2px solid #00ff00; border-radius: 10px; }")
        except Exception as e:
            self.show_error_message(f"Error updating frame: {e}")

    def fallFlag(self):
        self.red_light.setStyleSheet("background-color: red; border-radius: 30px;") 

    def reset_fall_flag(self):
        self.fall_detected_flag = False
        self.red_light.setStyleSheet("background-color: grey; border-radius: 30px;")

    def show_error_message(self, message):
        QMessageBox.critical(self, 'Error', message)

    def closeEvent(self, event):
        if self.radar_data:
            self.radar_data.stop()
        event.accept()

def write_ndarray_to_file(arr, file_path):
    with open(file_path, 'a') as file:
        file.write('[\n')
        for row in arr:
            line = ' '.join(map(str, row)) + '\n'
            file.write(line)
        file.write(']\n\n')

def mean_filter(data, kernel_size=3):
    if data.ndim == 1:
        kernel = np.ones(kernel_size) / kernel_size
        filtered_data = np.convolve(data, kernel, mode='same')
    elif data.ndim == 2:
        kernel = np.ones((kernel_size, kernel_size)) / (kernel_size ** 2)
        filtered_data = convolve(data, kernel, mode='reflect')
    else:
        raise ValueError("Input data must be a 1D or 2D array.")

    return filtered_data

def main():
    app = QApplication(sys.argv)
    ex = FallDetectionApp()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()