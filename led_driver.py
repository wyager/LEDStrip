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
from colorsys import hsv_to_rgb

audio_stream = pa.PyAudio().open(format=pa.paInt16, \
								channels=2, \
								rate=44100, \
								input=True, \
								frames_per_buffer=512)

# Convert the audio data to numbers, num_samples at a time.
def read_audio(audio_stream, num_samples):
	while True:
		# Read all the input data. 
		samples = audio_stream.read(num_samples) 
		# Convert input data to numbers
		samples = np.fromstring(samples, dtype=np.int16).astype(np.int32)
		samples = samples[::2] + samples[1::2]
		assert(len(samples) == num_samples)
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

# Normalize each element in a data stream so its value approaches 1
# Good for working with mics with uneven frequency distributions
def normalize_each(data_stream, falloff):
	norm = None
	for data in data_stream:
		norm = data.copy() if norm == None else norm
		difference = data - norm
		norm += np.sqrt(difference.clip(0))*falloff
		norm += difference.clip(max=0)*falloff
		norm += norm == 0 # No dividion by 0
		yield data/norm

# Normalize a data stream so the sum of each array in the stream approaches 1
def normalize_all(data_stream, falloff):
	norm = None
	for data in data_stream:
		norm = sum(data) if norm == None else norm
		norm *= falloff
		norm += sum(data)*(1.0 - falloff)
		if norm == 0:
			norm = 1 # No dividion by 0
		data /= norm
		yield data

# Smooth each individual element in the data stream
def smooth(data_stream, falloff):
	smoothed = None
	for data in data_stream:
		smoothed = data.copy() if smoothed == None else smoothed
		smoothed *= falloff
		smoothed += data*(1.0 - falloff)
		yield smoothed

def exaggerate(color_stream, num_leds, boldness):
	expected_brightness = (1.0 / num_leds) * boldness
	for brightnesses in color_stream:
		yield (brightnesses**2) / expected_brightness

def g_0(t, n):
	return sin(.1*n + sin(t*.27)*4)
def g_1(t, n):
	return sin(.3*n + sin(t*.17)*3)

waveforms = [g_0, g_1]

def waveform(t, n):
	total = sum([g(t,n) for g in waveforms]) / len(waveforms) # -1 to 1
	total += 1.0 # 0 to 2
	total /= 2.0 # 0 to 1
	return total


# Makes a list of colors. Each LED's color function is offset by 1 second 
def generate_colors(num_leds):
	while True:
		t = time.time()
		values = [waveform(t, n) for n in range(num_leds)]
		colors = [hsv_to_rgb(y, 1, 1) for y in values]
		yield colors

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
			assert(r+g+b <= 127)
		yield colors


teensy_file = "/dev/ttyACM0"
teensy = serial.Serial(teensy_file, 115200)
def send_to_teensy(strip):
	command = [(((i<<2)+0x80,r),((i<<2)+0x81,g),((i<<2)+0x82,b)) 
		for (i,(r,g,b)) in enumerate(strip)]
	command = ''.join(chr(ri)+chr(r)+chr(gi)+chr(g)+chr(bi)+chr(b) 
		for (ri,r),(gi,g),(bi,b) in command)
	teensy.write(command)

if __name__ == '__main__':
	brightnesses = to_fft(read_audio(audio_stream, num_samples = 512))
	brightnesses = normalize_each(brightnesses, falloff = .1)
	brightnesses = scale_to_LEDs(brightnesses, num_leds = 32, decimation = 8)
	#brightnesses = inject_white_noise(brightnesses, baseline = 5.0)
	brightnesses = normalize_all(brightnesses, falloff = .8)
	brightnesses = smooth(brightnesses, falloff = .8)
	brightnesses = exaggerate(brightnesses, num_leds = 32, boldness = 1.7)

	colors = normalize_colors(generate_colors(32))
	
	colors = multiply_colors(colors, brightnesses, scalar = 127*5.0)

	colors = cap_colors(colors, cap = 127.0)

	for strip in colors:
		# for r,g,b in strip:
		# 	sys.stdout.write("r"*r + "g"*g + "b"*b + "\n")
		# print
		send_to_teensy(strip)