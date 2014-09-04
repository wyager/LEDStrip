//
//  main.cpp
//  Teensy LED strip controller
//
//  Created by Will Yager on 2014-09-01.
//  Copyright (c) 2014 Will Yager. All rights reserved.
//

extern "C"{
#include <avr/io.h>
#include <util/delay.h>
#include "usb_serial.h"
#include "LPD8806/LPD8806.h"
}

#define CPU_PRESCALE(n) (CLKPR = 0x80, CLKPR = (n))

void wait_for_byte(){
	while(!usb_serial_available()){/* wait */};
}

int main(void)
{
	CPU_PRESCALE(0);

	const size_t num_strips = 1;
	strip_data strips[num_strips] = {};
	LPD8806_IO_init(num_strips);

	usb_init();
	while (!usb_configured()) /* wait */ ;
	while (!(usb_serial_get_control() & USB_SERIAL_DTR)) /* wait */ ;
	usb_serial_flush_input();

	while (1) {
		// Repeatedly read RGB data over USB serial and then
		// forward it to the LED strip
		for(uint8_t pixel = 0; pixel < 32; pixel++){
			wait_for_byte();
			uint8_t r = usb_serial_getchar();
			wait_for_byte();
			uint8_t g = usb_serial_getchar();
			wait_for_byte();
			uint8_t b = usb_serial_getchar();
			strips[0].pixels[pixel] = {r, g, b};
		}

		LPD8806_send(strips, num_strips);
	}
}
