import numpy as np
import matplotlib.pyplot as plt
from scipy import constants
from sklearn.cluster import DBSCAN
import time
from collections import deque

from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp
from ifxradarsdk.common.exceptions import ErrorFrameAcquisitionFailed

from helpers.DigitalBeamForming import DigitalBeamForming
from helpers.DopplerAlgo import DopplerAlgo
from helpers.DistanceAlgo import DistanceAlgo

class Radar3DProcessing:
    def __init__(self, config):
        self.config = config
        self.device = DeviceFmcw()
        self.setup_device()
        
        self.doppler = DopplerAlgo(config.chirp.num_samples, config.num_chirps, self.num_rx_antennas)
        self.dbf = DigitalBeamForming(self.num_rx_antennas, num_beams=27, max_angle_degrees=45)
        self.distance_algo = DistanceAlgo(config.chirp, config.num_chirps)
        
        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        self.consecutive_failures = 0
        self.cooldown_time = 1.0
        self.last_failure_time = 0
        
        self.all_targets = deque(maxlen=20)  # FIFO queue with max length of 20
        
    def setup_device(self):
        sequence = self.device.create_simple_sequence(self.config)
        self.device.set_acquisition_sequence(sequence)
        self.num_rx_antennas = bin(self.config.chirp.rx_mask).count("1")
        print(f"Number of RX antennas: {self.num_rx_antennas}")
        
    def process_frame(self):
        if time.time() - self.last_failure_time < self.cooldown_time:
            print("In cooldown period, skipping frame")
            return None

        max_retries = 3
        for attempt in range(max_retries):
            try:
                frame_contents = self.device.get_next_frame()
                frame = frame_contents[0]
                print(f"Frame shape: {frame.shape}")
                self.consecutive_failures = 0
                break
            except ErrorFrameAcquisitionFailed:
                print(f"Frame acquisition failed. Attempt {attempt + 1}/{max_retries}")
                self.consecutive_failures += 1
                if self.consecutive_failures >= 5:
                    print("Too many consecutive failures. Entering cooldown period.")
                    self.last_failure_time = time.time()
                    return None
                time.sleep(0.05)
            except Exception as e:
                print(f"Unexpected error during frame acquisition: {e}")
                return None
        else:
            print(f"Failed to acquire frame after {max_retries} attempts")
            return None
        
        try:
            rd_spectrum = np.zeros((self.config.chirp.num_samples, 2 * self.config.num_chirps, self.num_rx_antennas), dtype=complex)
            for i_ant in range(self.num_rx_antennas):
                mat = frame[i_ant, :, :]
                rd_spectrum[:, :, i_ant] = self.doppler.compute_doppler_map(mat, i_ant)
            
            rd_beam_formed = self.dbf.run(rd_spectrum)
            
            threshold = np.mean(np.abs(rd_beam_formed)) + 3 * np.std(np.abs(rd_beam_formed))
            detections = np.abs(rd_beam_formed) > threshold
            
            targets = []
            for r, d, b in np.argwhere(detections):
                range_m = r * self.distance_algo.range_bin_length
                doppler_hz = (d - self.config.num_chirps) * (1 / (self.config.chirp_repetition_time_s * self.config.num_chirps))
                angle_rad = np.deg2rad(np.linspace(-45, 45, 27)[b])
                targets.append([range_m, doppler_hz, angle_rad])
            
            if targets:
                clusterer = DBSCAN(eps=0.5, min_samples=3)
                clusters = clusterer.fit_predict(targets)
                
                final_targets = []
                for i in range(max(clusters) + 1):
                    cluster_points = np.array([t for t, c in zip(targets, clusters) if c == i])
                    final_targets.append(np.mean(cluster_points, axis=0))
                
                return np.array(final_targets)
            else:
                return np.array([])
        except Exception as e:
            print(f"Error during frame processing: {e}")
            return None

    def convert_to_cartesian(self, targets):
        x = targets[:, 0] * np.cos(targets[:, 2])
        y = targets[:, 0] * np.sin(targets[:, 2])
        center_frequency_Hz = (self.config.chirp.start_frequency_Hz + self.config.chirp.end_frequency_Hz) / 2
        z = targets[:, 1] * constants.c / (2 * center_frequency_Hz)
        return np.column_stack((x, y, z))
    def visualize_3d(self):
        self.ax.clear()
        if self.all_targets:
            cart_targets = np.vstack(self.all_targets)
            colors = cart_targets[:, 0]  
            scatter = self.ax.scatter(cart_targets[:, 0], cart_targets[:, 1], cart_targets[:, 2], c=colors, cmap='viridis', s=10, alpha=0.6)
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (m/s)')
        self.ax.set_title(f'3D Radar Targets (Last 20 Frames)')
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

if __name__ == "__main__":
    config = FmcwSimpleSequenceConfig(
        frame_repetition_time_s=0.05,
        chirp_repetition_time_s=0.0005,
        num_chirps=64,
        chirp=FmcwSequenceChirp(
            start_frequency_Hz=60e9,
            end_frequency_Hz=61.5e9,
            sample_rate_Hz=1e6,
            num_samples=32,
            rx_mask=7,
            tx_mask=1,
            tx_power_level=31,
            lp_cutoff_Hz=500000,
            hp_cutoff_Hz=80000,
            if_gain_dB=45,
        )
    )

    radar = Radar3DProcessing(config)
    print("Radar processing initialized")

    plt.ion()
    frame_count = 0
    try:
        while True:  # Run indefinitely
            start_time = time.time()
            targets = radar.process_frame()
            if targets is not None and len(targets) > 0:
                cart_targets = radar.convert_to_cartesian(targets)
                radar.all_targets.append(cart_targets)
                radar.visualize_3d()
                frame_count += 1
                print(f"Processed frame {frame_count}")
            
            processing_time = time.time() - start_time
            if processing_time < config.frame_repetition_time_s:
                time.sleep(config.frame_repetition_time_s - processing_time)
            
            if plt.waitforbuttonpress(0.001):
                break
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        plt.ioff()
        plt.savefig('radar_3d_plot.png')
    plt.show()