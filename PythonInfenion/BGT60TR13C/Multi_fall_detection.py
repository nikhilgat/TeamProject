import numpy as np
from scipy import signal
from helpers.fft_spectrum import fft_spectrum
import time
from radar_data_acquisition import get_radar_data

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

def run_fall_detection():
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
            print(f"Fall detected: {fall_detected}")
        time.sleep(0.1)

    print("Fall detection algorithm stopped.")

if __name__ == "__main__":
    from radar_data_acquisition import initialize_radar
    initialize_radar()
    run_fall_detection()