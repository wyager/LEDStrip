# LED Strip

`main.cpp` runs on a Teensy. It reads color data over USB and forwards it to one or more LPD8806-based LED strips. The format is [r byte, g byte, b byte]*32. Each color can have a max value of 127. Compile with `make`.

`led_driver.py` runs on a regular computer (tested on Linux and OS X). It reads audio from a microphone, does FFTs on it, makes the FFT data look pretty, generates cool colors, combines the FFT and color data, and sends it to the Teensy.

More info at http://yager.io/LEDStrip/LED.html

## Linux setup

You can technically use this software with any microphone interface and it will work. However, to get clean, perfect-quality digital audio, you will have to use a nonstandard setup.

On OS X, you can use Soundflower or something like that.

I used [Ubuntu Studio](http://ubuntustudio.org). It uses JACK, which provides a nice monitor interface that perfectly replicates the digital signal sent to the speakers. To use some ALSA software (mpd) with Ubuntu Studio, I used `snd-aloop`. I'm pretty sure I read [this article](http://alsa.opensrc.org/Jack_and_Loopback_device_as_Alsa-to-Jack_bridge). It's a bit of black magic. There may have been other steps to make this work. 
