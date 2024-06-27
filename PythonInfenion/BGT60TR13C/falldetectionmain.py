import argparse
from collections import namedtuple
from scipy import signal
from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp
from fft_spectrum import *
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import os
import subprocess
import sys
import falldetectionneu

script_dir = 'C:/Users/nikhi/Documents/Projekt/TeamProject/PythonInfenion/BGT60TR13C'
os.chdir(script_dir)

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

        peaks, _ = signal.find_peaks(fft_norm, height=100)
        self.fall_detected = len(peaks) > 0

        return namedtuple("FallDetection", ["fall_detected"])(self.fall_detected)

def run_fall_detection():
    parser = argparse.ArgumentParser(description='Fall Detection using Infineon Radar')
    parser.add_argument('-n', '--nframes', type=int, default=100, help="number of frames, default 100")
    parser.add_argument('-f', '--frate', type=int, default=5, help="frame rate in Hz, default 5")
    args = parser.parse_args()

    config = FmcwSimpleSequenceConfig(
        frame_repetition_time_s=1 / args.frate,
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
        algo = FallDetectionAlgo(config.chirp.num_samples, config.num_chirps)

        for frame_number in range(args.nframes):
            frame_contents = device.get_next_frame()
            frame = frame_contents[0]
            mat = frame[0, :, :]
            fall_detection = algo.detect_fall(mat)
            print(f"Fall Detected: {fall_detection.fall_detected}")

def run_script3():
    threading.Thread(target=run_fall_detection).start()

root = tk.Tk()
root.title("RADAR GUI")
root.geometry("1000x700")
root.configure(background='#2c3e50')

def exit_fullscreen(event=None):
    root.attributes('-fullscreen', False)

root.bind('<Escape>', exit_fullscreen)

button_style = {
    "font": ("Helvetica", 12, "bold"),
    "background": "#3498db",
    "foreground": "white",
    "borderwidth": 2,
    "relief": "raised",
    "width": 20,
    "height": 2
}

top_frame = tk.Frame(root, background='#2c3e50')
top_frame.pack(side=tk.TOP, fill=tk.X, pady=20)

button3 = tk.Button(top_frame, text="Script 3", command=run_script3, **button_style)
button3.pack(side=tk.LEFT, padx=20)

plot_frame = tk.Frame(root, background='#ecf0f1', bd=2, relief="sunken")
plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=20, pady=20)

label_presence = tk.Label(root, text="Presence: Not Detected", font=("Helvetica", 16), background='#2c3e50', foreground='white')
label_presence.pack(pady=10)
label_peeking = tk.Label(root, text="Peeking: Not Detected", font=("Helvetica", 16), background='#2c3e50', foreground='white')
label_peeking.pack(pady=10)

class RadarGUI:
    def __init__(self, root):
        self.label_presence = label_presence
        self.label_peeking = label_peeking

    def update_labels(self, presence_status, peeking_status):
        self.label_presence.config(text=f"Presence: {'Detected' if presence_status else 'Not Detected'}")
        self.label_peeking.config(text=f"Peeking: {'Detected' if peeking_status else 'Not Detected'}")
        root.update_idletasks()

gui = RadarGUI(root)

root.mainloop()
