#ifndef ENV_H
#define ENV_H

// 1. 라이브러리 매니저에서 MPU9250_WE, TinyGPSPlus 설치해야 함.

// 2. Wi-Fi 및 서버 정보 (사용자 환경에 맞게 수정)
const char* ssid = "hotspot";
const char* password = "12341234";
/**
 * ### 서버의 IP 주소
 * 수신 측 Python 서버가 실행되는 PC의 IP 주소로 변경해야 합니다.
 * 첫 번째로 서버를 실행하는 PC를 핫스팟에 연결한 후, 해당 PC의 로컬 IP 주소를 확인하여 여기에 입력합니다.
 * 윈도우 PC의 경우 명령 프롬프트에서 `ipconfig` 명령어를 사용하여 IP 주소를 확인할 수 있습니다. (IPv4 주소를 여기에 입력)
 */
const char* serverIP = "10.250.172.42";
const int serverPort = 65001; // Python UDP 수신 포트

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

#endif // ENV_

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

#include <WiFi.h>
#include <WiFiUdp.h> // UDP 사용을 위한 라이브러리 추가
#include <MPU9250_WE.h>
#include "GPSdata.h"
#include "env.h"

#define READOUT_DELAY 20 // about 50 Hz

// --- WiFiUDP 객체 생성 ---
WiFiUDP udp;

const int csPin = 10;
bool useSPI = true;
MPU9250_WE myMPU9250 = MPU9250_WE(&SPI, csPin, useSPI);
GPSdata gpsData(GPS_RX_PIN, GPS_TX_PIN);

// 전송할 데이터를 담을 버퍼 (String 객체보다 훨씬 효율적)
char packetBuffer[256]; 

void setup() {
  Serial.begin(115200);

  // Wi-Fi 연결
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  delay(3000);
  Serial.println("\nWiFi Connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // UDP 통신 시작
  if (udp.begin(serverPort)) {
      Serial.println("UDP communication started");
  } else {
      Serial.println("Failed to start UDP");
  }

  // GPS 및 MPU9250 센서 초기화 (기존과 동일)
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

// loop() 함수 위에 전역 변수로 추가
unsigned long lastImuReadTime = 0;
unsigned long lastGpsReadTime = 0;

// 가장 최근에 읽은 GPS 데이터를 저장할 변수
float lastLat = 0.0;
float lastLon = 0.0;

void loop() {
  unsigned long currentTime = millis();

  // --- 1. 느린 작업: GPS 데이터 읽기 (1초에 한 번) ---
  if (currentTime - lastGpsReadTime >= 1000) {
    lastGpsReadTime = currentTime;
    gpsData.update();
    // 가장 최근 GPS 값을 별도 변수에 저장
    lastLat = gpsData.latitude();
    lastLon = gpsData.longitude();
  }

  // --- 2. 빠른 작업: IMU 데이터 읽고 UDP로 전송 (20ms마다) ---
  if (currentTime - lastImuReadTime >= 20) {
    lastImuReadTime = currentTime;
    
    // IMU 센서 데이터 읽기
    xyzFloat gValue = myMPU9250.getGValues();
    xyzFloat gyr = myMPU9250.getGyrValues();
    xyzFloat magValue = myMPU9250.getMagValues();

    // 데이터를 char 배열 버퍼에 포맷팅 (가장 최근 GPS 값 사용)
    snprintf(packetBuffer, sizeof(packetBuffer), 
             "%.6f,%.6f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f",
             lastLat, lastLon, // 1초마다 갱신되는 GPS 값 사용
             gValue.x, gValue.y, gValue.z,
             gyr.x, gyr.y, gyr.z,
             magValue.x, magValue.y, magValue.z);

    // UDP 패킷 전송
    udp.beginPacket(serverIP, serverPort);
    udp.print(packetBuffer);
    udp.endPacket();

    // --- (디버깅 시에만 사용) ---
    Serial.println(packetBuffer);
  }
}