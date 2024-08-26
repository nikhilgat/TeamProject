import numpy as np
from scipy.signal import find_peaks
from collections import namedtuple
from scipy import signal
from helpers.fft_spectrum import fft_spectrum
from radar_data_acquisition import initialize_radar, get_radar_data

class PresenceAlgo:
    def __init__(self, num_samples_per_chirp, num_chirps_per_frame):
        self.num_samples_per_chirp = num_samples_per_chirp
        self.num_chirps_per_frame = num_chirps_per_frame

        self.detect_start_sample = num_samples_per_chirp // 8
        self.detect_end_sample = (3 * num_samples_per_chirp) // 4

        self.threshold_presence = 0.0001

        self.alpha_slow = 0.001
        self.alpha_med = 0.05
        self.alpha_fast = 0.6

        self.presence_status = False
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
            self.first_run = False

        if not self.presence_status:
            alpha_used = alpha_med
        else:
            alpha_used = alpha_slow

        self.slow_avg = self.slow_avg * (1 - alpha_used) + fft_norm * alpha_used
        self.fast_avg = self.fast_avg * (1 - alpha_fast) + fft_norm * alpha_fast
        data = self.fast_avg - self.slow_avg

        self.presence_status = np.max(data[self.detect_start_sample:self.detect_end_sample]) > self.threshold_presence

        peaks, _ = find_peaks(data[self.detect_start_sample:self.detect_end_sample], height=self.threshold_presence)
        num_persons = len(peaks)

        return namedtuple("state", ["presence", "num_persons", "peaks", "data"])(self.presence_status, num_persons, peaks, data)

    def estimate_aoa(self, mat, peaks, antenna_distance, wavelength):
        num_antennas = mat.shape[0]
        aoa_estimates = []

        for peak in peaks:
            phase_diffs = []
            for i in range(1, num_antennas):
                phase_diff = np.angle(mat[i, :, peak]) - np.angle(mat[0, :, peak])
                phase_diffs.append(np.mean(phase_diff))
            
            phase_diffs = np.array(phase_diffs)
            sin_theta = phase_diffs * wavelength / (2 * np.pi * antenna_distance)
            sin_theta = np.clip(sin_theta, -1, 1)  
            theta = np.arcsin(sin_theta)
            aoa_estimates.append(np.degrees(theta))

        return aoa_estimates

def run_presence_detection(radar_data):
    config = radar_data.config
    algo = PresenceAlgo(config.chirp.num_samples, config.num_chirps)

    antenna_distance = 0.0025  # in meters
    wavelength = 3e8 / ((config.chirp.start_frequency_Hz + config.chirp.end_frequency_Hz) / 2)

    while True:
        try:
            frame_contents = radar_data.get_latest_frame()
            if frame_contents is not None:
                num_rx_antennas = frame_contents.shape[0]
                presence_detected = False
                total_num_persons = 0

                aoa_estimates_all = []

                for i in range(num_rx_antennas):
                    frame = frame_contents[i]

                    mat = frame[:, :]

                    state = algo.presence(mat)

                    if state.presence:
                        presence_detected = True

                    total_num_persons += state.num_persons

                    if state.num_persons > 0:
                        aoa_estimates = algo.estimate_aoa(frame_contents, state.peaks, antenna_distance, wavelength)
                        aoa_estimates_all.extend(aoa_estimates)

                print(f"Presence: {presence_detected}")
                print(f"Number of persons: {total_num_persons}")

        except KeyboardInterrupt:
            print("Program stopped by user.")
            break
        except Exception as e:
            print(f"Error occurred: {e}")
            break

if __name__ == "__main__":

    radar_data = None
    try:
        initialize_radar()
        radar_data = get_radar_data()
        run_presence_detection(radar_data)
    except Exception as e:
        print(f"Error initializing radar: {e}")
    finally:
        if radar_data is not None:
            radar_data.stop()