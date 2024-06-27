
#Adjust the height parameter in the find_peaks function based on the specific setup and sensitivity required.

import numpy as np
from scipy import signal
from collections import namedtuple
import fft_spectrum

class FallDetectionAlgo:
    def __init__(self, num_samples_per_chirp, num_chirps_per_frame):
        self.num_samples_per_chirp = num_samples_per_chirp
        self.num_chirps_per_frame = num_chirps_per_frame
        self.window = signal.windows.blackmanharris(num_samples_per_chirp).reshape(1, num_samples_per_chirp)
        self.fall_detected = False

    def detect_fall(self, mat):
        range_fft = fft_spectrum(mat, self.window)
        fft_spec_abs = abs(range_fft)
        fft_norm = np.divide(fft_spec_abs.sum(axis=0), self.num_chirps_per_frame)

        # Simplified fall detection based on high-energy peak detection
        peaks, _ = signal.find_peaks(fft_norm, height=100)  # Adjust height based on calibration
        if len(peaks) > 0:
            self.fall_detected = True
        else:
            self.fall_detected = False

        return namedtuple("FallDetection", ["fall_detected"])(self.fall_detected)
