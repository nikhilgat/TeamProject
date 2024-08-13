from binascii import Error
import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os
import threading
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp
from Multiplepeopledetect import PresenceAntiPeekingAlgo
from helpers.DigitalBeamForming import DigitalBeamForming
from helpers.DopplerAlgo import DopplerAlgo
from scipy.signal import find_peaks
from scipy import signal
from helpers.fft_spectrum import fft_spectrum
import numpy as np

script_dir = 'C:/Users/nikhi/Documents/Projekt/TeamProject/PythonInfenion/BGT60TR13C'  # Change with your path
os.chdir(script_dir)

stop_event = threading.Event()

def run_script1():
    try:
        subprocess.run([sys.executable, 'raw_data.py'], check=True)
        messagebox.showinfo("Success", "Script 1 executed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Script 1 failed: {e}")

def run_script2():
    stop_event.clear()
    threading.Thread(target=presence_map_gui).start()

def run_script3():
    stop_event.clear()
    threading.Thread(target=run_presence_detection).start()

def run_presence_detection():
    presence_script = os.path.join(script_dir, 'Testingfile.py')
    process = subprocess.Popen([sys.executable, presence_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    for line in process.stdout:
        if stop_event.is_set():
            process.terminate()
            break
        if ',' in line:
            presence_status, peeking_status = line.strip().split(',')
            presence_status = presence_status == 'True'
            peeking_status = peeking_status == 'True'
            gui.update_labels(presence_status, peeking_status)
    
    process.stdout.close()
    process.stderr.close()
    process.wait()

def stop_script():
    stop_event.set()
    messagebox.showinfo("Info", "Stop signal sent!")

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

button1 = tk.Button(top_frame, text="Script 1", command=run_script1, **button_style)
button1.pack(side=tk.LEFT, padx=20)

button2 = tk.Button(top_frame, text="Script 2", command=run_script2, **button_style)
button2.pack(side=tk.LEFT, padx=20)

button3 = tk.Button(top_frame, text="Script 3", command=run_script3, **button_style)
button3.pack(side=tk.LEFT, padx=20)

stop_button = tk.Button(top_frame, text="Stop Script", command=stop_script, **button_style)
stop_button.pack(side=tk.LEFT, padx=20)

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
        self.plot_canvas = None

    def update_labels(self, presence_status, peeking_status):
        self.label_presence.config(text=f"Presence: {'Detected' if presence_status else 'Not Detected'}")
        self.label_peeking.config(text=f"Peeking: {'Detected' if peeking_status else 'Not Detected'}")
        root.update_idletasks()

    def draw_plot(self, figure):
        if self.plot_canvas:
            self.plot_canvas.get_tk_widget().pack_forget()
        self.plot_canvas = FigureCanvasTkAgg(figure, master=plot_frame)
        self.plot_canvas.draw()
        self.plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=1)

gui = RadarGUI(root)

def presence_map_gui():
    num_beams = 27
    max_angle_degrees = 40
    image_path = 'assets/bkg.jpg' 
    marker_path = 'assets/vect.png'

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

        chirp_loop = sequence.loop.sub_sequence.contents
        metrics = device.metrics_from_sequence(chirp_loop)
        max_range_m = metrics.max_range_m
        print("Maximum range:", max_range_m)

        chirp = chirp_loop.loop.sub_sequence.contents.chirp
        num_rx_antennas = bin(chirp.rx_mask).count('1')

        doppler = DopplerAlgo(config.chirp.num_samples, config.num_chirps, num_rx_antennas)
        dbf = DigitalBeamForming(num_rx_antennas, num_beams=num_beams, max_angle_degrees=max_angle_degrees)
        algo = PresenceAntiPeekingAlgo(config.chirp.num_samples, config.num_chirps)

        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(10, 8))
        ax.set_xlim(-max_angle_degrees, max_angle_degrees)
        ax.set_ylim(0, max_range_m)
        ax.axis('off')  # Hide axis

        # Load and set custom background image
        img = plt.imread(image_path)
        ax.imshow(img, extent=[-max_angle_degrees, max_angle_degrees, 0, max_range_m], aspect='auto', alpha=0.5)  # Adjust alpha as needed
        
        gui.draw_plot(fig)

        while not stop_event.is_set():
            try:
                frame_contents = device.get_next_frame()
                frame = frame_contents[0]

                rd_spectrum = np.zeros((config.chirp.num_samples, 2 * config.num_chirps, num_rx_antennas), dtype=complex)
                beam_range_energy = np.zeros((config.chirp.num_samples, num_beams))

                detections = []
                for i_ant in range(num_rx_antennas):
                    mat = frame[i_ant, :, :]
                    dfft_dbfs = doppler.compute_doppler_map(mat, i_ant)
                    rd_spectrum[:, :, i_ant] = dfft_dbfs

                    presence_status, peeking_status, num_persons, peaks, data = algo.presence(mat)

                    if presence_status:
                        for peak in peaks:
                            angle_degrees = np.linspace(-max_angle_degrees, max_angle_degrees, num_beams)[peak]
                            range_m = (peak / config.chirp.num_samples) * max_range_m
                            detections.append((angle_degrees, range_m))

                ax.clear()
                ax.set_xlim(-max_angle_degrees, max_angle_degrees)
                ax.set_ylim(0, max_range_m)
                ax.imshow(img, extent=[-max_angle_degrees, max_angle_degrees, 0, max_range_m], aspect='auto', alpha=0.5)
                for angle, distance in detections:
                    imagebox = OffsetImage(plt.imread(marker_path), zoom=0.05)  
                    ab = AnnotationBbox(imagebox, (angle, max_range_m - distance), frameon=False)  
                    ax.add_artist(ab)

                gui.draw_plot(fig)

            except Error as e:
                if e.code == Error.FRAME_ACQUISITION_FAILED:
                    print("Frame dropped. Continuing...")
                    continue
                else:
                    print(f"Error occurred: {e}")
                    break

        plt.close(fig)

button2.config(command=presence_map_gui)

root.mainloop()
