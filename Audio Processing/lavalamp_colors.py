# Will Yager
# This Python script sends color/brightness data based on
# ambient sound frequencies to the LEDs.

from math import cos, sin, pi
import time
from colorsys import hsv_to_rgb


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


def colorize(audio_stream, num_leds):
	colors = normalize_colors(generate_colors(num_leds))
	colors = multiply_colors(colors, audio_stream, scalar = 127.0)
	colors = cap_colors(colors, cap = 127.0)
	return colors