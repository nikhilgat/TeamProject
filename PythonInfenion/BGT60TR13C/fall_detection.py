import numpy as np
from collections import namedtuple
from scipy import signal
from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp
from fft_spectrum import fft_spectrum

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

def main():
    config = FmcwSimpleSequenceConfig(
        frame_repetition_time_s=0.5,
        chirp_repetition_time_s=0.001,
        num_chirps=64,
        tdm_mimo=False,
        chirp=FmcwSequenceChirp(
            start_frequency_Hz=60e9,
            end_frequency_Hz=61.5e9,
            sample_rate_Hz=1e6,
            num_samples=64,
            rx_mask=5,
            tx_mask=1,
            tx_power_level=31,
            lp_cutoff_Hz=500000,
            hp_cutoff_Hz=80000,
            if_gain_dB=33,
        )
    )

    with DeviceFmcw() as device:
        print(f"Radar SDK Version: {get_version_full()}")
        print("Sensor: " + str(device.get_sensor_type()))

        sequence = device.create_simple_sequence(config)
        device.set_acquisition_sequence(sequence)

        algo = FallDetectionAlgo(config.chirp.num_samples, config.num_chirps)

        for frame_number in range(1000):
            frame_contents = device.get_next_frame()
            frame = frame_contents[0]
            mat = frame[0, :, :]
            fall_detected = algo.detect_fall(mat)
            print(f"{fall_detected}")

if __name__ == "__main__":
    main()