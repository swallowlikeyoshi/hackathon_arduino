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
#define MPU9250_INT_PIN_CFG   0x37
#define MPU9250_I2C_MST_CTRL  0x24
#define MPU9250_I2C_SLV0_ADDR 0x25
#define MPU9250_I2C_SLV0_REG  0x26
#define MPU9250_I2C_SLV0_CTRL 0x27
#define MPU9250_EXT_SENS_DATA_00 0x49
#define MPU9250_I2C_SLV0_DO   0x63

// AK8963 (자력계) Registers
#define AK8963_I2C_ADDR   0x0C
#define AK8963_WHO_AM_I   0x00
#define AK8963_ST1        0x02
#define AK8963_HXL        0x03
#define AK8963_CNTL1      0x0A
#define AK8963_CNTL2      0x0B
#define AK8963_ASAX       0x10

class MotionData {
public:
    MotionData(uint8_t csPin);
    bool begin();
    void readAccel(float &ax, float &ay, float &az);
    void readGyro(float &gx, float &gy, float &gz);
    void readMag(float &mx, float &my, float &mz); 
    void readCalibration(float* bias);
    void calibrateMag(unsigned int samples = 300);

private:
    uint8_t _csPin;

    // MotionData 클래스 내부에 오프셋 저장 변수 추가
    float _accelBiasX = 0, _accelBiasY = 0, _accelBiasZ = 0;
    float _gyroBiasX = 0, _gyroBiasY = 0, _gyroBiasZ = 0;

    // 자력계 보정값 저장용
    float _magAdjX = 1.0f, _magAdjY = 1.0f, _magAdjZ = 1.0f;
    float _magBiasX = 0, _magBiasY = 0, _magBiasZ = 0;
    float _magScaleX = 1.0f, _magScaleY = 1.0f, _magScaleZ = 1.0f;

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

    // 🔹 내부 I2C Master를 통해 AK8963 제어
    void writeAK8963Register(uint8_t reg, uint8_t value);
    void readAK8963Registers(uint8_t reg, uint8_t* buffer, uint8_t len);
    bool initAK8963();
};

#endif // MOTIONDATA_H