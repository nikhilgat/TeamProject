from aifc import Error
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp
from helpers.DigitalBeamForming import DigitalBeamForming
from helpers.DopplerAlgo import DopplerAlgo

class SegmentPlot:
    def __init__(self, max_angle_degrees: float):
        self.max_angle_degrees = max_angle_degrees
        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.fig.canvas.manager.set_window_title("Segmented Range-Angle Detection")
        self.fig.canvas.mpl_connect('close_event', self.close)
        
        self.is_window_open = True

        # Define 6 segments across the angle range
        self.num_segments = 8
        self.segments = np.linspace(-self.max_angle_degrees, self.max_angle_degrees, self.num_segments + 1)
        self.bars = self.ax.bar(self.segments[:-1], np.zeros(self.num_segments), width=np.diff(self.segments), align='edge', color='blue', alpha=0.5)   

        self.ax.set_xlim(-self.max_angle_degrees, self.max_angle_degrees)
        self.ax.set_ylim(0, 1)  # Normalize the height to 1
        self.ax.axis('off')

        self.fig.tight_layout()

        # Queue to store recent angle indices for moving average
        self.angle_history = deque(maxlen=7)

    def update(self, angle: float):
        # Determine which segment the detected angle falls into
        segment_idx = np.digitize([angle], self.segments) - 1

        # Update the history of detected segments
        self.angle_history.append(segment_idx)

        # Compute the moving average of the detected segment indices
        avg_segment_idx = int(np.round(np.mean(self.angle_history)))

        # Highlight the corresponding segment
        for idx, bar in enumerate(self.bars):
            if idx == avg_segment_idx:
                bar.set_height(1)  # Full height for detected segment
                bar.set_visible(True)
            else:
                bar.set_height(0)  # Hide the non-detected segments
                bar.set_visible(False)

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
    max_angle_degrees = 60
    config = FmcwSimpleSequenceConfig(
        frame_repetition_time_s=0.5,
        chirp_repetition_time_s=0.001,
        num_chirps=128,
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
        dbf = DigitalBeamForming(num_rx_antennas, num_beams=27, max_angle_degrees=max_angle_degrees)
        plot = SegmentPlot(max_angle_degrees)

        plt.show(block=False)

        while not plot.is_closed():
            try:
                frame_contents = device.get_next_frame()
                frame = frame_contents[0]

                rd_spectrum = np.zeros((config.chirp.num_samples, 2 * config.num_chirps, num_rx_antennas), dtype=complex)
                beam_range_energy = np.zeros((config.chirp.num_samples, 27))

                for i_ant in range(num_rx_antennas):
                    mat = frame[i_ant, :, :]
                    dfft_dbfs = doppler.compute_doppler_map(mat, i_ant)
                    rd_spectrum[:, :, i_ant] = dfft_dbfs

                rd_beam_formed = dbf.run(rd_spectrum)
                for i_beam in range(27):
                    doppler_i = rd_beam_formed[:, :, i_beam]
                    beam_range_energy[:, i_beam] += np.linalg.norm(doppler_i, axis=1) / np.sqrt(27)

                max_row, max_col = np.unravel_index(beam_range_energy.argmax(), beam_range_energy.shape)
                angle_degrees = np.linspace(-max_angle_degrees, max_angle_degrees, 27)[max_col]

                plot.update(angle_degrees)

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
