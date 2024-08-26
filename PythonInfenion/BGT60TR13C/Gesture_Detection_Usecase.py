import argparse
import numpy as np
import time
from radar_data_acquisition import initialize_radar, get_radar_data
from helpers.DopplerAlgo import DopplerAlgo

def parse_program_arguments(description, def_frate):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-f', '--frate', type=int, default=def_frate,
                        help="frame rate in Hz, default " + str(def_frate))
    return parser.parse_args()

def linear_to_dB(x):
    return 20 * np.log10(abs(x))

class GestureDetectionAlgo:
    def __init__(self, num_samples, num_chirps, chirp_repetition_time_s, start_frequency_Hz):
        self.num_samples = num_samples
        self.num_chirps = num_chirps
        self.chirp_repetition_time_s = chirp_repetition_time_s
        self.start_frequency_Hz = start_frequency_Hz

    def detect_gesture(self, radar_data):
        frame = radar_data.get_latest_frame()
        if frame is None:
            return "No Gesture Detected"
        
        gesture = self.analyze_frame(frame)
        return gesture

    def analyze_frame(self, frame):

        frame = np.array(frame)
        frame_sum = np.sum(frame)
        
        if frame_sum > 10000:
            return "Wave"
        elif frame_sum > 5000:
            return "Swipe"
        elif frame_sum > 2000:
            return "Circle"
        else:
            return "No Gesture Detected"

if __name__ == '__main__':
    args = parse_program_arguments(
        '''Processes radar data and outputs detections to terminal''',
        def_frate=5)

    last_detection_time = 0
    detection_suppress_time = 1

    initialize_radar()
    radar_acquisition = get_radar_data()

    while radar_acquisition.get_latest_frame() is None:
        time.sleep(0.1)

    config = radar_acquisition.config
    
    num_rx_antennas = bin(config.chirp.rx_mask).count('1')

    doppler = DopplerAlgo(config.chirp.num_samples, config.num_chirps, num_rx_antennas)
    gesture_algo = GestureDetectionAlgo(config.chirp.num_samples, config.num_chirps,
                                         config.chirp_repetition_time_s, config.chirp.start_frequency_Hz)

    print("Processing radar data. Press Ctrl+C to stop.")
    try:
        while True:
            frame_data = radar_acquisition.get_latest_frame()
            if frame_data is not None:
                detection_occurred = False
                for i_ant in range(num_rx_antennas):
                    mat = frame_data[i_ant, :, :]
                    
                    dfft_dbfs = linear_to_dB(doppler.compute_doppler_map(mat, i_ant))
                    if np.any(dfft_dbfs > -64):
                        detection_occurred = True
                        break

                gesture = gesture_algo.detect_gesture(radar_acquisition)
                
                if detection_occurred:
                    current_time = time.time()
                    if current_time - last_detection_time > detection_suppress_time:
                        print("Assistance Required")
                        last_detection_time = current_time
                
                if gesture != "No Gesture Detected":
                    print(f"Detected Gesture: {gesture}")
            
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nProgram terminated by user.")

    finally:
        radar_acquisition.stop()

    print("Program finished.")
