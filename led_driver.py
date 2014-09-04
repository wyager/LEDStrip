# Will Yager
# This Python script sends color/brightness data based on
# ambient sound frequencies to the LEDs.

import pyaudio as pa
import numpy as np
import numpy.fft as fft
import struct
from math import cos, sin, pi
import time
import sys
import serial

audio_stream = pa.PyAudio().open(format=pa.paInt16, \
								channels=1, \
								rate=44100, \
								input=True, \
								frames_per_buffer=512)

# Convert the audio data to numbers, num_samples at a time.
def read_audio(audio_stream, num_samples):
	while True:
		# Read all the input data. 
		samples = audio_stream.read(num_samples) 
		# Convert input data to numbers
		samples = [struct.unpack('<h',samples[2*i:2*i+2])[0] \
									for i in range(num_samples)]
		yield samples

# Convert the audio stream into a stream of FFTs
def to_fft(audio_stream):
	for samples in audio_stream:
		# Take the FFT of the input signal
		frequencies = fft.fft(samples) 
		# Convert from complex to real magnitudes
		frequencies = np.abs(frequencies)
		# Sum negative and positive frequency components
		magnitudes = frequencies[0:len(samples)/2]
		magnitudes[1:] += frequencies[len(samples)/2 + 1:][::-1]
		yield magnitudes

# "Stretch" the FFT to fit the LEDs, and use only the bottom
# 1/decimation of the FFT bins
def scale_to_LEDs(fft_stream, num_leds, decimation):
	for sample in fft_stream:
		# Cut off the higher frequencies we don't care about any more
		sample = sample[0:len(sample)/decimation]
		# How many FFT bins do we want to lump into a single LED?
		scale_factor = len(sample)/num_leds
		# Sum the FFT bins into each LED's value
		led_magnitudes = sample.reshape(num_leds, scale_factor).sum(axis=1)
		yield led_magnitudes

# Inject a certain amount of white noise into the FFT to drown out quiet sounds
def inject_white_noise(fft_stream, baseline):
	for sample in fft_stream:
		yield sample + baseline

# Normalize a data stream so the sum of each array in the stream approaches 1
def normalize_all(data_stream, falloff):
	norm = None
	for data in data_stream:
		norm = sum(data) if norm == None else norm
		norm *= falloff
		norm += sum(data)*(1.0 - falloff)
		data /= norm
		yield data

# Smooth each individual element in the data stream
def smooth(data_stream, falloff):
	smoothed = None
	for data in data_stream:
		smoothed = data if smoothed == None else smoothed
		smoothed *= falloff
		smoothed += data*(1.0 - falloff)
		yield smoothed

# Generates a waveform with range [0,pi/2]
# Based on the sums of sines of the given frequencies
def waveform(frequencies):
	def f(x):
		total = sum([sin(f*2*pi*x)*pi/4 + pi/4 for f in frequencies])
		return total / len(frequencies)
	return f

# Makes a color based on time t
def color(t):
	theta = waveform([2.0/60, 3.0/60])(t)
	phi = waveform([5.0/60, 7.0/60])(t)
	x = sin(theta) * cos(phi)
	y = sin(theta) * sin(phi)
	z = cos(theta)
	return (x,y,z)

# Makes a list of colors. Each LED's color function is offset by 1 second 
def generate_colors(num_leds):
	while True:
		t = time.time()
		yield [color(t+dt) for dt in range(num_leds)]

# Make the components of a color add up to 1
def normalize_colors(color_stream):
	for colors in color_stream:
		yield [(r/(r+g+b), g/(r+g+b), b/(r+g+b)) for r,g,b in colors]

# Multiply each LED's color by its magnitude and a scalar
def multiply_colors(color_stream, magnitude_stream, scalar):
	while True:
		colors = color_stream.next()
		mags = magnitude_stream.next()
		def scale((r,g,b), magnitude):
			magnitude = scalar * magnitude
			return (r*magnitude),(g*magnitude),(b*magnitude)
		yield [scale(color,mag) for color,mag in zip(colors,mags)]

# Max the colors out at the cap value and turn them to integers
def cap_colors(color_stream, cap):
	for colors in color_stream:
		for i in range(len(colors)):
			r,g,b = colors[i]
			if r+g+b > cap:
				total = r+g+b
				r = float(r) / total * cap
				g = float(g) / total * cap
				b = float(b) / total * cap
			r,g,b = int(r),int(g),int(b)
			colors[i] = r,g,b
			assert(r+g+b < 127)
		yield colors


teensy_file = "/dev/tty.usbmodem12341"
teensy = serial.Serial(teensy_file, 115200)
def send_to_teensy(strip):
	command = ''.join(chr(r)+chr(g)+chr(b) for r,g,b in strip)
	teensy.write(command)

if __name__ == '__main__':
	fft_stream = to_fft(read_audio(audio_stream, num_samples = 512))
	scaled_fft = scale_to_LEDs(fft_stream, num_leds = 32, decimation = 8)
	noised_fft = inject_white_noise(scaled_fft, baseline = 5000)
	normalized = normalize_all(noised_fft, falloff = .8)
	smooth_fft = smooth(normalized, falloff = .8)

	raw_colors = normalize_colors(generate_colors(32))
	
	fft_colors = multiply_colors(raw_colors, smooth_fft, scalar = 127*5.0)

	led_colors = cap_colors(fft_colors, cap = 127.0)

	for strip_rgb in led_colors:
		send_to_teensy(strip_rgb)