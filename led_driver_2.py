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
from itertools import tee

audio_stream = pa.PyAudio().open(format=pa.paInt16, \
								channels=2, \
								rate=44100, \
								input=True, \
								frames_per_buffer=1024)

# Convert the audio data to numbers, num_samples at a time.
def read_audio(audio_stream, num_samples):
	while True:
		# Read all the input data. 
		samples = audio_stream.read(num_samples) 
		# Convert input data to numbers
		samples = np.fromstring(samples, dtype=np.int16).astype(np.float)
		samples = samples[::2] + samples[1::2]
		assert(len(samples) == num_samples)
		yield samples

# [[float x num_samples] x num frequencies] x 2
# Used to compute presence of frequencies in signal
def compute_convolution_matrices(frequencies, num_samples, sample_rate):
	times = np.arange(0, num_samples, dtype=np.float) / sample_rate
	sines = np.array([np.sin(times * (2*pi*f)) for f in frequencies])
	cosines = np.array([np.cos(times * (2*pi*f)) for f in frequencies])
	return sines, cosines

# Takes an audio sample from stream, and returns an array containing
# the presence of the frequencies from the generated conv. matrix
def convolve(audio_stream, convolution_matrices):
	sin_phase, cos_phase = convolution_matrices
	for samples in audio_stream:
		yield np.sqrt(sin_phase.dot(samples)**2 + cos_phase.dot(samples)**2)

def rolling_average(array_stream, falloff):
	average = np.average(array_stream.next())
	yield average
	for array in array_stream:
		average *= falloff
		average += np.average(array) * (1 - falloff)
		yield average

def ratio(constant_stream, array_stream):
	while True:
		constant = constant_stream.next()
		array = array_stream.next()
		if constant == 0:
			yield np.zeros(len(array))
		else:
			yield array/constant

def rolling_smooth(array_stream, falloff):
	smooth = array_stream.next()
	yield smooth
	for array in array_stream:
		smooth *= falloff
		smooth += array * (1 - falloff)
		yield smooth

# Intended to accept the output of
# ratio() or rolling_smooth(ratio()).
def calculate_scale_factors(array_stream):
	# Depending on the ratio of each frequency to average, scale it.
	# Graph this function to see what it's doing.
	# It's completely arbitrary; I just like it.
	# sqrt(2 / (1 + e^(5*(atan(1.55x)-1))))
	for array in array_stream:
		exponent = (np.arctan(array*1.55)-1)*5
		bottom = np.exp(exponent) + 1
		factors = np.sqrt(bottom*2)
		yield factors

def schur(array_stream1, array_stream2):
	while True:
		array1 = array_stream1.next()
		array2 = array_stream2.next()
		yield array1 * array2

def normalize(array_stream):
	for array in array_stream:
		average = np.average(array)
		if average == 0:
			yield np.zeros(len(array))
		else:
			yield array/average

def add_white_noise(array_stream, amount):
	for array in array_stream:
		if sum(array) != 0:
			yield array + amount
		else:
			yield array

def exaggerate(array_stream, exponent):
	for array in array_stream:
		yield array**exponent

def generate_compensation_factors_for_imbalanced_mic(note_stream):
	notes, notes2 = tee(note_stream)
	averages = rolling_average(notes, falloff=.9)
	relative_brightnesses = rolling_smooth(ratio(averages, notes2), falloff=.9)
	scale_factors = calculate_scale_factors(relative_brightnesses)
	return scale_factors


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
	# Frequency for a given note number.
	def f(n):
		return (2.0**(1.0/12))**(n-49) * 440.0
	#A1 to B6, by whole step. One for each LED.
	frequencies = [f(i) for i in range(13, 13+64)[::2]]
	convolution_matrices = compute_convolution_matrices(frequencies, num_samples=256, sample_rate=44100)
	audio = read_audio(audio_stream, num_samples=256)
	notes = convolve(audio, convolution_matrices)
	notes = add_white_noise(notes, amount=2000)
	notes, notes2 = tee(notes)
	scale_factors = generate_compensation_factors_for_imbalanced_mic(notes2)
	notes = schur(notes, scale_factors)
	notes = normalize(notes)
	notes = exaggerate(notes, exponent=1.6)
	notes = rolling_smooth(notes, falloff=.7)


	colors = normalize_colors(generate_colors(32))
	
	colors = multiply_colors(colors, notes, scalar = 127*.05)

	colors = cap_colors(colors, cap = 127.0)

	for strip in colors:
		# for r,g,b in strip:
		# 	sys.stdout.write("r"*r + "g"*g + "b"*b + "\n")
		# print
		send_to_teensy(strip)