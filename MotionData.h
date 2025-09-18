#ifndef MOTIONDATA_H
#define MOTIONDATA_H

#include "env.h"
#include <Arduino.h>
#include <SPI.h>

// Define USE_SOFT_SPI to enable software SPI
// #define USE_SOFT_SPI

#ifdef USE_SOFT_SPI
// Software SPI default pins
#define SOFT_SCK_PIN 5
#define SOFT_MOSI_PIN 6
#define SOFT_MISO_PIN 7
#endif

// MPU-9250 Registers
#define MPU9250_WHO_AM_I      0x75
#define MPU9250_PWR_MGMT_1    0x6B
#define MPU9250_PWR_MGMT_2    0x6C
#define MPU9250_ACCEL_XOUT_H  0x3B
#define MPU9250_GYRO_XOUT_H   0x43
#define MPU9250_GYRO_CONFIG   0x1B
#define MPU9250_ACCEL_CONFIG  0x1C
#define MPU9250_USER_CTRL     0x6A
#define I2C_IF_DIS            0x10  // Bit4

class MotionData {
public:
    MotionData(uint8_t csPin);
    bool begin();
    void readAccel(float &ax, float &ay, float &az);
    void readGyro(float &gx, float &gy, float &gz);

private:
    uint8_t _csPin;

    // MotionData 클래스 내부에 오프셋 저장 변수 추가
    float _accelBiasX = 0, _accelBiasY = 0, _accelBiasZ = 0;
    float _gyroBiasX = 0, _gyroBiasY = 0, _gyroBiasZ = 0;

#ifndef USE_SOFT_SPI
    SPIClass* _spi;
#else
    uint8_t _sckPin;
    uint8_t _mosiPin;
    uint8_t _misoPin;

    void softSPIBegin();
    uint8_t softSPITransfer(uint8_t data);
#endif

    void writeRegister(uint8_t reg, uint8_t value);
    uint8_t readRegister(uint8_t reg);
    void readRegisters(uint8_t reg, uint8_t* buffer, uint8_t length);
};

#endif // MOTIONDATA_H