from aifc import Error
import matplotlib.pyplot as plt
import numpy as np
from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp
from helpers.DigitalBeamForming import DigitalBeamForming
from helpers.DopplerAlgo import DopplerAlgo

class LivePlot:
    def __init__(self, max_angle_degrees: float, max_range_m: float):
        self.max_angle_degrees = max_angle_degrees
        self.max_range_m = max_range_m
        self.scatter = None

        plt.ion()
        self._fig, self._ax = plt.subplots(nrows=1, ncols=1, figsize=(10, 8))
        self._fig.canvas.manager.set_window_title("Range-Angle Detection")
        self._fig.canvas.mpl_connect('close_event', self.close)
        
        self._is_window_open = True
        self._ax.set_xlim(-self.max_angle_degrees, self.max_angle_degrees)
        self._ax.set_ylim(0, self.max_range_m)
        # self._ax.set_xlabel("Angle (degrees)")
        # self._ax.set_ylabel("Distance (m)")
        self._ax.set_title("Initializing...")
        self._ax.grid(True)

        self._fig.tight_layout()
        plt.show(block=False)

    def draw(self, angle: float, distance: float, title: str):
        if self._is_window_open:
            if self.scatter:
                self.scatter.remove()
            self.scatter = self._ax.scatter(angle, distance, color='red', s=100)
            self._ax.set_title(title)
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

def run_range_angle_map():
    num_beams = 27
    max_angle_degrees = 60

    config = FmcwSimpleSequenceConfig(
        frame_repetition_time_s=0.5,
        chirp_repetition_time_s=0.001,
        num_chirps=64,
        tdm_mimo=False,
        chirp=FmcwSequenceChirp(
            start_frequency_Hz=60e9,
            end_frequency_Hz=62e9,
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
        plot = LivePlot(max_angle_degrees, max_range_m)

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

                plot.draw(angle_degrees, range_m, 
                          f"Detected entity: angle={angle_degrees:+02.0f}°, range={range_m:.2f}m")

            except Error as e:
                if e.code == Error.FRAME_ACQUISITION_FAILED:
                    print("Frame dropped. Continuing...")
                    continue
                else:
                    print(f"Error occurred: {e}")
                    break

        plot.close()

if __name__ == "__main__":
    run_range_angle_map()