#include "LPD8806.h"

int main(){
	strip_data strips[1] = {};
	strips->pixels[0] = (color) {100, 50, 25};
	LPD8806_IO_init();
	LPD8806_send(strips, 1);
	return 0;
}