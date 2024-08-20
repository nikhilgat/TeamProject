'''

To run this usecase, place the Usecase outside the folder.

'''


from binascii import Error
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.image import imread
from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp
from helpers.DigitalBeamForming import DigitalBeamForming
from helpers.DopplerAlgo import DopplerAlgo
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from collections import deque


class LivePlot:
    def __init__(self, max_angle_degrees: float, max_range_m: float, image_path: str, marker_path: str):
        self.max_angle_degrees = max_angle_degrees
        self.max_range_m = max_range_m
        self.scatter = None
        self.marker_image = imread(marker_path)

        self.fig, self.ax = plt.subplots(nrows=1, ncols=1, figsize=(10, 8))
        self.fig.canvas.manager.set_window_title("Range-Angle Detection")
        self.fig.canvas.mpl_connect('close_event', self.close)
        
        self.is_window_open = True
        self.ax.set_xlim(-self.max_angle_degrees, self.max_angle_degrees)
        self.ax.set_ylim(0, self.max_range_m)
        self.ax.axis('off') 
        self.fig.tight_layout()
        
        self.set_background_image(image_path)
        
        self.history_length = 7  
        self.history = deque(maxlen=self.history_length)

    def set_background_image(self, image_path):
        img = imread(image_path)
        self.ax.imshow(img, extent=[-self.max_angle_degrees, self.max_angle_degrees, 0, self.max_range_m],
                        aspect='auto', alpha=0.5)
        self.ax.set_xlim(-self.max_angle_degrees, self.max_angle_degrees)
        self.ax.set_ylim(0, self.max_range_m)
        self.fig.canvas.draw()

    def draw(self, angle: float, distance: float):
        if self.is_window_open:
            if self.scatter:
                self.scatter.remove()

            imagebox = OffsetImage(self.marker_image, zoom=0.05)
            ab = AnnotationBbox(imagebox, (angle, self.max_range_m - distance), frameon=False)
            self.scatter = self.ax.add_artist(ab)

            self.fig.canvas.draw()
            self.fig.canvas.flush_events()

    def close(self, event=None):
        if not self.is_closed():
            self.is_window_open = False
            plt.close(self.fig)
            plt.close('all')
            print('Application closed!')

    def is_closed(self):
        return not self.is_window_open

def presence_map():
    num_beams = 27
    max_angle_degrees = 40
    image_path = 'C:/Users/nikhi/Documents/Projekt/TeamProject/PythonInfenion/BGT60TR13C/assets/bkg.jpg' 
    marker_path = 'C:/Users/nikhi/Documents/Projekt/TeamProject/PythonInfenion/BGT60TR13C/assets/vect.png'
    
    config = FmcwSimpleSequenceConfig(
        frame_repetition_time_s=0.5,  
        chirp_repetition_time_s=0.001,  
        num_chirps=128,
        tdm_mimo=False,  
        chirp=FmcwSequenceChirp(
            start_frequency_Hz=60e9,
            end_frequency_Hz=61.5e9,  
            sample_rate_Hz=1e6,
            num_samples=128,
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
        plot = LivePlot(max_angle_degrees, max_range_m, image_path, marker_path)

        plt.show(block=False)
        
        history = deque(maxlen=7)

        while not plot.is_closed():
            try:
                frame_contents = device.get_next_frame()
                frame = frame_contents[0]

                rd_spectrum = np.zeros((config.chirp.num_samples, 2 * config.num_chirps, num_rx_antennas), dtype=complex)
                beam_range_energy = np.zeros((config.chirp.num_samples, num_beams))

                for i_ant in range(num_rx_antennas):
                    mat = frame[i_ant, :, :]
                    dfft_dbfs = doppler.compute_doppler_map(mat, i_ant)
                    rd_spectrum[:, :, i_ant] = dfft_dbfs

                rd_beam_formed = dbf.run(rd_spectrum)
                for i_beam in range(num_beams):
                    doppler_i = rd_beam_formed[:, :, i_beam]
                    beam_range_energy[:, i_beam] += np.linalg.norm(doppler_i, axis=1) / np.sqrt(num_beams)
                
                history.append(beam_range_energy)
                averaged_beam_range_energy = np.mean(history, axis=0)
                max_energy = np.max(averaged_beam_range_energy)
                
                scale = 150
                averaged_beam_range_energy = scale * (averaged_beam_range_energy / max_energy - 1)
                
                r_idx, a_idx = np.unravel_index(averaged_beam_range_energy.argmax(), averaged_beam_range_energy.shape)
                angle_degrees = np.linspace(-max_angle_degrees, max_angle_degrees, num_beams)[a_idx]
                distance = r_idx * max_range_m / config.chirp.num_samples

                plot.draw(angle_degrees, distance)

            except Error as e:
                if e.code == Error.FRAME_ACQUISITION_FAILED:
                    print("Frame dropped. Continuing...")
                    continue
                else:
                    print(f"Error occurred: {e}")
                    break

        plot.close()

if __name__ == '__main__':
    presence_map()