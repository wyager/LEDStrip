# Will Yager
# This Python script sends color/brightness data based on
# ambient sound frequencies to the LEDs.

import numpy as np
from math import pi

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
	def convolve(samples):
		return np.sqrt(sin_phase.dot(samples)**2 + cos_phase.dot(samples)**2)
	for l, r in audio_stream:
		yield convolve(l) + convolve(r) # Do them separately to avoid interference

def rolling_scale(stream, falloff):
	average = 1.0
	for array in stream:
		average *= falloff
		average += np.average(array)*(1-falloff)
		if average == 0:
			average = 1
		yield array / average

def rolling_smooth(array_stream, falloff):
	smooth = array_stream.next()
	yield smooth
	for array in array_stream:
		smooth *= falloff
		smooth += array * (1 - falloff)
		yield smooth

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
		yield array ** exponent

def human_hearing_multiplier(freq):
	points = {0:-10, 50:-8, 100:-4, 200:0, 500:2, 1000:0, \
				2000:2, 5000:4, 10000:-4, 15000:0, 20000:-4}
	freqs = sorted(points.keys())
	for i in range(len(freqs)-1):
		if freq >= freqs[i] and freq < freqs[i+1]:
			x1 = float(freqs[i])
			x2 = float(freqs[i+1])
			break
	y1, y2 = points[x1], points[x2]
	decibels = ((x2-freq)*y1 + (freq-x1)*y2)/(x2-x1)
	return 10.0**(decibels/10.0)

def schur(array_stream, multipliers):
	for array in array_stream:
		yield array*multipliers

def rolling_scale_to_max(stream, falloff):
	avg_peak = 0.0
	for array in stream:
		peak = np.max(array)
		if peak > avg_peak:
			avg_peak = peak # Output never exceeds 1
		else:
			avg_peak *= falloff
			avg_peak += peak * (1-falloff)
		if avg_peak == 0:
			yield array
		else:
			yield array / avg_peak

# [[Float 0.0-1.0 x 32]]
def process(audio_stream, num_leds, num_samples, sample_rate):
	# Frequency for a given note number.
	def f(n):
		return (2.0**(1.0/12))**(n-49) * 440.0
	frequencies = [i*100 for i in range(num_leds)]#[f(i*3) for i in range(num_leds)]
	human_ear_multipliers = np.array([human_hearing_multiplier(f) for f in frequencies])
	convolution_matrices = compute_convolution_matrices(frequencies, num_samples=num_samples, sample_rate=sample_rate)
	notes = convolve(audio_stream, convolution_matrices)
	notes = add_white_noise(notes, amount=2000)
	notes = schur(notes, human_ear_multipliers)
	#notes = rolling_scale(notes, falloff = .99)
	#notes = normalize(notes)
	notes = rolling_scale_to_max(notes, falloff=.98) # Range: 0-1
	notes = exaggerate(notes, exponent=2)
	notes = rolling_smooth(notes, falloff=.7)
	return notes