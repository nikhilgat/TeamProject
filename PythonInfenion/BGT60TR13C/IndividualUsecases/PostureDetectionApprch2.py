import tkinter as tk
import threading
import numpy as np
from collections import deque, Counter
from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp
from helpers.DigitalBeamForming import DigitalBeamForming
from helpers.DopplerAlgo import DopplerAlgo
from binascii import Error

def classify_position(distance, thresholds):
    standing_threshold = thresholds.get('standing', float('inf'))
    sitting_threshold = thresholds.get('sitting', float('inf'))
    sleeping_threshold = thresholds.get('sleeping', float('inf'))
    
    if distance <= standing_threshold:
        return 'standing'
    elif standing_threshold < distance <= sitting_threshold:
        return 'sitting'
    elif sitting_threshold < distance <= sleeping_threshold:
        return 'sleeping'
    else:
        return 'walking'

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
            "walking": "🚶",
            "error": "❗",
            "unknown": "❓" 
        }

        self.start_detection()

    def update_status(self, status, distance=None):
        try:
            status_key = status.lower()
            print(f"Status: {status_key}")
            print(f"Available icons: {self.icons.keys()}")
            
            icon = self.icons.get(status_key, self.icons["unknown"])
            
            status_text = f"Status: {status}"
            if distance is not None:
                status_text += f" (Distance: {distance:.2f} m)"
            
            self.status_label.config(text=status_text)
            self.icon_label.config(text=icon)
        except Exception as e:
            print(f"Unexpected error: {e}")

    def start_detection(self):
        threading.Thread(target=self.run_detection, daemon=True).start()

    def run_detection(self):
        max_angle_degrees = 60
        num_segments = 4
        thresholds = {
            'segment_1': {'standing': 1.70, 'sitting': 2.10, 'sleeping': 2.90},
            'segment_2': {'standing': 1.50, 'sitting': 1.90, 'sleeping': 2.70},
            'segment_3': {'standing': 1.50, 'sitting': 1.90, 'sleeping': 2.70},
            'segment_4': {'standing': 1.70, 'sitting': 2.10, 'sleeping': 2.90},
        }

        config = FmcwSimpleSequenceConfig(
            frame_repetition_time_s=0.5,
            chirp_repetition_time_s=0.001,
            num_chirps=64,
            tdm_mimo=False,
            chirp=FmcwSequenceChirp(
                start_frequency_Hz=60e9,
                end_frequency_Hz=61.5e9,
                sample_rate_Hz=2e6,
                num_samples=128,
                rx_mask=5,
                tx_mask=1,
                tx_power_level=31,
                lp_cutoff_Hz=500000,
                hp_cutoff_Hz=80000,
                if_gain_dB=33,
            )
        )

        angle_history = deque(maxlen=3)
        distance_history = deque(maxlen=3)
        position_history = deque(maxlen=3)

        try:
            with DeviceFmcw() as device:
                print(f"Radar SDK Version: {get_version_full()}")
                print("Sensor: " + str(device.get_sensor_type()))

                sequence = device.create_simple_sequence(config)
                device.set_acquisition_sequence(sequence)

                chirp_loop = sequence.loop.sub_sequence.contents
                metrics = device.metrics_from_sequence(chirp_loop)
                max_range_m = metrics.max_range_m
                print("Maximum range:", max_range_m)

                chirp = chirp_loop.loop.sub_sequence.contents.chirp
                num_rx_antennas = bin(chirp.rx_mask).count('1')

                doppler = DopplerAlgo(config.chirp.num_samples, config.num_chirps, num_rx_antennas)
                dbf = DigitalBeamForming(num_rx_antennas, num_beams=40, max_angle_degrees=max_angle_degrees)

                while True:
                    try:
                        frame_contents = device.get_next_frame()
                        frame = frame_contents[0]

                        rd_spectrum = np.zeros((config.chirp.num_samples, 2 * config.num_chirps, num_rx_antennas), dtype=complex)
                        beam_range_energy = np.zeros((config.chirp.num_samples, 40))

                        for i_ant in range(num_rx_antennas):
                            mat = frame[i_ant, :, :]
                            dfft_dbfs = doppler.compute_doppler_map(mat, i_ant)
                            rd_spectrum[:, :, i_ant] = dfft_dbfs

                        rd_beam_formed = dbf.run(rd_spectrum)
                        for i_beam in range(40):
                            doppler_i = rd_beam_formed[:, :, i_beam]
                            beam_range_energy[:, i_beam] += np.linalg.norm(doppler_i, axis=1) / np.sqrt(40)

                        max_row, max_col = np.unravel_index(beam_range_energy.argmax(), beam_range_energy.shape)
                        angle_degrees = np.linspace(-max_angle_degrees, max_angle_degrees, 40)[max_col]

                        segments = np.linspace(-max_angle_degrees, max_angle_degrees, num_segments + 1)
                        segment_idx = np.digitize([angle_degrees], segments) - 1
                        segment_idx = min(max(segment_idx[0], 0), num_segments - 1)

                        angle_history.append(segment_idx)
                        avg_segment_idx = int(np.round(np.mean(angle_history)))
                        segment_key = f'segment_{avg_segment_idx + 1}'
                        segment_thresholds = thresholds.get(segment_key, {'standing': float('inf'), 'sitting': float('inf'), 'sleeping': float('inf')})

                        peak_idx = np.argmax(beam_range_energy[:, max_col])
                        distance = (peak_idx / config.chirp.num_samples) * max_range_m
                        
                        distance_history.append(distance)
                        avg_distance = np.mean(distance_history)
                        current_position = classify_position(avg_distance, segment_thresholds)
                        position_history.append(current_position)
                        avg_position = Counter(position_history).most_common(1)[0][0]

                        self.root.after(0, self.update_status, avg_position, avg_distance)

                    except Error as e:
                        if e.code == Error.FRAME_ACQUISITION_FAILED:
                            print("Frame dropped. Skipping to next frame...")
                            continue
                        else:
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
