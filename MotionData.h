#ifndef MOTIONDATA_H
#define MOTIONDATA_H

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>

// MPU-9250 Registers
#define MPU9250_WHO_AM_I      0x75
#define MPU9250_PWR_MGMT_1    0x6B
#define MPU9250_ACCEL_XOUT_H  0x3B
#define MPU9250_GYRO_XOUT_H   0x43

#define MPU9250_GYRO_CONFIG   0x1B

// USER_CTRL 레지스터
#define MPU9250_USER_CTRL     0x6A
#define I2C_IF_DIS            0x10  // Bit4

// AK8963 (Magnetometer) Registers
#define AK8963_ADDR           0x0C
#define AK8963_WHO_AM_I       0x00
#define AK8963_CNTL1          0x0A
#define AK8963_ST1            0x02
#define AK8963_XOUT_L         0x03

// MPU-92 SPI pins
// SCLK: 1
// SDA/SDI: MOSI 11
// ADO/SDO: MISO 12

class MotionData {
public:
    MotionData(uint8_t csPin = 9);
    bool begin();
    void readAccel(float &ax, float &ay, float &az);
    void readGyro(float &gx, float &gy, float &gz);
    // void readMag(float &mx, float &my, float &mz);

private:
    uint8_t _csPin;
    void writeRegister(uint8_t reg, uint8_t value);
    uint8_t readRegister(uint8_t reg);
    void readRegisters(uint8_t reg, uint8_t *buffer, uint8_t len);

    // Magnetometer helpers
    // void writeMagRegister(uint8_t reg, uint8_t value);
    // uint8_t readMagRegister(uint8_t reg);
    // void readMagRegisters(uint8_t reg, uint8_t *buffer, uint8_t len);
};

MotionData::MotionData(uint8_t csPin) : _csPin(csPin) {}

bool MotionData::begin() {
    pinMode(_csPin, OUTPUT);
    digitalWrite(_csPin, HIGH);
    SPI.begin();

    // Wake up MPU-9250
    writeRegister(MPU9250_PWR_MGMT_1, 0x00);
    delay(100);

    // I2C 인터페이스 비활성화
    writeRegister(MPU9250_USER_CTRL, I2C_IF_DIS);
    delay(10);

    writeRegister(MPU9250_GYRO_CONFIG, 0x00); // ±250°/s

    // Check WHO_AM_I
    uint8_t whoami = readRegister(MPU9250_WHO_AM_I);

    Serial.print("***********\nMPU9250 WHO_AM_I: 0x");
    Serial.print(whoami, HEX);
    Serial.println("\n***********");

    if (whoami != 0x71) return false;

    // Magnetometer init (pass-through mode)
    // writeRegister(0x37, 0x02); // Enable bypass
    // delay(10);
    // writeMagRegister(AK8963_CNTL1, 0x16); // 16-bit, continuous mode 2
    // delay(10);

    return true;
}

void MotionData::writeRegister(uint8_t reg, uint8_t value) {
    digitalWrite(_csPin, LOW);
    SPI.transfer(reg & 0x7F);
    SPI.transfer(value);
    digitalWrite(_csPin, HIGH);
}

uint8_t MotionData::readRegister(uint8_t reg) {
    digitalWrite(_csPin, LOW);
    SPI.transfer(reg | 0x80);
    uint8_t value = SPI.transfer(0x00);
    digitalWrite(_csPin, HIGH);
    return value;
}

void MotionData::readRegisters(uint8_t reg, uint8_t *buffer, uint8_t len) {
    digitalWrite(_csPin, LOW);
    SPI.transfer(reg | 0x80);
    for (uint8_t i = 0; i < len; i++) {
        buffer[i] = SPI.transfer(0x00);
    }
    digitalWrite(_csPin, HIGH);
}

void MotionData::readAccel(float &ax, float &ay, float &az) {
    uint8_t buf[6];
    readRegisters(MPU9250_ACCEL_XOUT_H, buf, 6);
    int16_t x = (buf[0] << 8) | buf[1];
    int16_t y = (buf[2] << 8) | buf[3];
    int16_t z = (buf[4] << 8) | buf[5];
    ax = x / 16384.0f;
    ay = y / 16384.0f;
    az = z / 16384.0f;
}

void MotionData::readGyro(float &gx, float &gy, float &gz) {
    uint8_t buf[6];
    readRegisters(MPU9250_GYRO_XOUT_H, buf, 6);
    int16_t x = (buf[0] << 8) | buf[1];
    int16_t y = (buf[2] << 8) | buf[3];
    int16_t z = (buf[4] << 8) | buf[5];
    gx = x / 131.0f;
    gy = y / 131.0f;
    gz = z / 131.0f;
}

// Magnetometer via I2C pass-through
/*
void MotionData::writeMagRegister(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(AK8963_ADDR);
    Wire.write(reg);
    Wire.write(value);
    Wire.endTransmission();
}

uint8_t MotionData::readMagRegister(uint8_t reg) {
    Wire.beginTransmission(AK8963_ADDR);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(AK8963_ADDR, 1);
    return Wire.read();
}

void MotionData::readMagRegisters(uint8_t reg, uint8_t *buffer, uint8_t len) {
    Wire.beginTransmission(AK8963_ADDR);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(AK8963_ADDR, len);
    for (uint8_t i = 0; i < len; i++) {
        buffer[i] = Wire.read();
    }
}

void MotionData::readMag(float &mx, float &my, float &mz) {
    uint8_t st1 = readMagRegister(AK8963_ST1);
    if (!(st1 & 0x01)) {
        mx = my = mz = 0;
        return;
    }
    uint8_t buf[6];
    readMagRegisters(AK8963_XOUT_L, buf, 6);
    int16_t x = (buf[1] << 8) | buf[0];
    int16_t y = (buf[3] << 8) | buf[2];
    int16_t z = (buf[5] << 8) | buf[4];
    mx = x * 0.15f;
    my = y * 0.15f;
    mz = z * 0.15f;
}
*/


#endif // MOTIONDATA_H