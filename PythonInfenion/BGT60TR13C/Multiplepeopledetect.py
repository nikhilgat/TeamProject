from aifc import Error
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.image import imread
from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp
from helpers.DigitalBeamForming import DigitalBeamForming
from helpers.DopplerAlgo import DopplerAlgo
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from scipy.signal import find_peaks
from collections import namedtuple
from scipy import signal
from helpers.fft_spectrum import fft_spectrum

class PresenceAntiPeekingAlgo:
    def __init__(self, num_samples_per_chirp, num_chirps_per_frame):
        """Presence and Anti-Peeking Algorithm"""
        self.num_samples_per_chirp = num_samples_per_chirp
        self.num_chirps_per_frame = num_chirps_per_frame

        # Algorithm Parameters
        self.detect_start_sample = num_samples_per_chirp // 8
        self.detect_end_sample = num_samples_per_chirp // 2
        self.peek_start_sample = num_samples_per_chirp // 2
        self.peek_end_sample = num_samples_per_chirp

        self.threshold_presence = 0.0007
        self.threshold_peeking = 0.0006

        self.alpha_slow = 0.001
        self.alpha_med = 0.05
        self.alpha_fast = 0.6

        # Initialize state
        self.presence_status = False
        self.peeking_status = False
        self.first_run = True

        # Use Blackmann-Harris as window function
        self.window = signal.windows.blackmanharris(num_samples_per_chirp).reshape(1, num_samples_per_chirp)

    def presence(self, mat):
        """Run the presence and anti-peeking algorithm on the current frame."""
        alpha_slow = self.alpha_slow
        alpha_med = self.alpha_med
        alpha_fast = self.alpha_fast

        # Compute range FFT
        range_fft = fft_spectrum(mat, self.window)

        # Average absolute FFT values over number of chirps
        fft_spec_abs = abs(range_fft)
        fft_norm = np.divide(fft_spec_abs.sum(axis=0), self.num_chirps_per_frame)

        # Presence sensing
        if self.first_run:  # initialize averages
            self.slow_avg = fft_norm
            self.fast_avg = fft_norm
            self.slow_peek_avg = fft_norm
            self.first_run = False

        if self.presence_status == False:
            alpha_used = alpha_med
        else:
            alpha_used = alpha_slow

        self.slow_avg = self.slow_avg * (1 - alpha_used) + fft_norm * alpha_used
        self.fast_avg = self.fast_avg * (1 - alpha_fast) + fft_norm * alpha_fast
        data = self.fast_avg - self.slow_avg

        self.presence_status = np.max(data[self.detect_start_sample:self.detect_end_sample]) > self.threshold_presence

        # Peeking sensing
        if self.peeking_status == False:
            alpha_used = self.alpha_med
        else:
            alpha_used = self.alpha_slow

        self.slow_peek_avg = self.slow_peek_avg * (1 - alpha_used) + fft_norm * alpha_used
        data_peek = self.fast_avg - self.slow_peek_avg

        self.peeking_status = np.max(data_peek[self.peek_start_sample:self.peek_end_sample]) > self.threshold_peeking

        # Peak detection to count number of persons
        peaks, _ = find_peaks(data[self.detect_start_sample:self.detect_end_sample], height=self.threshold_presence)
        num_persons = len(peaks)

        return namedtuple("state", ["presence", "peeking", "num_persons", "peaks", "data"])(self.presence_status, self.peeking_status, num_persons, peaks, data)

class LivePlot:
    def __init__(self, max_angle_degrees: float, max_range_m: float, image_path: str, marker_path: str):
        self.max_angle_degrees = max_angle_degrees
        self.max_range_m = max_range_m
        self.scatter = []
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

    def draw(self, detections):
        if self._is_window_open:
            for scatter in self.scatter:
                scatter.remove()
            self.scatter.clear()

            for angle, distance in detections:
                imagebox = OffsetImage(self.marker_image, zoom=0.05)  
                ab = AnnotationBbox(imagebox, (angle, self.max_range_m - distance), frameon=False)  
                self.scatter.append(self._ax.add_artist(ab))

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
        algo = PresenceAntiPeekingAlgo(config.chirp.num_samples, config.num_chirps)

        while not plot.is_closed():
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

                plot.draw(detections)

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
