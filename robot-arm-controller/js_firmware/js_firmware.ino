#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "pins.h"


#define LED_COUNT 57
#define LED_BRIGHTNESS 50
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRBW + NEO_KHZ800);


// --===== LED disks & animations =====--

struct LedDisk;
#define OUTER_DISK_LEN 12
#define INNER_DISK_LEN 6
#define TOTAL_DISK_LEN (OUTER_DISK_LEN + INNER_DISK_LEN + 1)
enum LedAnimations : unsigned int {
  SPIN_ANIM,
  FILL_ANIM,
  ATTRACT_ANIM,
  SUCCESS1_ANIM,
  SUCCESS2_ANIM,
  SUCCESS3_ANIM,
  NUM_ANIMATIONS
};

typedef unsigned int (animation_t)(unsigned int, LedDisk*);

struct LedDisk {
  static animation_t * animations[NUM_ANIMATIONS];
  unsigned int start_idx;
  unsigned int anim_idx, anim_frame;

  void draw(int idx, uint32_t color) {
    strip.setPixelColor(idx + start_idx, color);
  }

  void set_animation(unsigned int idx) {
    if (idx != anim_idx) { // only reset if being set to a NEW animation
      anim_idx = idx;
      anim_frame = 0;
    }
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
  int pos = (frame >> 1) % OUTER_DISK_LEN;
  for (int i=0; i<TOTAL_DISK_LEN; i++) {
    disk->draw(
      i, 
      i == pos ? strip.Color(0, 0, 0xff) : strip.Color(0,0,0)
    );
  }
  return SPIN_ANIM;
}


unsigned int fill_anim(unsigned int frame, LedDisk *disk) {
  int len = frame >> 4;
  for (int i=0; i<TOTAL_DISK_LEN; i++) {
    disk->draw(
      i,
      i <= len ? strip.Color(0,0,0xff) : strip.Color(0,0,0)
    );
  }

  if (len >= TOTAL_DISK_LEN) {
    return ATTRACT_ANIM;
  } else {
    return FILL_ANIM;
  }
}


unsigned int attract_anim(unsigned int frame, LedDisk *disk) {
  int k = (frame >> 2) % OUTER_DISK_LEN;
  for (int i=0; i<TOTAL_DISK_LEN; i++) {
    if (k==2 && (i==2 || i==4)) {
      disk->draw(i, strip.Color(0xff,0,0));
    } else if (k==8 && (i==8 || i==10)) {
      disk->draw(i, strip.Color(0,0x7f,0));
    } else {
      disk->draw(i, strip.Color(0,0,0));
    }
  }
  return ATTRACT_ANIM;
}


unsigned int success1_anim(unsigned int frame, LedDisk *disk) {
  uint64_t f = frame;
  uint64_t color = (f * 0xffffff) / 256;
  strip.fill(color, disk->start_idx, TOTAL_DISK_LEN);
  if (frame > 0xff) {
    return ATTRACT_ANIM;
  } else {
    return SUCCESS1_ANIM;
  }
}



unsigned int bounce_slow_anim(unsigned int frame, LedDisk *disk) {
  int f = (frame >> 2) % OUTER_DISK_LEN;
  for (int i=0; i<OUTER_DISK_LEN; i++) {
    if (i == f || (OUTER_DISK_LEN - i) == f) {
      disk->draw(i, 0xffffffff);
    } else {
      disk->draw(i, 0x000000);
    }
  }
  if ((frame >> 2) > 10*OUTER_DISK_LEN) {
    return ATTRACT_ANIM;
  } else {
    return SUCCESS1_ANIM;
  }
}




unsigned int bounce_anim(unsigned int frame, LedDisk *disk) {
  int f = (frame >> 1) % OUTER_DISK_LEN;
  const uint32_t colors[] = { 0xffffffff, 0xffffff00 };
  uint32_t color = colors[(2*f/OUTER_DISK_LEN) % sizeof(colors)];
  for (int i=0; i<OUTER_DISK_LEN; i++) {
    if (i == f || (OUTER_DISK_LEN - i) == f) {
      disk->draw(i, color);
    } else {
      disk->draw(i, 0x000000);
    }
  }
  if ((frame >> 2) > 10*OUTER_DISK_LEN) {
    return ATTRACT_ANIM;
  } else {
    return SUCCESS2_ANIM;
  }
}



unsigned int bounce_fast_anim(unsigned int frame, LedDisk *disk) {
  const int NUM_COLORS = 6;
  const uint32_t colors[NUM_COLORS] = { 
    0xf90101, 0x9c5504, 0x47e409, 
    0x03aa89, 0x0051ff, 0x90036a
  };

  const int NUM_FRAMES = 26;
  uint32_t color = colors[ (2*(frame >> 1)/(NUM_FRAMES>>1)) % NUM_COLORS ];
  const uint16_t frames[NUM_FRAMES] = {
    0b0000000000000000,
    0b0000100000000010,
    0b0000100000000010,
    0b0000010000000100,
    0b0000010000000100,
    0b0000001000001000,
    0b0000001000001000,
    0b0000000100010000,
    0b0000000100010000,
    0b0000000010100000,
    0b0000000010100000,
    0b0000000001000000,
    0b0000000001000000,
    0b0000000000000000,
    0b0000000001000000,
    0b0000000001000000,
    0b0000000010100000,
    0b0000000010100000,
    0b0000000100010000,
    0b0000000100010000,
    0b0000001000001000,
    0b0000001000001000,
    0b0000010000000100,
    0b0000010000000100,
    0b0000100000000010,
    0b0000100000000010,
  };
  uint16_t f = frames[frame % NUM_FRAMES];

  for (int i=0; i<OUTER_DISK_LEN; i++) {
    if ((1<<i) & f) {
      disk->draw(i, color);
    } else {
      disk->draw(i, 0);
    }
  }

  if (frame > 20*NUM_FRAMES) {
    return ATTRACT_ANIM;
  } else {
    return SUCCESS3_ANIM;
  }
}





void setup_animations() {
  LedDisk::animations[SPIN_ANIM] = spin_anim;
  LedDisk::animations[FILL_ANIM] = fill_anim;
  LedDisk::animations[ATTRACT_ANIM] = attract_anim;
  LedDisk::animations[SUCCESS1_ANIM] = bounce_slow_anim;
  LedDisk::animations[SUCCESS2_ANIM] = bounce_anim;
  LedDisk::animations[SUCCESS3_ANIM] = bounce_fast_anim;
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
interval_t ui_update, led_update, bs_update;
// strip should be here too but is referenced in specific functions



// --===== setup & loop =====--

void setup() {
  // configure all button pins
  pinMode(UP_BTN, INPUT_PULLUP);
  pinMode(DOWN_BTN, INPUT_PULLUP);
  pinMode(TARGET1, INPUT_PULLUP);
  pinMode(TARGET2, INPUT_PULLUP);
  pinMode(TARGET3, INPUT_PULLUP);

  // configure LED strip
  strip.begin();
  strip.show();
  strip.setBrightness(LED_BRIGHTNESS);
  setup_animations();

  // configure disks
  disk1.start_idx = 0 * TOTAL_DISK_LEN;
  disk1.set_animation(SUCCESS1_ANIM);
  disk2.start_idx = 1 * TOTAL_DISK_LEN;
  disk2.set_animation(ATTRACT_ANIM);
  disk3.start_idx = 2 * TOTAL_DISK_LEN;
  disk3.set_animation(ATTRACT_ANIM);

  // enable serial comms
  Serial.begin(115200);

  // configure update intervals
  ui_update.delta = 100; 
  led_update.delta = 33;
  bs_update.delta = 100;
}


void loop() {
  static int bs1 = 0;
  static int bs2 = 0;
  static int bs3 = 0;

  if (interval_ready(&ui_update)) {
    dump_joysticks();
    dump_buttons();
    Serial.println();
    if (!digitalRead(TARGET1)) {
      disk1.set_animation(SUCCESS1_ANIM);
      bs1 = 2;
    }
    if (!digitalRead(TARGET2)) {
      disk2.set_animation(SUCCESS2_ANIM);
      bs2 = 2;
    }
    if (!digitalRead(TARGET3)) {
      disk3.set_animation(SUCCESS3_ANIM);
      bs3 = 2;
    }
  }

  if (interval_ready(&led_update)) {
    disk1.update();
    disk2.update();
    disk3.update();
    strip.show();
  }

  if (interval_ready(&bs_update)) {
    if (bs1) {
      digitalWrite(BRIGHTSIGN_B0, 1);
      bs1 -= 1;
    } else {
      digitalWrite(BRIGHTSIGN_B0, 0);
    }

    if (bs2) {
      digitalWrite(BRIGHTSIGN_B1, 1);
      bs2 -= 1;
    } else {
      digitalWrite(BRIGHTSIGN_B1, 0);
    }

    if (bs3) {
      digitalWrite(BRIGHTSIGN_B2, 1);
      bs3 -= 1;
    } else {
      digitalWrite(BRIGHTSIGN_B2, 0);
    }
  }
}
