# Will Yager
# This Python script sends color/brightness data based on
# ambient sound frequencies to the LEDs.

import pyaudio as pa
import numpy as np
import sys
import serial
# Output values max at 1.0
import notes_scaled_nosaturation
import lavalamp_colors

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
		samples_l = samples[::2]  
		samples_r = samples[1::2]
		yield (samples_l, samples_r)


teensy_file = "/dev/ttyACM0"
teensy = serial.Serial(teensy_file, 115200)
def send_to_teensy(strip):
	command = [(((i<<2)+0x80,r),((i<<2)+0x81,g),((i<<2)+0x82,b)) 
		for (i,(r,g,b)) in enumerate(strip)]
	command = ''.join(chr(ri)+chr(r)+chr(gi)+chr(g)+chr(bi)+chr(b) 
		for (ri,r),(gi,g),(bi,b) in command)
	teensy.write(command)

if __name__ == '__main__':

	audio = read_audio(audio_stream, num_samples=512)
	leds = notes_scaled_nosaturation.process(audio, num_leds=32, num_samples=512, sample_rate=44100)
	colors = lavalamp_colors.colorize(leds, num_leds=32)

	for strip in colors:
		# for r,g,b in strip:
		# 	sys.stdout.write("r"*r + "g"*g + "b"*b + "\n")
		# print
		send_to_teensy(strip)