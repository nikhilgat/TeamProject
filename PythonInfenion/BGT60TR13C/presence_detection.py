import numpy as np
from collections import namedtuple
from scipy import signal
from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp
from fft_spectrum import fft_spectrum

class PresenceAntiPeekingAlgo:
    def __init__(self, num_samples_per_chirp, num_chirps_per_frame):
        self.num_samples_per_chirp = num_samples_per_chirp
        self.num_chirps_per_frame = num_chirps_per_frame

        self.detect_start_sample = num_samples_per_chirp // 8
        self.detect_end_sample = num_samples_per_chirp // 2
        self.peek_start_sample = num_samples_per_chirp // 2
        self.peek_end_sample = num_samples_per_chirp

        self.threshold_presence = 0.0007
        self.threshold_peeking = 0.0006

        self.alpha_slow = 0.001
        self.alpha_med = 0.05
        self.alpha_fast = 0.6

        self.presence_status = False
        self.peeking_status = False
        self.first_run = True

        self.window = signal.windows.blackmanharris(num_samples_per_chirp).reshape(1, num_samples_per_chirp)

    def presence(self, mat):
        alpha_slow = self.alpha_slow
        alpha_med = self.alpha_med
        alpha_fast = self.alpha_fast

        range_fft = fft_spectrum(mat, self.window)

        fft_spec_abs = abs(range_fft)
        fft_norm = np.divide(fft_spec_abs.sum(axis=0), self.num_chirps_per_frame)

        if self.first_run:
            self.slow_avg = fft_norm
            self.fast_avg = fft_norm
            self.slow_peek_avg = fft_norm
            self.first_run = False

        if not self.presence_status:
            alpha_used = alpha_med
        else:
            alpha_used = alpha_slow

        self.slow_avg = self.slow_avg * (1 - alpha_used) + fft_norm * alpha_used
        self.fast_avg = self.fast_avg * (1 - alpha_fast) + fft_norm * alpha_fast
        data = self.fast_avg - self.slow_avg

        self.presence_status = np.max(data[self.detect_start_sample:self.detect_end_sample]) > self.threshold_presence

        if not self.peeking_status:
            alpha_used = self.alpha_med
        else:
            alpha_used = self.alpha_slow

        self.slow_peek_avg = self.slow_peek_avg * (1 - alpha_used) + fft_norm * alpha_used
        data_peek = self.fast_avg - self.slow_peek_avg

        self.peeking_status = np.max(data_peek[self.peek_start_sample:self.peek_end_sample]) > self.threshold_peeking

        return namedtuple("state", ["presence", "peeking"])(self.presence_status, self.peeking_status)

def main():
    config = FmcwSimpleSequenceConfig(
        frame_repetition_time_s=1 / 5,
        chirp_repetition_time_s=0.000411238,
        num_chirps=32,
        tdm_mimo=False,
        chirp=FmcwSequenceChirp(
            start_frequency_Hz=59_133_931_281,
            end_frequency_Hz=62_366_068_720,
            sample_rate_Hz=1e6,
            num_samples=64,
            rx_mask=1,
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

        algo = PresenceAntiPeekingAlgo(config.chirp.num_samples, config.num_chirps)

        for frame_number in range(100):
            frame_contents = device.get_next_frame()
            frame = frame_contents[0]
            mat = frame[0, :, :]
            presence_status, peeking_status = algo.presence(mat)
            print(f"{presence_status},{peeking_status}")

if __name__ == "__main__":
    main()
