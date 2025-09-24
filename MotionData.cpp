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
#ifdef DEBUG_VERBOSE
    Serial.print("MPU9250 WHO_AM_I: 0x");
    Serial.println(whoami, HEX);
#endif // DEBUG_VERBOSE

#ifdef USE_AK8963

    if (!initAK8963()) {
        Serial.println("AK8963 initialization failed!");
        // return false;
    }

#endif // USE_AK8963

    if (whoami != 0x71) { // 0x71 is the expected value for MPU-9250
        return false;
    }


#ifdef USE_CALIBRATE_MPU9250

    Serial.println("Calibration starts in 3 seconds. Keep the device still.");
    delay(3000);

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

    Serial.println("Calobration magnetometer starts in 3 seconds. Move the device in figure-8 motion.");
    delay(3000);

    calibrateMag(300);

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

#ifdef MOTIONDATA_DEBUG
    // debugging print buf values
    Serial.print("Accel raw: ");
    for (int i = 0; i < 6; i++) {
        Serial.print(buf[i], HEX);
        Serial.print(" ");
    }
    Serial.println();
#endif // MOTIONDATA_DEBUG

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

#ifdef MOTIONDATA_DEBUG
    // debugging print buf values
    Serial.print("Gyro raw: ");
    for (int i = 0; i < 6; i++) {
        Serial.print(buf[i], HEX);
        Serial.print(" ");
    }
    Serial.println();
#endif // MOTIONDATA_DEBUG

    int16_t x = (buf[0] << 8) | buf[1];
    int16_t y = (buf[2] << 8) | buf[3];
    int16_t z = (buf[4] << 8) | buf[5];
    gx = x / 131.0f - _gyroBiasX;
    gy = y / 131.0f - _gyroBiasY;
    gz = z / 131.0f - _gyroBiasZ;
}

void MotionData::readCalibration(float* bias) {
    if (bias != nullptr) {
        bias[0] = _accelBiasX;
        bias[1] = _accelBiasY;
        bias[2] = _accelBiasZ;
        bias[3] = _gyroBiasX;
        bias[4] = _gyroBiasY;
        bias[5] = _gyroBiasZ;
    }
    return;
}

// 🔹 AK8963 초기화
bool MotionData::initAK8963() {
    // I2C Master Enable
    writeRegister(MPU9250_USER_CTRL, 0x20);
    delay(10);
    writeRegister(MPU9250_I2C_MST_CTRL, 0x0D); // 400kHz I2C

    // WHO_AM_I 확인
    uint8_t whoami;
    readAK8963Registers(AK8963_WHO_AM_I, &whoami, 1);
    if (whoami != 0x48) return false; // AK8963 ID = 0x48

    Serial.print("AK8963 WHO_AM_I: 0x");
    Serial.println(whoami, HEX);

    // Factory calibration 값 읽기
    uint8_t rawData[3];
    readAK8963Registers(AK8963_ASAX, rawData, 3);
    _magAdjX = ((rawData[0] - 128) / 256.0f) + 1.0f;
    _magAdjY = ((rawData[1] - 128) / 256.0f) + 1.0f;
    _magAdjZ = ((rawData[2] - 128) / 256.0f) + 1.0f;

    Serial.print("Mag Adjustment: ");
    Serial.print(_magAdjX, 3); Serial.print(", ");
    Serial.print(_magAdjY, 3); Serial.print(", ");
    Serial.println(_magAdjZ, 3);

    // Continuous measurement mode 2 (100 Hz, 16-bit)
    writeAK8963Register(AK8963_CNTL1, 0x16);
    delay(10);

    return true;
}

// 🔹 AK8963 Register Write
void MotionData::writeAK8963Register(uint8_t reg, uint8_t value) {
    writeRegister(MPU9250_I2C_SLV0_ADDR, AK8963_I2C_ADDR);
    writeRegister(MPU9250_I2C_SLV0_REG, reg);
    writeRegister(MPU9250_I2C_SLV0_DO, value);
    writeRegister(MPU9250_I2C_SLV0_CTRL, 0x81); // enable, 1 byte
    delay(10);
}

// 🔹 안정화된 AK8963 레지스터 읽기
void MotionData::readAK8963Registers(uint8_t reg, uint8_t* buffer, uint8_t len) {
    if (len > 16) len = 16; // MPU9250 SLV0 최대 16바이트

    // I2C 마스터 슬레이브 설정
    writeRegister(MPU9250_I2C_SLV0_ADDR, 0x80 | AK8963_I2C_ADDR); // 읽기 모드
    writeRegister(MPU9250_I2C_SLV0_REG, reg);
    writeRegister(MPU9250_I2C_SLV0_CTRL, 0x80 | len); // Enable + 길이
    delayMicroseconds(50); // 데이터 준비 시간

    // EXT_SENS_DATA_00에서 실제 데이터 읽기
    readRegisters(MPU9250_EXT_SENS_DATA_00, buffer, len);
    delayMicroseconds(50);
}

// 🔹 안정화된 자력계 읽기
void MotionData::readMag(float &mx, float &my, float &mz) {
    uint8_t st1 = 0;

    // 데이터 준비될 때까지 대기
    do {
        readAK8963Registers(AK8963_ST1, &st1, 1);
    } while (!(st1 & 0x01));

    uint8_t rawData[6];
    readAK8963Registers(AK8963_HXL, rawData, 6);

    // 16-bit 센서 값, HXL~HZH 순서
    int16_t x = (rawData[1] << 8) | rawData[0];
    int16_t y = (rawData[3] << 8) | rawData[2];
    int16_t z = (rawData[5] << 8) | rawData[4];

    // 단위 변환 및 보정 적용
    mx = ((float)x * 0.15f * _magAdjX - _magBiasX) * _magScaleX;
    my = ((float)y * 0.15f * _magAdjY - _magBiasY) * _magScaleY;
    mz = ((float)z * 0.15f * _magAdjZ - _magBiasZ) * _magScaleZ;
}

void MotionData::calibrateMag(unsigned int samples) {
    int16_t mag_max[3] = { -32767, -32767, -32767 };
    int16_t mag_min[3] = { 32767, 32767, 32767 };

    for (unsigned int i = 0; i < samples; i++) {
        float mx, my, mz;
        readMag(mx, my, mz);

        if (mx == 0 && my == 0 && mz == 0) {
            delay(10);
            continue;
        }

        if (mx > mag_max[0]) mag_max[0] = mx;
        if (my > mag_max[1]) mag_max[1] = my;
        if (mz > mag_max[2]) mag_max[2] = mz;

        if (mx < mag_min[0]) mag_min[0] = mx;
        if (my < mag_min[1]) mag_min[1] = my;
        if (mz < mag_min[2]) mag_min[2] = mz;

        delay(20);
    }

    _magBiasX = (mag_max[0] + mag_min[0]) / 2.0f;
    _magBiasY = (mag_max[1] + mag_min[1]) / 2.0f;
    _magBiasZ = (mag_max[2] + mag_min[2]) / 2.0f;

    float scaleX = (mag_max[0] - mag_min[0]) / 2.0f;
    float scaleY = (mag_max[1] - mag_min[1]) / 2.0f;
    float scaleZ = (mag_max[2] - mag_min[2]) / 2.0f;

    float avg = (scaleX + scaleY + scaleZ) / 3.0f;

    _magScaleX = avg / scaleX;
    _magScaleY = avg / scaleY;
    _magScaleZ = avg / scaleZ;
}