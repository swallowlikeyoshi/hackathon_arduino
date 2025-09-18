#include "MotionData.h"

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
    writeRegister(MPU9250_PWR_MGMT_1, 0x80); // Reset 10000000
    delay(100);
    writeRegister(MPU9250_PWR_MGMT_1, 0x01); // Wake up 00000001
    delay(10);
    writeRegister(MPU9250_PWR_MGMT_2, 0x00); // Enable all sensors
    writeRegister(MPU9250_GYRO_CONFIG, 0x00); // ±250 dps
    writeRegister(MPU9250_ACCEL_CONFIG, 0x00); // ±2g

    // // Optional: Check WHO_AM_I
    uint8_t whoami = readRegister(MPU9250_WHO_AM_I);
    // Serial.print("MPU9250 WHO_AM_I: 0x");
    // Serial.println(whoami, HEX);
    if (whoami != 0x71) { // 0x71 is the expected value for MPU-9250
        return false;
    }

    uint8_t buf[6];
    readRegisters(0x00, buf, 3);
    readRegisters(0x0D, buf + 3, 3);
    Serial.print("Self-test raw data(Gyro, Accel): ");
    for (int i = 0; i < 6; i++) {
        Serial.print(buf[i], HEX);
        Serial.print(" ");
    }
    Serial.println();

    Serial.print("Gryo Self Test reg: ");
    Serial.println(readRegister(0x1C));


#ifdef USE_CALIBRATE_MPU9250

    // Calibration: collect samples while device is still
    const int samples = 200;
    long accX = 0, accY = 0, accZ = 0;
    long gyrX = 0, gyrY = 0, gyrZ = 0;

    for (int i = 0; i < samples; i++) {
        uint8_t buf[6];
        
        // Read raw accel
        readRegisters(MPU9250_ACCEL_XOUT_H, buf, 6);
        int16_t ax = (buf[0] << 8) | buf[1];
        int16_t ay = (buf[2] << 8) | buf[3];
        int16_t az = (buf[4] << 8) | buf[5];
        accX += ax; accY += ay; accZ += az;

        // Read raw gyro
        readRegisters(MPU9250_GYRO_XOUT_H, buf, 6);
        int16_t gx = (buf[0] << 8) | buf[1];
        int16_t gy = (buf[2] << 8) | buf[3];
        int16_t gz = (buf[4] << 8) | buf[5];
        gyrX += gx; gyrY += gy; gyrZ += gz;

        delay(5);
    }

    _accelBiasX = (float)accX / samples / 16384.0f;
    _accelBiasY = (float)accY / samples / 16384.0f;
    // Z축은 중력가속도(1g = 9.8m/s^2 ≈ 1.0) 보정
    _accelBiasZ = (float)accZ / samples / 16384.0f - 1.0f;

    _gyroBiasX = (float)gyrX / samples / 131.0f;
    _gyroBiasY = (float)gyrY / samples / 131.0f;
    _gyroBiasZ = (float)gyrZ / samples / 131.0f;

#endif // USE_CALIBRATE_MPU9250

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
    // debugging print buf values
    Serial.print("Accel raw: ");
    for (int i = 0; i < 6; i++) {
        Serial.print(buf[i], HEX);
        Serial.print(" ");
    }
    Serial.println();

    int16_t x = (buf[0] << 8) | buf[1];
    int16_t y = (buf[2] << 8) | buf[3];
    int16_t z = (buf[4] << 8) | buf[5];
    ax = x / 16384.0f - _accelBiasX;
    ay = y / 16384.0f - _accelBiasY;
    az = z / 16384.0f - _accelBiasZ;
}

void MotionData::readGyro(float &gx, float &gy, float &gz) {
    uint8_t buf[6];
    readRegisters(MPU9250_GYRO_XOUT_H, buf, 6);
    // debugging print buf values
    Serial.print("Gyro raw: ");
    for (int i = 0; i < 6; i++) {
        Serial.print(buf[i], HEX);
        Serial.print(" ");
    }
    Serial.println();

    int16_t x = (buf[0] << 8) | buf[1];
    int16_t y = (buf[2] << 8) | buf[3];
    int16_t z = (buf[4] << 8) | buf[5];
    gx = x / 131.0f - _gyroBiasX;
    gy = y / 131.0f - _gyroBiasY;
    gz = z / 131.0f - _gyroBiasZ;
}