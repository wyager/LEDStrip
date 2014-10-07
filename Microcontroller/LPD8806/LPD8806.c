#include "LPD8806.h"
#include <avr/io.h>

#define CLOCKPIN 5
#define DATAPIN 4
inline void set_clock_high(void){ PORTD |= 1 << CLOCKPIN; }
inline void set_clock_low(void){ PORTD &= ~(1 << CLOCKPIN); }
inline void set_data_high(void){ PORTD |= 1 << DATAPIN; }
inline void set_data_low(void){ PORTD &= ~(1 << DATAPIN); }
inline void set_data_out(void){ DDRD |= 1 << DATAPIN; }
inline void set_clock_out(void){ DDRD |= 1 << CLOCKPIN; }
void clock_strobe(void)  {set_clock_high(); set_clock_low();}

void LPD8806_send_byte(uint8_t the_byte){
  for(uint8_t i = 0; i < 8; i++){
    uint8_t bit = the_byte & (1 << (7 - i));
    if(bit == 0) set_data_low();
    else set_data_high();
    clock_strobe();
  }
}

// Prepare teensy pins and then prepare the strip
void LPD8806_IO_init(size_t num_strips){
  set_data_out();
  set_clock_out();
  for (size_t i = 0; i < num_strips; i++){
    LPD8806_send_byte(0);
  }
}

void LPD8806_send(strip_data* strips, size_t num_strips){
  for(size_t i = 0; i < num_strips; i++){
    for(size_t px = 0; px < 32; px++){
      color pixel = strips[i].pixels[px];
      LPD8806_send_byte(pixel.g | 0x80);
      LPD8806_send_byte(pixel.b | 0x80);
      LPD8806_send_byte(pixel.r | 0x80);
    }
  }
  for(size_t i = 0; i < num_strips; i++){
    LPD8806_send_byte(0);
  }
}