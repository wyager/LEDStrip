#include <inttypes.h>
#include <stdlib.h>
// Color is 7 bit pwm value
typedef struct { uint8_t r, g, b; } color;
typedef struct {
  color pixels[32];
} strip_data;
// Prepare teensy pins and then prepare the strip
void LPD8806_IO_init(size_t num_strips);
void LPD8806_send_byte(uint8_t the_byte);
void LPD8806_send(strip_data* strips, size_t num_strips);
