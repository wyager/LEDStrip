# Gus Naughton 
# This python script outputs all sound devices on the system 
# for specifying which input you'd like to use for led_driver.py

import pyaudio 

def find_input_devices():
	pa = pyaudio.PyAudio()
	for i in range( pa.get_device_count() ):
		devinfo = pa.get_device_info_by_index(i)
		print( "Device %d: %s"%(i,devinfo["name"]) )
		
find_input_devices()
