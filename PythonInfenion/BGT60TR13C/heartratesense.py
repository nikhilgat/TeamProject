import numpy as np
from scipy import signal
from collections import namedtuple

class HeartRateAlgo:
    def __init__(self, num_samples_per_chirp, num_chirps_per_frame):
        self.num_samples_per_chirp = num_samples_per_chirp
        self.num_chirps_per_frame = num_chirps_per_frame

        self.window = signal.windows.blackmanharris(num_samples_per_chirp).reshape(1, num_samples_per_chirp)
        self.heart_rate = 0
        self.bpm_history = []

    def detect_heart_rate(self, mat):
        range_fft = fft_spectrum(mat, self.window)
        fft_spec_abs = abs(range_fft)
        fft_norm = np.divide(fft_spec_abs.sum(axis=0), self.num_chirps_per_frame)

        # Simplified peak detection
        peaks, _ = signal.find_peaks(fft_norm, distance=20)
        num_peaks = len(peaks)

        if num_peaks > 0:
            peak_intervals = np.diff(peaks)
            if len(peak_intervals) > 0:
                avg_interval = np.mean(peak_intervals)
                self.heart_rate = 60.0 / avg_interval
                self.bpm_history.append(self.heart_rate)
                if len(self.bpm_history) > 10:
                    self.bpm_history.pop(0)
                self.heart_rate = np.mean(self.bpm_history)

        return namedtuple("HeartRate", ["bpm"])(self.heart_rate)
