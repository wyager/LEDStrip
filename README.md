# LED Strip

`main.cpp` runs on a Teensy. It reads color data over USB and forwards it to one or more LPD8806-based LED strips. The format is [r byte, g byte, b byte]*32. Each color can have a max value of 127. Compile with `make`.

`led_driver.py` runs on a regular computer, like a Raspberry Pi. It reads audio from a microphone, does FFTs on it, makes the FFT data look pretty, generates cool colors, combines the FFT and color data, and sends it to the Teensy.