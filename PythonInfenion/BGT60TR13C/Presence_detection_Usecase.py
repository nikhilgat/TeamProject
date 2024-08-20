import matplotlib.pyplot as plt
import numpy as np
from collections import deque
from matplotlib.image import imread
from helpers.DigitalBeamForming import DigitalBeamForming
from helpers.DopplerAlgo import DopplerAlgo
import time
import queue
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class PresenceDetectionSignals(QObject):
    update_plot = pyqtSignal(float)

class SegmentPlot(FigureCanvas):
    def __init__(self, max_angle_degrees: float, image_path: str, start_height: float, end_height: float, num_bars: int, margin_ratio: float = 0.1):
        self.fig = Figure(figsize=(8, 8))
        super().__init__(self.fig)
        
        self.ax = self.fig.add_subplot(111)
        self.max_angle_degrees = max_angle_degrees
        self.start_height = start_height
        self.end_height = end_height
        self.num_bars = num_bars

        self.set_background_image(image_path)

        total_angle_range = 2 * self.max_angle_degrees
        margin = margin_ratio * total_angle_range
        adjusted_angle_range = total_angle_range - 2 * margin
        self.segments = np.linspace(-self.max_angle_degrees + margin, self.max_angle_degrees - margin, self.num_bars + 1)

        self.bars = self.ax.bar(self.segments[:-1], np.zeros(self.num_bars), width=np.diff(self.segments), align='edge', color='blue', alpha=0.5)

        self.ax.set_xlim(-self.max_angle_degrees, self.max_angle_degrees)
        self.ax.set_ylim(0, 1)  
        self.ax.axis('off')

        self.fig.tight_layout()

        self.angle_history = deque(maxlen=5)
        self.is_window_open = True
        
        self.draw() 

    def set_background_image(self, image_path):
        img = imread(image_path)
        self.ax.imshow(img, extent=[-self.max_angle_degrees, self.max_angle_degrees, 0, 1],
                       aspect='auto', alpha=0.9)
        self.ax.set_xlim(-self.max_angle_degrees, self.max_angle_degrees)
        self.ax.set_ylim(0, 1)

    def update_angle(self, angle: float):
        segment_idx = np.digitize([angle], self.segments) - 1
        self.angle_history.append(segment_idx)
        avg_segment_idx = int(np.round(np.mean(self.angle_history)))

        for idx, bar in enumerate(self.bars):
            if idx == avg_segment_idx:
                bar.set_height(self.end_height - self.start_height)
                bar.set_y(self.start_height)
                bar.set_visible(True)
            else:
                bar.set_height(0)
                bar.set_visible(False)

        self.draw()

class PresenceDetection:
    def __init__(self, max_angle_degrees: float, image_path: str, start_height: float, end_height: float, num_bars: int, margin_ratio: float):
        self.max_angle_degrees = max_angle_degrees
        self.image_path = image_path
        self.start_height = start_height
        self.end_height = end_height
        self.num_bars = num_bars
        self.margin_ratio = margin_ratio
        
        # These values should match the radar configuration
        self.num_samples = 128
        self.num_chirps = 64
        self.num_rx_antennas = 2
        
        self.doppler = DopplerAlgo(self.num_samples, self.num_chirps, self.num_rx_antennas)
        self.dbf = DigitalBeamForming(self.num_rx_antennas, num_beams=80, max_angle_degrees=max_angle_degrees)
        
        self.plot = None
        self.signals = PresenceDetectionSignals()

    def initialize_plot(self):
        self.plot = SegmentPlot(self.max_angle_degrees, self.image_path, self.start_height, self.end_height, self.num_bars, self.margin_ratio)
        self.signals.update_plot.connect(self.plot.update_angle)
        return self.plot

    def process_frame(self, frame):
        rd_spectrum = np.zeros((self.num_samples, 2 * self.num_chirps, self.num_rx_antennas), dtype=complex)
        beam_range_energy = np.zeros((self.num_samples, 80))

        for i_ant in range(self.num_rx_antennas):
            mat = frame[i_ant, :, :]
            dfft_dbfs = self.doppler.compute_doppler_map(mat, i_ant)
            rd_spectrum[:, :, i_ant] = dfft_dbfs

        rd_beam_formed = self.dbf.run(rd_spectrum)
        for i_beam in range(80):
            doppler_i = rd_beam_formed[:, :, i_beam]
            beam_range_energy[:, i_beam] += np.linalg.norm(doppler_i, axis=1) / np.sqrt(80)

        max_row, max_col = np.unravel_index(beam_range_energy.argmax(), beam_range_energy.shape)
        angle_degrees = np.linspace(-self.max_angle_degrees, self.max_angle_degrees, 80)[max_col]

        return angle_degrees

    def run_presence_detection(self):
        from Radar_Data_Acquisition import get_radar_data
        radar_data = get_radar_data()
        if radar_data is None:
            print("Radar data acquisition not initialized")
            return
        
        while radar_data.running:
            frame = radar_data.get_latest_frame()
            if frame is not None:
                angle_degrees = self.process_frame(frame)
                self.signals.update_plot.emit(angle_degrees)
            time.sleep(0.1)

def run_presence_detection():
    presence_detection = PresenceDetection(
        max_angle_degrees=60,
        image_path='PythonInfenion/BGT60TR13C/assets/topviewbkgcomp.jpg',
        start_height=0.13,
        end_height=0.8785,
        num_bars=8,
        margin_ratio=0.13
    )
    
    return presence_detection

if __name__ == '__main__':
    from Radar_Data_Acquisition import initialize_radar
    initialize_radar()
    run_presence_detection()