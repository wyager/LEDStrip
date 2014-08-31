//
//  main.cpp
//  Teensy LED strip controller
//
//  Created by Will Yager on 6/25/13.
//  Copyright (c) 2013 Will Yager. All rights reserved.
//

extern "C"{
#include <avr/io.h>
#include <util/delay.h>
#include "usb_serial.h"
#include "LPD8806.h"
}
#define LED_CONFIG	(DDRD |= (1<<6))
#define LED_ON		(PORTD |= (1<<6))
#define LED_OFF		(PORTD &= ~(1<<6))
#define LED_TOGGLE	(PORTD ^= (1<<6)) 
#define CPU_PRESCALE(n) (CLKPR = 0x80, CLKPR = (n))

void parse_and_execute_command(const char *buf, uint8_t num);
void send_nibble_as_hex(const uint8_t nibble);
void send_byte_as_hex(const uint8_t byte);


int main(void)
{
	CPU_PRESCALE(0);
	LED_CONFIG;
	LED_ON;

	strip_data strips[1] = {};
	LPD8806_IO_init();

	usb_init();
	while (!usb_configured()) /* wait */ ;
	while (!(usb_serial_get_control() & USB_SERIAL_DTR)) /* wait */ ;
	usb_serial_flush_input();
	
	while (1) {
		

		for(uint8_t pixel = 0; pixel < 32; pixel++){
			uint8_t r = usb_serial_getchar();
			uint8_t g = usb_serial_getchar();
			uint8_t b = usb_serial_getchar();
			strips[0].pixels[pixel] = {r, g, b};
		}

		LPD8806_send(strips, 1);
		usb_serial_putchar('a');
		LED_TOGGLE;
	}
}


//Send a byte as an unsigned hex value
void send_byte_as_hex(const uint8_t byte){
	send_nibble_as_hex(byte >> 4);
	send_nibble_as_hex(byte & 0x0F);
}
//Send a nibble as a hex digit to the USB serial device
//Invalid values are represented as a '#'
void send_nibble_as_hex(const uint8_t nibble){
	if(nibble>15){
		usb_serial_putchar('#');
	}
	else if(nibble<10){
		usb_serial_putchar(nibble + 48);
	}
	else{
		usb_serial_putchar(nibble + 55);
	}
}

