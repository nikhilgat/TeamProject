from aifc import Error
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.image import imread
from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp
from helpers.DigitalBeamForming import DigitalBeamForming
from helpers.DopplerAlgo import DopplerAlgo
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

class LivePlot:
    def __init__(self, max_angle_degrees: float, max_range_m: float, image_path: str, marker_path: str):
        self.max_angle_degrees = max_angle_degrees
        self.max_range_m = max_range_m
        self.scatter = None
        self.marker_image = imread(marker_path)

        plt.ion()
        self._fig, self._ax = plt.subplots(nrows=1, ncols=1, figsize=(10, 8))
        self._fig.canvas.manager.set_window_title("Range-Angle Detection")
        self._fig.canvas.mpl_connect('close_event', self.close)
        
        self._is_window_open = True
        self._ax.set_xlim(-self.max_angle_degrees, self.max_angle_degrees)
        self._ax.set_ylim(0, self.max_range_m)
        self._ax.axis('off')  # Hide axis
        self._fig.tight_layout()
        
        # Load and set custom background image
        self.set_background_image(image_path)
        
        plt.show(block=False)

    def set_background_image(self, image_path):
        # Load and flip image
        img = imread(image_path)
        #img_flipped = np.flipud(img)  # Flip the image vertically
        
        # Display flipped image behind plot
        self._ax.imshow(img, extent=[-self.max_angle_degrees, self.max_angle_degrees, 0, self.max_range_m],
                        aspect='auto', alpha=0.5)  # Adjust alpha as needed
        
        # Adjust plot limits to fit image
        self._ax.set_xlim(-self.max_angle_degrees, self.max_angle_degrees)
        self._ax.set_ylim(0, self.max_range_m)
        
        self._fig.canvas.draw()

    def draw(self, angle: float, distance: float):
        if self._is_window_open:
            if self.scatter:
                self.scatter.remove()

            imagebox = OffsetImage(self.marker_image, zoom=0.05)  
            ab = AnnotationBbox(imagebox, (angle, self.max_range_m - distance), frameon=False)  
            self.scatter = self._ax.add_artist(ab)

            self._fig.canvas.draw()
            self._fig.canvas.flush_events()

    def close(self, event=None):
        if not self.is_closed():
            self._is_window_open = False
            plt.close(self._fig)
            plt.close('all')
            print('Application closed!')

    def is_closed(self):
        return not self._is_window_open

def presence_map():
    num_beams = 27
    max_angle_degrees = 40
    image_path = '/Users/nikhi/Documents/Projekt/TeamProject/PythonInfenion/BGT60TR13C/assets/bkg.jpg' 
    marker_path = '/Users/nikhi/Documents/Projekt/TeamProject/PythonInfenion/BGT60TR13C/assets/vect.png'
    
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
        plot = LivePlot(max_angle_degrees, max_range_m, image_path, marker_path)

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

                max_row, max_col = np.unravel_index(beam_range_energy.argmax(), beam_range_energy.shape)
                angle_degrees = np.linspace(-max_angle_degrees, max_angle_degrees, num_beams)[max_col]
                range_m = (max_row / config.chirp.num_samples) * max_range_m

                plot.draw(angle_degrees, range_m)

            except Error as e:
                if e.code == Error.FRAME_ACQUISITION_FAILED:
                    print("Frame dropped. Continuing...")
                    continue
                else:
                    print(f"Error occurred: {e}")
                    break

        plot.close()

if __name__ == "__main__":
    presence_map()
