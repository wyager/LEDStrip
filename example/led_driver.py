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

num_samples = 512

audio_stream = pa.PyAudio().open(format=pa.paInt16, \
								channels=1, \
								rate=44100, \
								input=True, \
								frames_per_buffer=num_samples)

# Converts the audio stream to a stream of FFT values
# The FFT values are num_samples/2 wide.
# They have been converted from complex positive and negative to real positive.
def to_fft(audio_stream):
	while True:
		# Read all the input data. 
		samples = audio_stream.read(num_samples) 
		# Convert input data to numbers
		samples = [struct.unpack('<h',samples[2*i:2*i+2])[0] \
									for i in range(num_samples)]
		# Take the FFT of the input signal
		frequencies = fft.fft(samples) 
		# Convert from complex to real magnitudes
		frequencies = np.abs(frequencies)
		# Sum negative and positive frequency components
		magnitudes = frequencies[0:num_samples/2]
		magnitudes[1:] += frequencies[num_samples/2 + 1:][::-1]
		yield magnitudes

num_leds = 32

# Takes the stream of FFT values, discards an arbitrary fraction of them,
# and fits the rest to the LEDs.
def scale_to_LEDs(fft_stream):
	frequency_range = 8 # Only use 1/4th of the FFT's output
	for sample in fft_stream:
		# Cut off the higher frequencies we don't care about any more
		sample = sample[0:len(sample)/frequency_range]
		# How many FFT bins do we want to lump into a single LED?
		scale_factor = len(sample)/num_leds
		# Sum the FFT bins into each LED's value
		led_magnitudes = sample.reshape(num_leds, scale_factor).sum(axis=1)
		yield led_magnitudes

# Adds a constant to all values in an FFT output.
# This is equivalent to adding white noise to the audio signal.
# This prevents the LEDs from flickering from with a weak audio signal
def inject_white_noise(fft_stream):
	baseline = 5000
	for sample in fft_stream:
		yield sample + baseline

# Smooths the brightness values going to the LEDs, and scales them
# according to ambient volume.
def smooth_LED_brightness(led_stream):
	volume_falloff = .9
	brightness_falloff = .8
	moving_avg_volume = 1.0
	moving_avg_brightness = np.array([0.0]*num_leds)
	for brightnesses in led_stream:
		# Keep the total LED brightness around 1.0
		moving_avg_volume *= volume_falloff
		moving_avg_volume += sum(brightnesses)*(1.0 - volume_falloff)
		brightnesses /= moving_avg_volume
		# Smooth each individual LED
		moving_avg_brightness *= brightness_falloff
		moving_avg_brightness += brightnesses*(1.0 - brightness_falloff)
		yield moving_avg_brightness

# This iterator outputs an array containing a color for each LED.
# The colors are time-based, and look cool
# The colors are in the form of (r,g,b) tuples.
def generate_led_colors():
	theta_frequencies = [2.0/60, 3.0/60] # 2 & 3 times a minute
	phi_frequencies   = [5.0/60, 7.0/60] # 5 & 7 times a minute
	delta_t_per_led = 1.0 # Each LED is one second ahead of the last
	while True:
		led_colors = [(0,0,0)] * num_leds
		for led in range(num_leds):
			# We need to angles, in range 0 to pi/2
			# Current time/x-coord for this LED
			t = 2 * pi * (time.time() + delta_t_per_led*led)
			# From this time, generate a point on the 3-sphere's positive quad
			thetas = [sin(t*f) * pi/4 + pi/4 for f in theta_frequencies]
			theta  = sum(thetas)/len(thetas)
			phis   = [sin(t*f) * pi/4 + pi/4 for f in phi_frequencies]
			phi    = sum(phis)/len(phis)
			x = sin(theta) * cos(phi)
			y = sin(theta) * sin(phi)
			z = cos(theta)
			led_colors[led] = (x,y,z)
		yield led_colors

# Takes in a stream of brightnesses and a stream of colors,
# and outputs a stream of integer RGB values that can be sent
# to the LEDs.
def generate_RGB_values(brightness_stream, color_stream):
	brightness_booster = 5.0 # Arbitrary brightness tuner
	max_rgb = 127 # Max brightness the LEDs can do
	def to_rgb((brightness, color)):
		brightness = min(max_rgb * brightness * brightness_booster, max_rgb)
		r, g, b = color
		r, g, b = r/(r+g+b), g/(r+g+b), b/(r+g+b)
		r, g, b = int(r*brightness), int(g*brightness), int(b*brightness)
		return (r,g,b)
	while True:
		brightnesses = brightness_stream.next()
		colors = color_stream.next()
		yield map(to_rgb, zip(brightnesses, colors))

teensy_file = "/dev/tty.usbmodem12341"
teensy = serial.Serial(teensy_file, 115200)
def send_to_teensy(strip):
	command = ''.join(chr(r)+chr(g)+chr(b) for r,g,b in strip)
	teensy.write(command)

if __name__ == '__main__':
	# Raw frequency data
	fft_stream = to_fft(audio_stream)
	# Frequency data fitted to LEDs
	brightness_stream = scale_to_LEDs(fft_stream)
	# Introduce white noise (baseline brightness)
	brightness_stream = inject_white_noise(brightness_stream)
	# Smoothed fitted frequency data
	smoothed_brightness_stream = smooth_LED_brightness(brightness_stream)
	# Cool colors for each LED. Changes over time
	color_stream = generate_led_colors()
	# Actual RGB values
	rgb_stream = generate_RGB_values(smoothed_brightness_stream, color_stream)
	for strip_rgb in rgb_stream:
		for r,g,b in strip_rgb:
			sys.stdout.write("r"*r)
			sys.stdout.write("g"*g)
			sys.stdout.write("b"*b)
			sys.stdout.write("\n")
			sys.stdout.flush()
		print
		send_to_teensy(strip_rgb)