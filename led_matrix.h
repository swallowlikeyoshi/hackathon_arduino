#ifndef LED_MATRIX_H
#define LED_MATRIX_H

#include <Arduino.h>
#include "env.h"

enum {
    LED_HI = 0,
    LED_1,
    LED_2,
    LED_3,
    LED_ERR,
    LED_ERR_SD,
    LED_ERR_MPU,
    LED_ERR_GPS,
    LED_WORKING_1,
    LED_WORKING_2,
};

const uint32_t hackathon_led_matrix[][4] = {
  {
    0x00028838,
    0x82880000,
    0x88070000
  },
  {
    0x00002006,
    0x00A00200,
    0x200F8000
  },
  {
    0x0000F001,
    0x00F00800,
    0x800F0000
  },
  {
    0x0000F001,
    0x00F00100,
    0x100F0000
  },
  {
    0x00070040,
    0x074846C4,
    0x4874A000
  },
  {
    0x1E011014,
    0x81481081,
    0x481081F8
  },
  {
    0x00020070,
    0x42042042,
    0x203F4020
  },
  {
    0x00000020,
    0x42842A42,
    0xA02A4000
  },
  {
    0x00020000,
    0x00000000,
    0x00000000
  },
  {
    0x00010000,
    0x00000000,
    0x00000000
  }
};

#endif // LED_MATRIX_H