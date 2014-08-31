import sys # to write to stdout
from math import sin, cos, pi
import numpy.fft as fft # to do an FFT on the data
import numpy as np
import pyaudio as pa
import time
import struct
import serial

""" Stop using simple decimation like this. Looks like it's only safe to
do so if I low-pass the audio first. Just do an excessive FFT and only take
a fraction of it."""

### Audio options
sample_rate = 44100	# Audio sample rate
fft_samples = 512	# FFT size. *Always* make this a power of 2
fft_samples_used = 32 # Use only this portion of the FFT (at lower frequencies)
num_leds = 32 # The number of LEDs on the strip
volume_smoothing_decay = .8 # The rate at which the calculated volume falls off
led_smoothing_decay = .8 # The rate at which the calculated freqs fall off
### Color pattern options
theta_frequencies = [2.0/60, 3.0/60] # 2/3 times a minute
phi_frequencies   = [5.0/60, 7.0/60] # 5/7 times a minute
delta_t_per_led = 1.0 # Each LED is 1 second ahead of the last
brightness_booster = 5.0 # Brightness scale factor
### Teensy options
teensy_file = "/dev/ttyUSBmodem666" # The Teensy's serial device


stream = pa.PyAudio().open(format=pa.paInt16, \
							channels=1, \
							rate=sample_rate, \
							input=True, \
							frames_per_buffer=fft_samples)

# Returns an iterator.
# The iterator outputs arrays with one element for each LED.
# The element contains the magnitude of the frequency range about that LED.
# Each LED gets (sample_rate / 2 / input_decimation / num_leds) hertz range.
# The sum of all the elements will tend towards 1.0
def get_led_magnitudes():
	moving_avg_volume = 1.0 # Used to scale the output depending on volume
	moving_avg_leds = np.array([0.0]*32)
	while True:
		# Read all the input data. 
		samples = stream.read(fft_samples) 
		# Convert input data to numbers
		samples = [struct.unpack('<h',samples[2*i:2*i+2])[0] \
									for i in range(fft_samples)]
		# Take the FFT of the input signal
		frequencies = fft.fft(samples) 
		# Convert from complex to real magnitudes
		frequencies = np.abs(frequencies)
		# Sum negative and positive frequency components
		magnitudes = frequencies[0:fft_samples/2]
		magnitudes[1:] += frequencies[fft_samples/2 + 1:][::-1]
		magnitudes = magnitudes[0:fft_samples_used]
		# How many FFT bins do we want to lump into a single LED?
		scale_factor = len(magnitudes) / num_leds
		# Sum the FFT bins into each LED's value
		led_magnitudes = magnitudes.reshape(num_leds, scale_factor).sum(axis=1)
		# Calculate the volume scale factor based on ambient volume
		moving_avg_volume *= volume_smoothing_decay
		moving_avg_volume += sum(led_magnitudes)*(1.0 - volume_smoothing_decay)
		# Scale the LED magnitudes
		led_magnitudes /= moving_avg_volume
		# Smooth the measured frequency
		moving_avg_leds *= led_smoothing_decay
		moving_avg_leds += led_magnitudes*(1.0 - led_smoothing_decay)
		yield moving_avg_leds

# Returns an iterator.
# The iterator outputs an array containing a color for each LED.
# The colors are time-based, and look cool
# The colors are in the form of (r,g,b) tuples.
def get_led_colors():
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

# Returns an iterator.
# The iterator outputs an array of (R,G,B) values. One per LED.
# The value is based on A) the frequency in that LED's range
# and B) the color at this time.
def get_led_RGB_values():
	def to_rgb(magnitude, color):
		brightness = 127 * magnitude * brightness_booster
		r, g, b = color
		r, g, b = r/(r+g+b), g/(r+g+b), b/(r+g+b)
		r, g, b = int(r*brightness), int(g*brightness), int(b*brightness)
		r, g, b = min(r, 127), min(g, 127), min(b, 127)
		return (r,g,b)
	magnitudes = get_led_magnitudes()
	colors = get_led_colors()
	while True:
		strip_mags = magnitudes.next()
		strip_colors = colors.next()
		yield [to_rgb(mag,color) for mag,color in zip(strip_mags,strip_colors)]

#teensy = serial.Serial.open(teensy_file)
for RGBs in get_led_RGB_values():
	for r,g,b in RGBs:
		sys.stdout.write("r"*r)
		sys.stdout.write("g"*g)
		sys.stdout.write("b"*b)
		sys.stdout.write("\n")
		sys.stdout.flush()
		#teensy.write(chr(r))
		#teensy.write(chr(g))
		#teensy.write(chr(b))
	#teensy.flush()
	print