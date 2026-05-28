#include <Arduino.h>


#define J1_X A1
#define J1_Y A0
// #define J2_X A3
#define J2_Y A2

#define B_UP 2
#define B_DOWN 3


void setup() {
	pinMode(B_UP, INPUT_PULLUP);
	pinMode(B_DOWN, INPUT_PULLUP);
	Serial.begin(115200);
}


void loop() {
	Serial.print(analogRead(J1_X)); Serial.print(" ");
	Serial.print(analogRead(J1_Y)); Serial.print(" ");
	Serial.print(analogRead(J2_Y)); Serial.print(" ");
	Serial.print(digitalRead(B_UP)   ? 0 : 1023); Serial.print(" ");
	Serial.print(digitalRead(B_DOWN) ? 0 : 1023); Serial.print(" ");
	Serial.println();
	delay(100);
}
