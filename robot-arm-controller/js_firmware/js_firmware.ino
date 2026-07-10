#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "pins.h"


#define LED_COUNT 57
#define LED_BRIGHTNESS 50
Adafruit_NeoPixel led_strip(LED_COUNT, LED_PIN, NEO_GRBW + NEO_KHZ800);


// --===== LED disks & animations =====--

struct LedDisk;
#define OUTER_DISK_LEN 12
#define INNER_DISK_LEN 6
#define TOTAL_DISK_LEN (OUTER_DISK_LEN + INNER_DISK_LEN + 1)
#define NUM_ANIMATIONS 1

typedef unsigned int (animation_t)(unsigned int, LedDisk*);

struct LedDisk {
  static animation_t * animations[NUM_ANIMATIONS];
  unsigned int start_idx;
  unsigned int anim_idx, anim_frame;

  void draw(int idx, uint32_t color) {
    led_strip.setPixelColor(idx + start_idx, color);
  }

  void set_animation(unsigned int idx) {
    anim_idx = idx;
    anim_frame = 0;
  }

  void update() {
    if (anim_idx < NUM_ANIMATIONS) {
      unsigned int next = animations[anim_idx](anim_frame, this);
      anim_frame += 1;
      if (next != anim_idx) {
        set_animation(next);
      }
    }
  }
};
animation_t * LedDisk::animations[NUM_ANIMATIONS];


unsigned int spin_anim(unsigned int frame, LedDisk *disk) {
  int pos = frame % OUTER_DISK_LEN;
  for (int i=0; i<TOTAL_DISK_LEN; i++) {
    disk->draw(
      i, 
      i == pos ? led_strip.Color(0xff, 0, 0) : led_strip.Color(0,0,0)
    );
  }
  return 0;
}


// --===== timing intervals =====--

typedef struct {
  unsigned long timestamp = 0;
  unsigned long delta = 0;
} interval_t;


int interval_ready(interval_t *interval);
int interval_ready(interval_t *interval) {
  if (millis() > interval->timestamp) {
    interval->timestamp = millis() + interval->delta;
    return 1;
  } else {
    return 0;
  }
}


// --===== serial output data dump functions =====--

void dump_button(int pin) {
  Serial.print(digitalRead(pin) ? 0 : 1023);
  Serial.print(" ");
}

void dump_analog(int pin) {
  Serial.print(analogRead(pin));
  Serial.print(" ");
}

void dump_joysticks() {
  dump_analog(JOY1_X);
  dump_analog(JOY1_Y);
  dump_analog(JOY2_Y);
}

void dump_buttons() {
  dump_button(UP_BTN);
  dump_button(DOWN_BTN);
  dump_button(TARGET1);
  dump_button(TARGET2);
  dump_button(TARGET3);
}



// --===== globals =====--
LedDisk disk1, disk2, disk3;
interval_t ui_update, led_update;
// led_strip should be here too but is referenced in specific functions



// --===== setup & loop =====--

void setup() {
  // configure all button pins
	pinMode(UP_BTN, INPUT_PULLUP);
	pinMode(DOWN_BTN, INPUT_PULLUP);
	pinMode(TARGET1, INPUT_PULLUP);
	pinMode(TARGET2, INPUT_PULLUP);
	pinMode(TARGET3, INPUT_PULLUP);

	// configure LED strip
	led_strip.begin();
	led_strip.show();
	led_strip.setBrightness(LED_BRIGHTNESS);

	// configure disks
  LedDisk::animations[0] = spin_anim;
	disk1.start_idx = 0 * TOTAL_DISK_LEN;
	disk1.set_animation(0);
	disk2.start_idx = 1 * TOTAL_DISK_LEN;
	disk2.set_animation(0);
	disk3.start_idx = 2 * TOTAL_DISK_LEN;
	disk3.set_animation(0);

  // enable serial comms
	Serial.begin(115200);

  // configure update intervals
	ui_update.delta = 100; 
	led_update.delta = 10;
}


void loop() {
  if (interval_ready(&ui_update)) {
    dump_joysticks();
    dump_buttons();
	  Serial.println();
	}

	if (interval_ready(&led_update)) {
  	disk1.update();
  	disk2.update();
  	disk3.update();
  	led_strip.show();
  }
}
