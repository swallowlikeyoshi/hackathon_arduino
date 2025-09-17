#ifndef MOTIONDATA_H
#define MOTIONDATA_H

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

// Constructor
MotionData::MotionData(uint8_t csPin) 
    : _csPin(csPin)
#ifndef USE_SOFT_SPI
    , _spi(&SPI)
#else
    , _sckPin(SOFT_SCK_PIN), _mosiPin(SOFT_MOSI_PIN), _misoPin(SOFT_MISO_PIN)
#endif
{}

// Begin
bool MotionData::begin() {
    pinMode(_csPin, OUTPUT);
    digitalWrite(_csPin, HIGH);

#ifndef USE_SOFT_SPI
    _spi->begin();
#else
    softSPIBegin();
#endif

    // Reset and initialize MPU-9250
    writeRegister(MPU9250_PWR_MGMT_1, 0x80); // Reset
    delay(100);
    writeRegister(MPU9250_PWR_MGMT_1, 0x01); // Wake up
    delay(10);
    writeRegister(MPU9250_GYRO_CONFIG, 0x00); // ±250 dps
    writeRegister(MPU9250_ACCEL_CONFIG, 0x00); // ±2g

    // Optional: Check WHO_AM_I
    uint8_t whoami = readRegister(MPU9250_WHO_AM_I);
    Serial.print("MPU9250 WHO_AM_I: 0x");
    Serial.println(whoami, HEX);

    return true;
}

#ifndef USE_SOFT_SPI
// Hardware SPI
void MotionData::writeRegister(uint8_t reg, uint8_t value) {
    _spi->beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
    digitalWrite(_csPin, LOW);
    _spi->transfer(reg & 0x7F);
    _spi->transfer(value);
    digitalWrite(_csPin, HIGH);
    _spi->endTransaction();
}

uint8_t MotionData::readRegister(uint8_t reg) {
    uint8_t value;
    _spi->beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
    digitalWrite(_csPin, LOW);
    _spi->transfer(reg | 0x80);
    value = _spi->transfer(0x00);
    digitalWrite(_csPin, HIGH);
    _spi->endTransaction();
    return value;
}

void MotionData::readRegisters(uint8_t reg, uint8_t* buffer, uint8_t length) {
    _spi->beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
    digitalWrite(_csPin, LOW);
    _spi->transfer(reg | 0x80);
    for (uint8_t i = 0; i < length; i++) {
        buffer[i] = _spi->transfer(0x00);
    }
    digitalWrite(_csPin, HIGH);
    _spi->endTransaction();
}

#else
// Software SPI
void MotionData::softSPIBegin() {
    pinMode(_sckPin, OUTPUT);
    pinMode(_mosiPin, OUTPUT);
    pinMode(_misoPin, INPUT);
    digitalWrite(_sckPin, LOW);
}

uint8_t MotionData::softSPITransfer(uint8_t data) {
    uint8_t received = 0;
    for (int8_t i = 7; i >= 0; i--) {
        digitalWrite(_sckPin, LOW);
        digitalWrite(_mosiPin, (data & (1 << i)) ? HIGH : LOW);
        delayMicroseconds(1);
        digitalWrite(_sckPin, HIGH);
        delayMicroseconds(1);
        received <<= 1;
        if (digitalRead(_misoPin)) {
            received |= 0x01;
        }
    }
    digitalWrite(_sckPin, LOW);
    return received;
}

void MotionData::writeRegister(uint8_t reg, uint8_t value) {
    digitalWrite(_csPin, LOW);
    softSPITransfer(reg & 0x7F);
    softSPITransfer(value);
    digitalWrite(_csPin, HIGH);
}

uint8_t MotionData::readRegister(uint8_t reg) {
    digitalWrite(_csPin, LOW);
    softSPITransfer(reg | 0x80);
    uint8_t value = softSPITransfer(0x00);
    digitalWrite(_csPin, HIGH);
    return value;
}

void MotionData::readRegisters(uint8_t reg, uint8_t* buffer, uint8_t length) {
    digitalWrite(_csPin, LOW);
    softSPITransfer(reg | 0x80);
    for (uint8_t i = 0; i < length; i++) {
        buffer[i] = softSPITransfer(0x00);
    }
    digitalWrite(_csPin, HIGH);
}
#endif

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

#endif // MOTIONDATA_H