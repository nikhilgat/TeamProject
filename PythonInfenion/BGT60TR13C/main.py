import argparse
import numpy as np
from scipy import signal, constants
from scipy.signal import butter, sosfilt
from collections import deque
from ifxAvian import Avian

from fft_spectrum import fft_spectrum
from heartratesense.Peakcure import peakcure
from heartratesense.Diffphase import diffphase
from heartratesense.IIR_Heart import iir_heart
from heartratesense.PeakHeart import peakheart

def iir_breath(n: int, phase: np.ndarray):
    fs = 20  # Sampling rate is 20Hz
    f1 = 0.1 / (fs/2)  # Normalized passband cutoff frequency
    f2 = 0.5 / (fs/2)  # Normalized stopband cutoff frequency
    # Design Butterworth IIR filter
    sos = butter(n, [f1, f2], btype='bandpass', output='sos')
    res = sosfilt(sos, phase)
    return res

def peakbreath(data_in):
    breath_start_freq_index = 5  # Starting index for breath frequency range
    breath_end_freq_index = 20  # Ending index for breath frequency range
    p_peak_values = np.zeros(128)  # To store peak values
    p_peak_index = np.zeros(128)  # To store peak indices
    max_num_peaks_spectrum = 4  # Maximum allowed number of peaks
    num_peaks = 0

    for i in range(breath_start_freq_index, breath_end_freq_index):
        if data_in[i] > data_in[i - 1] and data_in[i] > data_in[i + 1]:
            p_peak_index[num_peaks] = i
            p_peak_values[num_peaks] = data_in[i]
            num_peaks += 1
    if num_peaks < max_num_peaks_spectrum:
        index_num_peaks = num_peaks
    else:
        index_num_peaks = max_num_peaks_spectrum

    p_peak_index_sorted = np.zeros(index_num_peaks)
    if index_num_peaks != 0:
        for i in range(index_num_peaks):
            idx = np.argmax(p_peak_values)
            p_peak_index_sorted[i] = idx
            p_peak_values[idx] = 0
        max_index_breath_spect = p_peak_index[int(p_peak_index_sorted[0])]
    else:
        max_index_breath_spect = np.argmax(data_in[breath_start_freq_index:breath_end_freq_index])

    res = 60.0 * (max_index_breath_spect - 1) * 0.0195
    res_index = max_index_breath_spect

    return res, res_index

class HumanPresenceAndDFFTAlgo:
    def __init__(self, config: Avian.DeviceConfig):
        self.num_samples_per_chirp = config.num_samples_per_chirp
        self.num_chirps_per_frame = config.num_chirps_per_frame

        # Compute Blackman-Harris Window matrix over chirp samples(range)
        self.range_window = signal.windows.blackmanharris(self.num_samples_per_chirp).reshape(1, self.num_samples_per_chirp)

        bandwidth_hz = abs(config.end_frequency_Hz - config.start_frequency_Hz)
        fft_size = self.num_samples_per_chirp * 2
        self.range_bin_length = constants.c / (2 * bandwidth_hz * fft_size / self.num_samples_per_chirp)

        # Algorithm Parameters
        self.detect_start_sample = self.num_samples_per_chirp // 8
        self.detect_end_sample = self.num_samples_per_chirp // 2

        self.threshold_presence = 0.1

        self.alpha_slow = 0.001
        self.alpha_med = 0.05
        self.alpha_fast = 0.6

        self.slow_avg = None
        self.fast_avg = None

        # Initialize state
        self.presence_status = False
        self.first_run = True

    def human_presence_and_dfft(self, data_in):
        # Copy values into local variables to keep names short
        alpha_slow = self.alpha_slow
        alpha_med = self.alpha_med
        alpha_fast = self.alpha_fast

        # Calculate range fft spectrum of the frame
        range_fft = fft_spectrum(data_in, self.range_window)

        # Average absolute FFT values over number of chirps
        fft_spec_abs = abs(range_fft)
        fft_norm = np.divide(fft_spec_abs.sum(axis=0), self.num_chirps_per_frame)

        skip = 8
        max_index = np.argmax(fft_norm[skip:])
        dist = self.range_bin_length * (max_index + skip)

        # Presence sensing
        if self.first_run:  # Initialize averages
            self.slow_avg = fft_norm
            self.fast_avg = fft_norm
            self.first_run = False

        alpha_used = alpha_med if not self.presence_status else alpha_slow
        self.slow_avg = self.slow_avg * (1 - alpha_used) + fft_norm * alpha_used
        self.fast_avg = self.fast_avg * (1 - alpha_fast) + fft_norm * alpha_fast
        data = self.fast_avg - self.slow_avg

        self.presence_status = np.max(data[self.detect_start_sample:self.detect_end_sample]) > self.threshold_presence

        return self.presence_status, range_fft

def parse_program_arguments(description, def_nframes, def_frate):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-n', '--nframes', type=int, default=def_nframes,
                        help=f"number of frames, default {str(def_nframes)}")
    parser.add_argument('-f', '--frate', type=int, default=def_frate,
                        help=f"frame rate in Hz, default {str(def_frate)}")
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_program_arguments(
        '''Derives presence and peeking information from Radar Data''',
        def_nframes=300,
        def_frate=20)

    config = Avian.DeviceConfig(
        sample_rate_Hz=2e6,  # ADC sample rate of 2MHz
        rx_mask=1,  # RX antenna 1 activated
        tx_mask=1,  # TX antenna 1 activated
        tx_power_level=31,  # TX power level of 31
        if_gain_dB=33,  # 33dB if gain
        start_frequency_Hz=58e9,  # start frequency: 58.0 GHz
        end_frequency_Hz=63.5e9,  # end frequency: 63.5 GHz
        num_samples_per_chirp=256,  # 256 samples per chirp
        num_chirps_per_frame=1,  # 32 chirps per frame
        chirp_repetition_time_s=0.000400,  # Chirp repetition time (or pulse repetition time) of 150us
        frame_repetition_time_s=1 / args.frate,  # Frame repetition time default 0.005s (frame rate of 200Hz)
        mimo_mode="off")  # MIMO disabled

    # Connect to an Avian radar sensor
    with Avian.Device() as device:
        device.set_config(config)
        algo = HumanPresenceAndDFFTAlgo(config)
        q = deque()
        while True:
            frame = device.get_next_frame()
            frame = frame[0, 0, :]

            q.append(frame)
            if len(q) == args.nframes:
                data = np.array(q)
                presence, dfft_data = algo.human_presence_and_dfft(data)
                
                # Extract range-bin phase and unwrap phase
                rang_bin, phase, phase_unwrap = peakcure(dfft_data)
                
                # Compute phase difference
                diff_phase = diffphase(phase_unwrap)
                
                # Perform sliding average filtering
                phase_remove = np.convolve(diff_phase, np.ones(5)/5, 'same')
                
                # Filter breath signal using IIR Butterworth bandpass filter
                breath_wave = iir_breath(4, phase_remove)
                
                # Filter heart signal
                heart_wave = iir_heart(8, phase_remove)

                # Compute FFT for breath and heart signals
                breath_fre = np.abs(np.fft.fft(breath_wave)) ** 2
                heart_fre = np.abs(np.fft.fftshift(np.fft.fft(heart_wave)))

                breath_rate, maxIndexBreathSpect = peakbreath(breath_fre)
                heart_rate = peakheart(heart_fre, maxIndexBreathSpect)

                print(f"Breath rate: {breath_rate}, Heart rate: {heart_rate}")
                q.pop()
