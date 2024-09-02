import argparse
import matplotlib.pyplot as plt
import numpy as np
import time 

from ifxradarsdk import get_version_full
from ifxradarsdk.fmcw import DeviceFmcw
from ifxradarsdk.fmcw.types import FmcwSimpleSequenceConfig, FmcwMetrics
from helpers.DopplerAlgo import *

def parse_program_arguments(description, def_nframes, def_frate):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-n', '--nframes', type=int,
                        default=def_nframes, help="number of frames, default " + str(def_nframes))
    parser.add_argument('-f', '--frate', type=int, default=def_frate,
                        help="frame rate in Hz, default " + str(def_frate))
    return parser.parse_args()


def linear_to_dB(x):
    return 20 * np.log10(abs(x))

if __name__ == '__main__':
    args = parse_program_arguments(
        '''Displays range doppler map from Radar Data''',
        def_nframes=5000,
        def_frate=5)

    last_detection_time = 0
    detection_suppress_time = 1
    display_duration = 5
    gesture_detected = False

    with DeviceFmcw() as device:
        print(f"Radar SDK Version: {get_version_full()}")
        print("Sensor: " + str(device.get_sensor_type()))

        num_rx_antennas = device.get_sensor_information()["num_rx_antennas"]

        metrics = FmcwMetrics(
            range_resolution_m=0.15,
            max_range_m=0.7,
            max_speed_m_s=2.45,
            speed_resolution_m_s=0.2,
            center_frequency_Hz=60_750_000_000,
        )

        sequence = device.create_simple_sequence(FmcwSimpleSequenceConfig())
        sequence.loop.repetition_time_s = 1 / args.frate

        chirp_loop = sequence.loop.sub_sequence.contents
        device.sequence_from_metrics(metrics, chirp_loop)

        chirp = chirp_loop.loop.sub_sequence.contents.chirp
        chirp.sample_rate_Hz = 1_000_000
        chirp.rx_mask = (1 << num_rx_antennas) - 1
        chirp.tx_mask = 1
        chirp.tx_power_level = 31
        chirp.if_gain_dB = 33
        chirp.lp_cutoff_Hz = 500000
        chirp.hp_cutoff_Hz = 80000

        device.set_acquisition_sequence(sequence)

        doppler = DopplerAlgo(chirp.num_samples, chirp_loop.loop.num_repetitions, num_rx_antennas)

        for frame_number in range(args.nframes):
            frame_contents = device.get_next_frame()
            frame_data = frame_contents[0]
            data_all_antennas = []
            for i_ant in range(0, num_rx_antennas):
                mat = frame_data[i_ant, :, :]
                dfft_dbfs = linear_to_dB(doppler.compute_doppler_map(mat, i_ant))
                if np.any(dfft_dbfs > -59):
                    current_time = time.time()
                    if current_time - last_detection_time > detection_suppress_time:
                        print("Gesture detected")
                        last_detection_time = current_time
                        gesture_detected = True
                data_all_antennas.append(dfft_dbfs)

            if gesture_detected and time.time() - last_detection_time > display_duration:
                print("No gesture detected")
                gesture_detected = False


