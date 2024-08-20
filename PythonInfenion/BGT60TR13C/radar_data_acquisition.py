import threading
import time
from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwSequenceChirp

class RadarDataAcquisition:
    def __init__(self, config):
        self.config = config
        self.device = None
        self.latest_frame = None
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        self.device = DeviceFmcw()
        print(f"Radar SDK Version: {get_version_full()}")
        print("Sensor: " + str(self.device.get_sensor_type()))

        sequence = self.device.create_simple_sequence(self.config)
        self.device.set_acquisition_sequence(sequence)

        self.running = True
        self.acquisition_thread = threading.Thread(target=self._acquire_data)
        self.acquisition_thread.start()

    def _acquire_data(self):
        while self.running:
            frame_contents = self.device.get_next_frame()
            with self.lock:
                self.latest_frame = frame_contents[0]

    def get_latest_frame(self):
        with self.lock:
            return self.latest_frame

    def stop(self):
        self.running = False
        if self.acquisition_thread:
            self.acquisition_thread.join()
        if self.device:
            self.device.close()

radar_data = None

def initialize_radar():
    global radar_data
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
    radar_data = RadarDataAcquisition(config)
    radar_data.start()

def get_radar_data():
    return radar_data