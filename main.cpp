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

uint8_t usb_is_connected(void){
	return (usb_serial_get_control() & USB_SERIAL_DTR);
}

uint8_t usb_serial_blocking_read(void){
	while(!usb_serial_available()){}
	return usb_serial_getchar();
}

int main(void)
{
	CPU_PRESCALE(0);

	const size_t num_strips = 1;
	strip_data strips[num_strips] = {};
	LPD8806_IO_init(num_strips);

	usb_init();
	while (!usb_configured()) /* wait */ ;
	while (!usb_is_connected()) /* wait */ ;
	usb_serial_flush_input();

	while (1) {
		uint8_t index = usb_serial_blocking_read();
		if(!(index & 0x80)) index = usb_serial_blocking_read(); // dropped byte
		uint8_t color_byte = usb_serial_blocking_read();

		uint8_t pixel_index = (index >> 2) & 0x1F; // 5 pixel index bits
		uint8_t color_index = index & 0x03; // 2 color bits

		if(color_index == 0) strips[0].pixels[pixel_index].r = color_byte;
		if(color_index == 1) strips[0].pixels[pixel_index].g = color_byte;
		if(color_index == 2) strips[0].pixels[pixel_index].b = color_byte;

		if(pixel_index == 31 && color_index == 2){
			LPD8806_send(strips, num_strips);
		}
	}
}
