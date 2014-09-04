#include "LPD8806.h"
#include <avr/io.h>
#include <util/delay.h>

#define CLOCKPIN 2
#define DATAPIN 3
inline void set_clock_high(void){ PORTB |= 1 << CLOCKPIN; _delay_ms(1);}
inline void set_clock_low(void){ PORTB &= ~(1 << CLOCKPIN); _delay_ms(1);}
inline void set_data_high(void){ PORTF |= 1 << DATAPIN; _delay_ms(1);}
inline void set_data_low(void){ PORTF &= ~(1 << DATAPIN); _delay_ms(1);}
inline void set_data_out(void){ DDRF |= 1 << DATAPIN; }
inline void set_clock_out(void){ DDRB |= 1 << CLOCKPIN; }
void clock_strobe(void)  {set_clock_high(); set_clock_low();}
// Prepare teensy pins and then prepare the strip
void LPD8806_IO_init(uint8_t num_strips){
  set_data_out();
  set_clock_out();
  for (uint8_t i = 0; i < num_strips; i++){
    LPD8806_send_byte(0);
  }
}

void LPD8806_send_bit(uint8_t bit){
  if(bit == 0){
    set_data_low();
  }
  else {
    set_data_high();
  }
  clock_strobe();
}
void LPD8806_send_byte(uint8_t the_byte){
  for(uint8_t mask=0x80; mask; mask >>= 1) {
    uint8_t bit = the_byte & mask;
    if(bit == 0) set_data_low();
    else set_data_high();
    clock_strobe();
  }
}
void LPD8806_send(strip_data* strips, uint8_t num_strips){
  for(uint8_t i = 0; i < num_strips; i++){
    for(uint8_t px = 0; px < 32; px++){
      color pixel = strips[i].pixels[px];
      LPD8806_send_byte(pixel.g | 0x80);
      LPD8806_send_byte(pixel.b | 0x80);
      LPD8806_send_byte(pixel.r | 0x80);
    }
  }
  for(uint8_t i = 0; i < num_strips; i++){
    LPD8806_send_byte(0);
  }
}