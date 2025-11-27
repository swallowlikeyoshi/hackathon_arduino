// Hackathon_Serial.ino

// begin env.h
#ifndef ENV_H
#define ENV_H

#define SERIAL_BAUD 115200
#define GPS_BAUD 9600L
#define GPS_RX_PIN 3
#define GPS_TX_PIN 4
#define SD_CS_PIN 10
#define MPU9250_CS_PIN 9
#define RTC_OFFSET (9 * 3600) // GMT+9
#define MAX_LOG_ENTRIES 1000

#define USE_SOFT_SPI

// #define USE_CALIBRATE_MPU9250
#define USE_AK8963

#define DEBUG_VERBOSE

#endif // ENV
// end env.h

//begin GPSdata.h
#ifndef GPSDATA_H
#define GPSDATA_H

#include <SoftwareSerial.h>
#include <TinyGPSPlus.h>

class GPSdata {
private:
    const int rxPin;
    const int txPin;
    long timeOffset;
    SoftwareSerial ss;
    TinyGPSPlus gps;
public:
    GPSdata(int rx, int tx) : rxPin(rx), txPin(tx), ss(rx, tx) {}

    bool begin(long, long);
    void update();
    bool locationUpdated();
    double latitude();
    double longitude();
    String getFormattedDateTime();
};

#endif // GPSDATA_H

// #include "GPSdata.h"

bool GPSdata::begin(long baud, long offsetSeconds) {
    timeOffset = offsetSeconds;
    return ss.begin(baud);
}

void GPSdata::update() {
    while (ss.available() > 0) {
        gps.encode(ss.read());
    }
}

bool GPSdata::locationUpdated() {
    return gps.location.isUpdated();
}

double GPSdata::latitude() {
    return gps.location.lat();
}

double GPSdata::longitude() {
    return gps.location.lng();
}

String GPSdata::getFormattedDateTime() {
    if (gps.date.isValid() && gps.time.isValid()) {
        // GPS에서 받은 UTC 시각을 초 단위로 변환
        long totalSeconds = gps.time.hour() * 3600L +
                            gps.time.minute() * 60L +
                            gps.time.second() +
                            timeOffset;

        // 하루(24h = 86400s) 단위 보정
        int hour   = (totalSeconds / 3600) % 24;
        if (hour < 0) hour += 24; // 음수 방지
        int minute = (totalSeconds % 3600) / 60;
        int second = totalSeconds % 60;

        // 날짜 보정 (offset 때문에 날짜가 바뀔 수 있음)
        int year  = gps.date.year();
        int month = gps.date.month();
        int day   = gps.date.day();

        if (totalSeconds >= 86400) {
            // 다음 날로 넘어감
            day++;
            totalSeconds -= 86400;
            // 간단 처리를 위해 TinyGPSPlus 날짜값 직접 사용 (윤년 계산 등은 필요시 추가)
        } else if (totalSeconds < 0) {
            // 이전 날로 돌아감
            day--;
            totalSeconds += 86400;
        }

        char buffer[25];
        snprintf(buffer, sizeof(buffer), "%04d-%02d-%02d %02d:%02d:%02d",
                 year, month, day, hour, minute, second);
        return String(buffer);
    } else {
        return String("Invalid DateTime");
    }
}

// end GPSdata.h

#include <MPU9250_WE.h>
#include "GPSdata.h"
#include "env.h"

#define READOUT_DELAY 20 // about 50 Hz

const int csPin = 10;
bool useSPI = true;
MPU9250_WE myMPU9250 = MPU9250_WE(&SPI, csPin, useSPI);
GPSdata gpsData(GPS_RX_PIN, GPS_TX_PIN);

// 전송할 데이터를 담을 버퍼
char packetBuffer[256]; 

void setup() {
  // 시리얼 통신 시작 (속도 115200)
  Serial.begin(115200);
  while(!Serial); // 시리얼 포트가 열릴 때까지 대기 (필수는 아니지만 권장)

  // GPS 및 MPU9250 센서 초기화
  gpsData.begin(GPS_BAUD, RTC_OFFSET);

  if (!myMPU9250.init()) {
    Serial.println("MPU9250 does not respond");
  } else {
    Serial.println("MPU9250 is connected");
  }
  
  if (!myMPU9250.initMagnetometer()) {
    Serial.println("Magnetometer does not respond");
  } else {
    Serial.println("Magnetometer is connected");
  }

  Serial.println("Position you MPU9250 flat and don't move it - calibrating...");
  delay(1000);
  myMPU9250.autoOffsets();
  Serial.println("Done!");

  myMPU9250.enableGyrDLPF();
  myMPU9250.setGyrDLPF(MPU9250_DLPF_6);
  myMPU9250.setSampleRateDivider(5);
  myMPU9250.setGyrRange(MPU9250_GYRO_RANGE_250);
  myMPU9250.setAccRange(MPU9250_ACC_RANGE_2G);
  myMPU9250.enableAccDLPF(true);
  myMPU9250.setAccDLPF(MPU9250_DLPF_6);
  myMPU9250.setMagOpMode(AK8963_CONT_MODE_100HZ);
  delay(200);
}

// 전역 변수
unsigned long lastImuReadTime = 0;
unsigned long lastGpsReadTime = 0;

float lastLat = 0.0;
float lastLon = 0.0;

void loop() {
  unsigned long currentTime = millis();

  // --- 1. 느린 작업: GPS 데이터 읽기 (1초에 한 번) ---
  if (currentTime - lastGpsReadTime >= 1000) {
    lastGpsReadTime = currentTime;
    gpsData.update();
    lastLat = gpsData.latitude();
    lastLon = gpsData.longitude();
  }

  // --- 2. 빠른 작업: IMU 데이터 읽고 Serial로 전송 (20ms마다) ---
  if (currentTime - lastImuReadTime >= 20) {
    lastImuReadTime = currentTime;
    
    xyzFloat gValue = myMPU9250.getGValues();
    xyzFloat gyr = myMPU9250.getGyrValues();
    xyzFloat magValue = myMPU9250.getMagValues();

    // 데이터를 char 배열 버퍼에 포맷팅
    snprintf(packetBuffer, sizeof(packetBuffer), 
             "%.6f,%.6f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f",
             lastLat, lastLon,
             gValue.x, gValue.y, gValue.z,
             gyr.x, gyr.y, gyr.z,
             magValue.x, magValue.y, magValue.z);

    // UDP 대신 Serial.println 사용 (줄바꿈 문자 포함 전송)
    Serial.println(packetBuffer);
  }
}