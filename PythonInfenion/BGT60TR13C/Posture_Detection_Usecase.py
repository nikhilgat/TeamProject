import tkinter as tk
import threading
import numpy as np
from scipy.signal import find_peaks
from collections import namedtuple
from scipy import signal
from helpers.fft_spectrum import fft_spectrum
from radar_data_acquisition import initialize_radar, get_radar_data

class PostureDetectionAlgo:
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

    def posture(self, mat):
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

class RadarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Radar Posture Classification")
        self.root.geometry("400x300")

        self.status_label = tk.Label(root, text="Status: Initializing...", font=("Arial", 16))
        self.status_label.pack(pady=20)

        self.icon_label = tk.Label(root, text="", font=("Arial", 72))
        self.icon_label.pack(pady=20)

        self.icons = {
            "standing": "🧍",
            "sitting": "🪑",
            "sleeping": "🛌",
            "no_presence": "❌",
            "unknown": "❓"
        }

        self.start_detection()

    def update_status(self, status):
        self.status_label.config(text=f"Status: {status}")
        self.icon_label.config(text=self.icons.get(status.lower(), self.icons["unknown"]))

    def start_detection(self):
        threading.Thread(target=self.run_detection, daemon=True).start()

    def run_detection(self):
        try:
            initialize_radar()
            radar_data = get_radar_data()
            config = radar_data.config

            algo = PostureDetectionAlgo(config.chirp.num_samples, config.num_chirps)

            while True:
                try:
                    frame = radar_data.get_latest_frame()
                    if frame is not None:
                        movement_detected = False

                        for i_ant in range(frame.shape[0]):
                            mat = frame[i_ant, :, :]
                            state = algo.posture(mat)

                            if state.presence:
                                movement_detected = True
                                if len(state.peaks) > 0:
                                    peak_idx = state.peaks[0]
                                    max_range_m = radar_data.device.metrics_from_sequence(radar_data.device.get_acquisition_sequence().loop.sub_sequence.contents).max_range_m
                                    distance = (peak_idx / config.chirp.num_samples) * max_range_m

                                    if distance <= 0.50:
                                        self.root.after(0, self.update_status, "Standing")
                                    elif 0.50 < distance <= 0.70:
                                        self.root.after(0, self.update_status, "Sitting")
                                    elif 0.70 < distance <= 0.90:
                                        self.root.after(0, self.update_status, "Sleeping")
                                else:
                                    self.root.after(0, self.update_status, "Unknown")
                            else:
                                self.root.after(0, self.update_status, "No Presence")

                except Exception as e:
                    print(f"Error occurred: {e}")
                    self.root.after(0, self.update_status, "Error")
                    break

        except Exception as e:
            print(f"Error initializing device: {e}")
            self.root.after(0, self.update_status, "Device Error")

if __name__ == "__main__":
    root = tk.Tk()
    app = RadarGUI(root)
    root.mainloop()